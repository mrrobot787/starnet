"""
Main Data Management Orchestrator
Coordinates all components of the Agent University data management system

This is the central entry point that ties together:
- Data source registry and scoring
- Bronze/Silver/Gold storage layers
- PII redaction and security scanning
- Double Helix tagging and SISSA integration
- Governance and compliance framework
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import argparse

# Import all our components
from scoring_system import DataSourceRegistry, DataSourceScorer
from storage_layers import DataLakeManager
from safety_gates import SafetyGateOrchestrator
from double_helix_sissa_integration import DataIngestionOrchestrator
from governance_framework import GovernanceOrchestrator

class AgentUniversityDataManager:
    """Main orchestrator for the Agent University data management system"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        # Initialize all components
        self.db_path = self.config.get('database_path', 'agent_university.db')
        self.data_lake_path = self.config.get('data_lake_path', 'data_lake')
        self.datasources_dir = self.config.get('datasources_dir', 'datasources')
        
        # Core components
        self.source_registry = DataSourceRegistry(self.db_path, self.datasources_dir)
        self.data_lake = DataLakeManager(self.data_lake_path)
        self.safety_gates = SafetyGateOrchestrator(self.db_path)
        self.dh_sissa_orchestrator = DataIngestionOrchestrator(self.db_path)
        self.governance = GovernanceOrchestrator(self.db_path)
        
        self.logger.info("Agent University Data Manager initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        default_config = {
            'database_path': 'agent_university.db',
            'data_lake_path': 'data_lake',
            'datasources_dir': 'datasources',
            'log_level': 'INFO',
            'safety_gates_enabled': True,
            'double_helix_enabled': True,
            'governance_enabled': True
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
        
        return default_config
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO'))
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('agent_university_data_manager.log')
            ]
        )
        
        return logging.getLogger(__name__)
    
    def initialize_system(self) -> Dict[str, Any]:
        """Initialize the complete data management system"""
        self.logger.info("Initializing Agent University Data Management System")
        
        results = {
            'initialization_start': datetime.now(timezone.utc).isoformat(),
            'components_initialized': [],
            'errors': []
        }
        
        try:
            # Initialize database schema
            self._initialize_database()
            results['components_initialized'].append('database_schema')
            
            # Create directory structure
            self._create_directory_structure()
            results['components_initialized'].append('directory_structure')
            
            # Load and score data sources
            scores = self.source_registry.load_and_score_all_sources()
            self.source_registry.update_database_scores(scores)
            results['components_initialized'].append('data_source_scoring')
            results['data_sources_scored'] = len(scores)
            
            # Generate initial reports
            priority_report = self.source_registry.generate_priority_report(scores)
            with open('data_source_priority_report.md', 'w') as f:
                f.write(priority_report)
            results['components_initialized'].append('priority_report')
            
            # Run initial governance checks
            if self.config.get('governance_enabled', True):
                governance_results = self.governance.run_daily_governance_checks()
                results['governance_check'] = governance_results
                results['components_initialized'].append('governance_framework')
            
            results['status'] = 'success'
            results['initialization_end'] = datetime.now(timezone.utc).isoformat()
            
            self.logger.info("System initialization completed successfully")
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            results['errors'].append(str(e))
            self.logger.error(f"System initialization failed: {e}")
        
        return results
    
    def ingest_data_source(self, source_id: str, data_records: List[Dict],
                          transformation_config: Dict = None,
                          gold_configs: List[Dict] = None) -> Dict[str, Any]:
        """
        Complete end-to-end data ingestion for a source
        
        Args:
            source_id: Data source identifier
            data_records: Raw data records to ingest
            transformation_config: Silver layer transformation config
            gold_configs: Gold layer processing configs
            
        Returns:
            Complete ingestion results
        """
        self.logger.info(f"Starting data ingestion for source: {source_id}")
        
        ingestion_results = {
            'source_id': source_id,
            'ingestion_start': datetime.now(timezone.utc).isoformat(),
            'total_records': len(data_records),
            'stages_completed': [],
            'errors': []
        }
        
        try:
            # Stage 1: Safety Gates
            if self.config.get('safety_gates_enabled', True):
                safe_records = []
                for i, record in enumerate(data_records):
                    content = record.get('content', record.get('body_text', ''))
                    if content:
                        safety_result = self.safety_gates.process_content_through_gates(
                            content, record
                        )
                        
                        if safety_result['all_gates_passed']:
                            record['content'] = safety_result['processed_content']
                            record['safety_metadata'] = safety_result
                            safe_records.append(record)
                        else:
                            self.logger.warning(f"Record {i} failed safety gates: {safety_result.get('gates_failed', [])}")
                
                data_records = safe_records
                ingestion_results['records_after_safety_gates'] = len(data_records)
                ingestion_results['stages_completed'].append('safety_gates')
            
            # Stage 2: Double Helix + SISSA Integration
            if self.config.get('double_helix_enabled', True):
                dh_sissa_results = self.dh_sissa_orchestrator.batch_process_dataset(
                    data_records, source_id
                )
                ingestion_results['dh_sissa_results'] = dh_sissa_results
                ingestion_results['stages_completed'].append('double_helix_sissa')
            
            # Stage 3: Data Lake Ingestion (Bronze -> Silver -> Gold)
            if not transformation_config:
                transformation_config = self._get_default_transformation_config(source_id)
            
            if not gold_configs:
                gold_configs = self._get_default_gold_configs(source_id)
            
            lake_metadata = self.data_lake.ingest_data_end_to_end(
                source_id, data_records, transformation_config, gold_configs
            )
            
            ingestion_results['lake_metadata'] = [
                {
                    'dataset_id': meta.dataset_id,
                    'layer': meta.layer,
                    'record_count': meta.record_count,
                    'size_bytes': meta.size_bytes
                }
                for meta in lake_metadata
            ]
            ingestion_results['stages_completed'].append('data_lake_ingestion')
            
            # Stage 4: Update Registry
            self._update_ingestion_registry(source_id, ingestion_results)
            ingestion_results['stages_completed'].append('registry_update')
            
            ingestion_results['status'] = 'success'
            ingestion_results['ingestion_end'] = datetime.now(timezone.utc).isoformat()
            
            self.logger.info(f"Data ingestion completed for {source_id}: {len(data_records)} records processed")
            
        except Exception as e:
            ingestion_results['status'] = 'error'
            ingestion_results['error'] = str(e)
            ingestion_results['errors'].append(str(e))
            self.logger.error(f"Data ingestion failed for {source_id}: {e}")
        
        return ingestion_results
    
    def run_data_source_scoring(self) -> Dict[str, Any]:
        """Run data source scoring and prioritization"""
        self.logger.info("Running data source scoring and prioritization")
        
        try:
            # Load and score all sources
            scores = self.source_registry.load_and_score_all_sources()
            
            # Update database
            self.source_registry.update_database_scores(scores)
            
            # Generate report
            report = self.source_registry.generate_priority_report(scores)
            
            # Save report
            report_path = f"data_source_priority_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, 'w') as f:
                f.write(report)
            
            return {
                'status': 'success',
                'sources_scored': len(scores),
                'top_priority_source': scores[0].source_id if scores else None,
                'top_priority_score': scores[0].priority_score if scores else None,
                'report_path': report_path
            }
            
        except Exception as e:
            self.logger.error(f"Data source scoring failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def run_governance_checks(self) -> Dict[str, Any]:
        """Run comprehensive governance and compliance checks"""
        self.logger.info("Running governance and compliance checks")
        
        try:
            results = self.governance.run_daily_governance_checks()
            
            # Generate dashboard
            dashboard = self.governance.generate_governance_dashboard()
            
            # Save dashboard
            dashboard_path = f"governance_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(dashboard_path, 'w') as f:
                json.dump(dashboard, f, indent=2)
            
            results['dashboard_path'] = dashboard_path
            return results
            
        except Exception as e:
            self.logger.error(f"Governance checks failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system_health': 'healthy',
            'components': {},
            'statistics': {}
        }
        
        try:
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                # Data source statistics
                cursor = conn.execute("SELECT COUNT(*) FROM datasource_registry WHERE status = 'active'")
                status['statistics']['active_data_sources'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM dataset_registry")
                status['statistics']['total_datasets'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT AVG(priority_score) FROM datasource_registry WHERE priority_score IS NOT NULL")
                avg_priority = cursor.fetchone()[0]
                status['statistics']['average_priority_score'] = round(avg_priority, 2) if avg_priority else 0
                
                # Recent ingestion activity
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM ingestion_audit 
                    WHERE ingestion_start > datetime('now', '-24 hours')
                """)
                status['statistics']['ingestions_last_24h'] = cursor.fetchone()[0]
                
                # Governance statistics
                cursor = conn.execute("SELECT COUNT(*) FROM data_processing_agreements WHERE status = 'active'")
                status['statistics']['active_dpas'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM data_subject_requests WHERE status = 'received'")
                status['statistics']['pending_data_requests'] = cursor.fetchone()[0]
            
            # Component health checks
            status['components']['database'] = 'healthy'
            status['components']['data_lake'] = 'healthy' if os.path.exists(self.data_lake_path) else 'warning'
            status['components']['datasources_config'] = 'healthy' if os.path.exists(self.datasources_dir) else 'error'
            
        except Exception as e:
            status['system_health'] = 'error'
            status['error'] = str(e)
            self.logger.error(f"System status check failed: {e}")
        
        return status
    
    def _initialize_database(self):
        """Initialize database with all required tables"""
        # Database initialization is handled by individual components
        # This ensures all tables are created
        pass
    
    def _create_directory_structure(self):
        """Create required directory structure"""
        directories = [
            self.data_lake_path,
            f"{self.data_lake_path}/bronze",
            f"{self.data_lake_path}/silver", 
            f"{self.data_lake_path}/gold",
            self.datasources_dir,
            "reports",
            "logs"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def _get_default_transformation_config(self, source_id: str) -> Dict:
        """Get default transformation config for a source"""
        return {
            'text_extraction': {
                'enabled': True
            },
            'normalization': {
                'timestamp_columns': ['created_at', 'modified_at', 'timestamp'],
                'text_columns': ['title', 'description', 'content', 'body_text']
            },
            'deduplication': {
                'method': 'exact',
                'subset_columns': ['id', 'content_hash']
            },
            'language_filter': ['en', 'en-US'],
            'quality_filters': {
                'min_length': 100,
                'max_length': 50000,
                'remove_empty': True
            }
        }
    
    def _get_default_gold_configs(self, source_id: str) -> List[Dict]:
        """Get default Gold layer configs for a source"""
        return [
            {
                'purpose': 'rag',
                'chunk_size': 1024,
                'overlap': 128,
                'min_chunk_size': 100
            }
        ]
    
    def _update_ingestion_registry(self, source_id: str, results: Dict):
        """Update ingestion registry with results"""
        try:
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE datasource_registry 
                    SET last_ingestion = datetime('now'), updated_at = datetime('now')
                    WHERE id = ?
                """, (source_id,))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to update ingestion registry: {e}")

def main():
    """Main entry point for the data management system"""
    parser = argparse.ArgumentParser(description='Agent University Data Management System')
    parser.add_argument('command', choices=[
        'init', 'score', 'ingest', 'governance', 'status'
    ], help='Command to execute')
    parser.add_argument('--config', default='config.json', help='Configuration file path')
    parser.add_argument('--source-id', help='Data source ID for ingestion')
    parser.add_argument('--data-file', help='Data file for ingestion')
    
    args = parser.parse_args()
    
    # Initialize system
    manager = AgentUniversityDataManager(args.config)
    
    if args.command == 'init':
        print("Initializing Agent University Data Management System...")
        results = manager.initialize_system()
        print(json.dumps(results, indent=2))
        
    elif args.command == 'score':
        print("Running data source scoring...")
        results = manager.run_data_source_scoring()
        print(json.dumps(results, indent=2))
        
    elif args.command == 'ingest':
        if not args.source_id or not args.data_file:
            print("Error: --source-id and --data-file required for ingestion")
            sys.exit(1)
        
        print(f"Ingesting data from {args.data_file} for source {args.source_id}...")
        
        # Load data file (assuming JSON for now)
        with open(args.data_file, 'r') as f:
            data_records = json.load(f)
        
        results = manager.ingest_data_source(args.source_id, data_records)
        print(json.dumps(results, indent=2))
        
    elif args.command == 'governance':
        print("Running governance checks...")
        results = manager.run_governance_checks()
        print(json.dumps(results, indent=2))
        
    elif args.command == 'status':
        print("Getting system status...")
        status = manager.get_system_status()
        print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()
