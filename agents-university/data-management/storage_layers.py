"""
Bronze/Silver/Gold Storage Layer Architecture
Implements Delta-style data lake without drama for Agent University

Storage Strategy:
- Bronze: Raw, append-only, immutable (gzip/parquet)
- Silver: Cleaned + normalized; PII removed/hashed; document text extracted
- Gold: Task-ready tables (features, labels, eval sets) + vector indexes for RAG
"""

import os
import json
import hashlib
import gzip
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dataclasses import dataclass, asdict
import logging

@dataclass
class StorageMetadata:
    """Metadata for stored data artifacts"""
    source_id: str
    dataset_id: str
    layer: str  # bronze, silver, gold
    created_at: str
    record_count: int
    size_bytes: int
    checksum: str
    schema_version: str
    dh_tag_ids: List[str]
    sissa_overlay: Optional[str] = None
    lineage_hash: Optional[str] = None

class BronzeLayer:
    """Raw data storage - append-only, immutable"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)
        
    def store_raw_data(self, source_id: str, data: List[Dict], 
                      batch_id: str = None) -> StorageMetadata:
        """
        Store raw data in Bronze layer
        
        Args:
            source_id: Data source identifier
            data: List of raw records
            batch_id: Optional batch identifier
            
        Returns:
            StorageMetadata for the stored data
        """
        if not batch_id:
            batch_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            
        # Create directory structure
        source_dir = self.base_path / "bronze" / source_id
        source_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        filename = f"{batch_id}.parquet.gz"
        file_path = source_dir / filename
        
        # Convert to DataFrame and store as compressed Parquet
        df = pd.DataFrame(data)
        
        # Add ingestion metadata
        df['_ingestion_timestamp'] = datetime.now(timezone.utc).isoformat()
        df['_batch_id'] = batch_id
        df['_source_id'] = source_id
        
        # Write compressed Parquet
        table = pa.Table.from_pandas(df)
        with gzip.open(file_path, 'wb') as f:
            pq.write_table(table, f, compression='snappy')
        
        # Calculate metadata
        size_bytes = file_path.stat().st_size
        checksum = self._calculate_checksum(file_path)
        
        metadata = StorageMetadata(
            source_id=source_id,
            dataset_id=f"{source_id}_{batch_id}",
            layer="bronze",
            created_at=datetime.now(timezone.utc).isoformat(),
            record_count=len(data),
            size_bytes=size_bytes,
            checksum=checksum,
            schema_version="1.0",
            dh_tag_ids=[]
        )
        
        # Store metadata
        self._store_metadata(source_dir, batch_id, metadata)
        
        self.logger.info(f"Stored {len(data)} records to Bronze: {file_path}")
        return metadata
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _store_metadata(self, source_dir: Path, batch_id: str, metadata: StorageMetadata):
        """Store metadata alongside data"""
        metadata_path = source_dir / f"{batch_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(asdict(metadata), f, indent=2)

class SilverLayer:
    """Cleaned and normalized data storage"""
    
    def __init__(self, base_path: str, pii_redactor=None):
        self.base_path = Path(base_path)
        self.pii_redactor = pii_redactor
        self.logger = logging.getLogger(__name__)
        
    def process_bronze_to_silver(self, bronze_metadata: StorageMetadata,
                                transformation_config: Dict) -> StorageMetadata:
        """
        Process Bronze data to Silver layer with cleaning and normalization
        
        Args:
            bronze_metadata: Metadata from Bronze layer
            transformation_config: Configuration for transformations
            
        Returns:
            StorageMetadata for Silver layer data
        """
        # Load Bronze data
        bronze_path = self._get_bronze_path(bronze_metadata)
        df = self._load_bronze_data(bronze_path)
        
        # Apply transformations
        df_clean = self._apply_transformations(df, transformation_config)
        
        # Apply PII redaction
        if self.pii_redactor:
            df_clean, redaction_log = self.pii_redactor.redact_dataframe(df_clean)
            self._store_redaction_log(bronze_metadata.source_id, redaction_log)
        
        # Store in Silver layer
        silver_metadata = self._store_silver_data(bronze_metadata, df_clean)
        
        return silver_metadata
    
    def _apply_transformations(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """Apply cleaning and normalization transformations"""
        df_clean = df.copy()
        
        # Text extraction and cleaning
        if 'text_extraction' in config:
            df_clean = self._extract_text_content(df_clean, config['text_extraction'])
        
        # Normalization
        if 'normalization' in config:
            df_clean = self._normalize_data(df_clean, config['normalization'])
        
        # Deduplication
        if 'deduplication' in config:
            df_clean = self._deduplicate(df_clean, config['deduplication'])
        
        # Language detection and filtering
        if 'language_filter' in config:
            df_clean = self._filter_by_language(df_clean, config['language_filter'])
        
        # Quality filtering
        if 'quality_filters' in config:
            df_clean = self._apply_quality_filters(df_clean, config['quality_filters'])
        
        return df_clean
    
    def _extract_text_content(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """Extract and clean text content"""
        # Implementation would depend on content types
        # For now, basic text cleaning
        if 'body_text' in df.columns:
            df['body_text_clean'] = df['body_text'].str.strip()
            df['body_text_clean'] = df['body_text_clean'].str.replace(r'\s+', ' ', regex=True)
        
        return df
    
    def _normalize_data(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """Normalize data formats and structures"""
        # Timestamp normalization
        timestamp_cols = config.get('timestamp_columns', [])
        for col in timestamp_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Text normalization
        text_cols = config.get('text_columns', [])
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].str.lower().str.strip()
        
        return df
    
    def _deduplicate(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """Remove duplicate records"""
        method = config.get('method', 'exact')
        
        if method == 'exact':
            # Exact duplicate removal
            subset_cols = config.get('subset_columns')
            df = df.drop_duplicates(subset=subset_cols, keep='first')
        elif method == 'simhash':
            # Simhash-based near-duplicate detection
            # Implementation would use simhash library
            pass
        
        return df
    
    def _filter_by_language(self, df: pd.DataFrame, languages: List[str]) -> pd.DataFrame:
        """Filter records by language"""
        # Would use language detection library like langdetect
        # For now, simple implementation
        return df
    
    def _apply_quality_filters(self, df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """Apply quality filters"""
        # Minimum length filter
        if 'min_length' in filters and 'body_text' in df.columns:
            min_len = filters['min_length']
            df = df[df['body_text'].str.len() >= min_len]
        
        # Maximum length filter
        if 'max_length' in filters and 'body_text' in df.columns:
            max_len = filters['max_length']
            df = df[df['body_text'].str.len() <= max_len]
        
        # Remove empty content
        if 'remove_empty' in filters and filters['remove_empty']:
            df = df.dropna(subset=['body_text'])
            df = df[df['body_text'].str.strip() != '']
        
        return df
    
    def _get_bronze_path(self, metadata: StorageMetadata) -> Path:
        """Get path to Bronze data file"""
        return self.base_path / "bronze" / metadata.source_id / f"{metadata.dataset_id.split('_')[-1]}.parquet.gz"
    
    def _load_bronze_data(self, bronze_path: Path) -> pd.DataFrame:
        """Load data from Bronze layer"""
        with gzip.open(bronze_path, 'rb') as f:
            table = pq.read_table(f)
            return table.to_pandas()
    
    def _store_silver_data(self, bronze_metadata: StorageMetadata, df: pd.DataFrame) -> StorageMetadata:
        """Store processed data in Silver layer"""
        # Create Silver directory
        silver_dir = self.base_path / "silver" / bronze_metadata.source_id
        silver_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate Silver filename
        batch_id = bronze_metadata.dataset_id.split('_')[-1]
        filename = f"{batch_id}_silver.parquet"
        file_path = silver_dir / filename
        
        # Store as Parquet (uncompressed for faster access)
        table = pa.Table.from_pandas(df)
        pq.write_table(table, file_path, compression='snappy')
        
        # Create Silver metadata
        size_bytes = file_path.stat().st_size
        checksum = self._calculate_checksum(file_path)
        
        silver_metadata = StorageMetadata(
            source_id=bronze_metadata.source_id,
            dataset_id=f"{bronze_metadata.source_id}_{batch_id}_silver",
            layer="silver",
            created_at=datetime.now(timezone.utc).isoformat(),
            record_count=len(df),
            size_bytes=size_bytes,
            checksum=checksum,
            schema_version="1.0",
            dh_tag_ids=bronze_metadata.dh_tag_ids,
            sissa_overlay=bronze_metadata.sissa_overlay,
            lineage_hash=bronze_metadata.checksum  # Link to Bronze
        )
        
        # Store metadata
        self._store_metadata(silver_dir, f"{batch_id}_silver", silver_metadata)
        
        self.logger.info(f"Processed to Silver: {len(df)} records -> {file_path}")
        return silver_metadata
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _store_metadata(self, silver_dir: Path, batch_id: str, metadata: StorageMetadata):
        """Store metadata alongside data"""
        metadata_path = silver_dir / f"{batch_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(asdict(metadata), f, indent=2)
    
    def _store_redaction_log(self, source_id: str, redaction_log: List[Dict]):
        """Store PII redaction log for audit trail"""
        log_dir = self.base_path / "silver" / source_id / "redaction_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"redaction_log_{timestamp}.json"
        
        with open(log_path, 'w') as f:
            json.dump(redaction_log, f, indent=2)

class GoldLayer:
    """Task-ready data storage with features, labels, and vector indexes"""
    
    def __init__(self, base_path: str, vector_store=None):
        self.base_path = Path(base_path)
        self.vector_store = vector_store
        self.logger = logging.getLogger(__name__)
        
    def create_rag_corpus(self, silver_metadata: StorageMetadata,
                         chunking_config: Dict) -> StorageMetadata:
        """Create RAG corpus from Silver data"""
        # Load Silver data
        silver_path = self._get_silver_path(silver_metadata)
        df = self._load_silver_data(silver_path)
        
        # Create document chunks
        chunks_df = self._create_document_chunks(df, chunking_config)
        
        # Generate embeddings if vector store available
        if self.vector_store:
            chunks_df = self._generate_embeddings(chunks_df)
        
        # Store in Gold layer
        gold_metadata = self._store_gold_data(silver_metadata, chunks_df, "rag_corpus")
        
        return gold_metadata
    
    def create_training_dataset(self, silver_metadata: StorageMetadata,
                              labeling_config: Dict) -> StorageMetadata:
        """Create supervised learning dataset from Silver data"""
        # Load Silver data
        silver_path = self._get_silver_path(silver_metadata)
        df = self._load_silver_data(silver_path)
        
        # Extract features and labels
        training_df = self._extract_features_labels(df, labeling_config)
        
        # Split train/validation/test
        training_df = self._create_train_test_splits(training_df, labeling_config)
        
        # Store in Gold layer
        gold_metadata = self._store_gold_data(silver_metadata, training_df, "training")
        
        return gold_metadata
    
    def _create_document_chunks(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """Create document chunks for RAG"""
        chunks = []
        
        for idx, row in df.iterrows():
            text = row.get('body_text_clean', '')
            if not text:
                continue
                
            # Simple chunking by character count
            chunk_size = config.get('chunk_size', 1024)
            overlap = config.get('overlap', 128)
            
            for i in range(0, len(text), chunk_size - overlap):
                chunk_text = text[i:i + chunk_size]
                if len(chunk_text.strip()) < config.get('min_chunk_size', 100):
                    continue
                    
                chunk = {
                    'chunk_id': f"{row.get('id', idx)}_{i}",
                    'source_doc_id': row.get('id', idx),
                    'chunk_order': i // (chunk_size - overlap),
                    'chunk_text': chunk_text,
                    'token_count': len(chunk_text.split()),
                    'char_count': len(chunk_text),
                    'metadata_json': json.dumps({
                        'source': row.get('source', ''),
                        'created_at': row.get('created_at', ''),
                        'author': row.get('author', '')
                    })
                }
                chunks.append(chunk)
        
        return pd.DataFrame(chunks)
    
    def _generate_embeddings(self, chunks_df: pd.DataFrame) -> pd.DataFrame:
        """Generate embeddings for chunks"""
        # Placeholder - would integrate with actual embedding service
        chunks_df['embedding_key'] = chunks_df['chunk_id'].apply(
            lambda x: f"embedding_{x}"
        )
        return chunks_df
    
    def _extract_features_labels(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """Extract features and labels for supervised learning"""
        # Extract feature columns
        feature_cols = config.get('feature_columns', [])
        label_cols = config.get('label_columns', [])
        
        # Create training dataset
        training_data = df[feature_cols + label_cols].copy()
        
        # Add engineered features
        if 'feature_engineering' in config:
            training_data = self._engineer_features(training_data, config['feature_engineering'])
        
        return training_data
    
    def _engineer_features(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """Engineer additional features"""
        # Text length features
        if 'text_length' in config and 'body_text_clean' in df.columns:
            df['text_length'] = df['body_text_clean'].str.len()
            df['word_count'] = df['body_text_clean'].str.split().str.len()
        
        # Temporal features
        if 'temporal' in config and 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['hour_of_day'] = df['created_at'].dt.hour
            df['day_of_week'] = df['created_at'].dt.dayofweek
        
        return df
    
    def _create_train_test_splits(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """Create train/validation/test splits"""
        split_method = config.get('split_method', 'random')
        
        if split_method == 'temporal' and 'created_at' in df.columns:
            # Temporal split to avoid data leakage
            df = df.sort_values('created_at')
            train_end = config.get('train_end_date')
            val_start = config.get('validation_start_date')
            test_start = config.get('test_start_date')
            
            if train_end:
                df.loc[df['created_at'] <= train_end, 'split'] = 'train'
            if val_start and test_start:
                df.loc[(df['created_at'] >= val_start) & (df['created_at'] < test_start), 'split'] = 'validation'
                df.loc[df['created_at'] >= test_start, 'split'] = 'test'
        else:
            # Random split
            df = df.sample(frac=1).reset_index(drop=True)  # Shuffle
            n = len(df)
            train_size = config.get('train_ratio', 0.7)
            val_size = config.get('val_ratio', 0.15)
            
            df.loc[:int(n * train_size), 'split'] = 'train'
            df.loc[int(n * train_size):int(n * (train_size + val_size)), 'split'] = 'validation'
            df.loc[int(n * (train_size + val_size)):, 'split'] = 'test'
        
        return df
    
    def _get_silver_path(self, metadata: StorageMetadata) -> Path:
        """Get path to Silver data file"""
        batch_id = metadata.dataset_id.split('_')[-2]  # Extract batch ID
        return self.base_path / "silver" / metadata.source_id / f"{batch_id}_silver.parquet"
    
    def _load_silver_data(self, silver_path: Path) -> pd.DataFrame:
        """Load data from Silver layer"""
        return pd.read_parquet(silver_path)
    
    def _store_gold_data(self, silver_metadata: StorageMetadata, df: pd.DataFrame, 
                        purpose: str) -> StorageMetadata:
        """Store processed data in Gold layer"""
        # Create Gold directory
        gold_dir = self.base_path / "gold" / silver_metadata.source_id / purpose
        gold_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate Gold filename
        batch_id = silver_metadata.dataset_id.split('_')[-2]
        filename = f"{batch_id}_{purpose}.parquet"
        file_path = gold_dir / filename
        
        # Store as Parquet
        df.to_parquet(file_path, compression='snappy')
        
        # Create Gold metadata
        size_bytes = file_path.stat().st_size
        checksum = self._calculate_checksum(file_path)
        
        gold_metadata = StorageMetadata(
            source_id=silver_metadata.source_id,
            dataset_id=f"{silver_metadata.source_id}_{batch_id}_{purpose}",
            layer="gold",
            created_at=datetime.now(timezone.utc).isoformat(),
            record_count=len(df),
            size_bytes=size_bytes,
            checksum=checksum,
            schema_version="1.0",
            dh_tag_ids=silver_metadata.dh_tag_ids,
            sissa_overlay=silver_metadata.sissa_overlay,
            lineage_hash=silver_metadata.checksum  # Link to Silver
        )
        
        # Store metadata
        self._store_metadata(gold_dir, f"{batch_id}_{purpose}", gold_metadata)
        
        self.logger.info(f"Created Gold {purpose}: {len(df)} records -> {file_path}")
        return gold_metadata
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _store_metadata(self, gold_dir: Path, batch_id: str, metadata: StorageMetadata):
        """Store metadata alongside data"""
        metadata_path = gold_dir / f"{batch_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(asdict(metadata), f, indent=2)

class DataLakeManager:
    """Orchestrates the Bronze/Silver/Gold data lake"""
    
    def __init__(self, base_path: str, pii_redactor=None, vector_store=None):
        self.base_path = Path(base_path)
        self.bronze = BronzeLayer(base_path)
        self.silver = SilverLayer(base_path, pii_redactor)
        self.gold = GoldLayer(base_path, vector_store)
        self.logger = logging.getLogger(__name__)
        
    def ingest_data_end_to_end(self, source_id: str, raw_data: List[Dict],
                              transformation_config: Dict, 
                              gold_configs: List[Dict]) -> List[StorageMetadata]:
        """
        Complete end-to-end data ingestion pipeline
        
        Args:
            source_id: Data source identifier
            raw_data: Raw data records
            transformation_config: Silver layer transformation config
            gold_configs: List of Gold layer configurations
            
        Returns:
            List of metadata for all created datasets
        """
        metadata_list = []
        
        # Bronze layer ingestion
        bronze_metadata = self.bronze.store_raw_data(source_id, raw_data)
        metadata_list.append(bronze_metadata)
        
        # Silver layer processing
        silver_metadata = self.silver.process_bronze_to_silver(
            bronze_metadata, transformation_config
        )
        metadata_list.append(silver_metadata)
        
        # Gold layer processing
        for gold_config in gold_configs:
            purpose = gold_config.get('purpose', 'rag')
            
            if purpose == 'rag':
                gold_metadata = self.gold.create_rag_corpus(silver_metadata, gold_config)
            elif purpose == 'training':
                gold_metadata = self.gold.create_training_dataset(silver_metadata, gold_config)
            else:
                self.logger.warning(f"Unknown Gold purpose: {purpose}")
                continue
                
            metadata_list.append(gold_metadata)
        
        self.logger.info(f"End-to-end ingestion complete: {len(metadata_list)} datasets created")
        return metadata_list
