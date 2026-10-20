"""
Data Source Scoring and Prioritization System
Implements the 4-axis rubric for Agent University / ClosedLoopSecuritySystem

Scoring Formula: priority = 2*Value + 2*Legality + Effort^-1 + Risk^-1
"""

import sqlite3
import yaml
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

@dataclass
class DataSourceScore:
    """Data source scoring result"""
    source_id: str
    value: int
    legality: int
    effort: int
    risk: int
    priority_score: float
    rationale: Dict[str, str]

class DataSourceScorer:
    """Implements the 4-axis scoring rubric for data source prioritization"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
    def score_data_source(self, source_config: Dict) -> DataSourceScore:
        """
        Score a data source on the 4-axis rubric (0-5 scale each)
        
        Args:
            source_config: YAML configuration dict for the data source
            
        Returns:
            DataSourceScore with calculated priority
        """
        
        # Extract scoring from config if provided, otherwise calculate
        if 'scoring' in source_config:
            scores = source_config['scoring']
            value = scores.get('value', 0)
            legality = scores.get('legality', 0)
            effort = scores.get('effort', 5)  # Default high effort
            risk = scores.get('risk', 5)      # Default high risk
        else:
            # Calculate scores based on configuration
            value = self._calculate_value_score(source_config)
            legality = self._calculate_legality_score(source_config)
            effort = self._calculate_effort_score(source_config)
            risk = self._calculate_risk_score(source_config)
        
        # Calculate priority using the formula
        priority_score = self._calculate_priority(value, legality, effort, risk)
        
        # Generate rationale
        rationale = self._generate_rationale(source_config, value, legality, effort, risk)
        
        return DataSourceScore(
            source_id=source_config['id'],
            value=value,
            legality=legality,
            effort=effort,
            risk=risk,
            priority_score=priority_score,
            rationale=rationale
        )
    
    def _calculate_priority(self, value: int, legality: int, effort: int, risk: int) -> float:
        """Calculate priority score using the formula"""
        effort_component = 5.0 / effort if effort > 0 else 0
        risk_component = 5.0 / risk if risk > 0 else 0
        
        return 2.0 * value + 2.0 * legality + effort_component + risk_component
    
    def _calculate_value_score(self, config: Dict) -> int:
        """Calculate value score (0-5) based on configuration"""
        score = 0
        
        # High value indicators
        if config.get('system_of_record', False):
            score += 2
            
        usage = config.get('usage', {})
        primary_purpose = usage.get('primary_purpose', '')
        
        # Training data is highest value
        if primary_purpose == 'ft':
            score += 3
        elif primary_purpose == 'rag':
            score += 2
        elif primary_purpose == 'eval':
            score += 2
        
        # Multiple use cases add value
        secondary_purposes = usage.get('secondary_purposes', [])
        score += min(len(secondary_purposes), 1)
        
        # Operational/incident data is high value
        if any(keyword in config.get('scope', '').lower() 
               for keyword in ['incident', 'security', 'critical', 'production']):
            score += 1
            
        return min(score, 5)
    
    def _calculate_legality_score(self, config: Dict) -> int:
        """Calculate legality score (0-5) based on legal framework"""
        score = 0
        legal = config.get('legal', {})
        
        # Legal basis strength
        basis = legal.get('basis', '')
        if basis == 'legitimate_interests':
            score += 3
        elif basis == 'consent':
            score += 2
        elif basis in ['contract', 'legal_obligation']:
            score += 4
        
        # PII level (inverse scoring - less PII is better)
        pii_level = legal.get('pii', 'present')
        if pii_level == 'none':
            score += 2
        elif pii_level == 'possible':
            score += 1
        
        # License clarity
        license_text = legal.get('license', '').lower()
        if 'internal use only' in license_text:
            score += 1
        elif 'enterprise agreement' in license_text:
            score += 1
            
        return min(score, 5)
    
    def _calculate_effort_score(self, config: Dict) -> int:
        """Calculate effort score (0-5, higher = more effort)"""
        score = 3  # Default moderate effort
        
        # API maturity indicators
        auth_method = config.get('security', {}).get('auth', '')
        if auth_method in ['oauth2_service_account', 'aad_app_sp']:
            score -= 1  # Mature auth = less effort
        elif auth_method in ['api_key', 'basic_auth']:
            score += 1  # Simple but less secure
            
        # Data type complexity
        data_type = config.get('type', '')
        if data_type in ['sharepoint', 'github', 'jira']:
            score -= 1  # Well-documented APIs
        elif data_type in ['siem', 'logs', 'database']:
            score += 1  # More complex integration
            
        # Processing complexity
        processing = config.get('processing', {})
        if processing.get('code_analysis', False):
            score += 1
        if processing.get('extract_metadata', []):
            score += 1
            
        # Quality controls complexity
        quality = config.get('quality', {})
        if quality.get('dedupe', '') != 'exact_match':
            score += 1
            
        return max(1, min(score, 5))
    
    def _calculate_risk_score(self, config: Dict) -> int:
        """Calculate risk score (0-5, higher = more risk)"""
        score = 2  # Default low-moderate risk
        
        # PII risk
        pii_level = config.get('legal', {}).get('pii', 'none')
        if pii_level == 'high':
            score += 2
        elif pii_level == 'present':
            score += 1
        elif pii_level == 'possible':
            score += 1
            
        # Sensitivity level
        sensitivity = config.get('governance', {}).get('sensitivity', 'Internal')
        if sensitivity == 'Restricted':
            score += 2
        elif sensitivity == 'Confidential':
            score += 1
            
        # External data risk
        if not config.get('system_of_record', False):
            score += 1
            
        # Security controls (inverse - more controls = less risk)
        security = config.get('security', {})
        if security.get('permissions', []):
            score -= 1
        if security.get('secret_name'):
            score -= 1
            
        return max(1, min(score, 5))
    
    def _generate_rationale(self, config: Dict, value: int, legality: int, 
                          effort: int, risk: int) -> Dict[str, str]:
        """Generate human-readable rationale for scoring"""
        return {
            'value': self._value_rationale(config, value),
            'legality': self._legality_rationale(config, legality),
            'effort': self._effort_rationale(config, effort),
            'risk': self._risk_rationale(config, risk)
        }
    
    def _value_rationale(self, config: Dict, score: int) -> str:
        """Generate value score rationale"""
        reasons = []
        
        if config.get('system_of_record', False):
            reasons.append("system of record")
            
        primary_purpose = config.get('usage', {}).get('primary_purpose', '')
        if primary_purpose == 'ft':
            reasons.append("supervised training data")
        elif primary_purpose == 'rag':
            reasons.append("knowledge retrieval")
            
        if 'incident' in config.get('scope', '').lower():
            reasons.append("operational incident data")
            
        return f"Score {score}/5: {', '.join(reasons) if reasons else 'standard value'}"
    
    def _legality_rationale(self, config: Dict, score: int) -> str:
        """Generate legality score rationale"""
        legal = config.get('legal', {})
        basis = legal.get('basis', 'unknown')
        pii = legal.get('pii', 'unknown')
        
        return f"Score {score}/5: {basis} legal basis, {pii} PII level"
    
    def _effort_rationale(self, config: Dict, score: int) -> str:
        """Generate effort score rationale"""
        data_type = config.get('type', 'unknown')
        auth = config.get('security', {}).get('auth', 'unknown')
        
        return f"Score {score}/5: {data_type} connector, {auth} authentication"
    
    def _risk_rationale(self, config: Dict, score: int) -> str:
        """Generate risk score rationale"""
        pii = config.get('legal', {}).get('pii', 'unknown')
        sensitivity = config.get('governance', {}).get('sensitivity', 'unknown')
        
        return f"Score {score}/5: {pii} PII, {sensitivity} sensitivity"

class DataSourceRegistry:
    """Manages the data source registry and scoring"""
    
    def __init__(self, db_path: str, datasources_dir: str):
        self.db_path = db_path
        self.datasources_dir = Path(datasources_dir)
        self.scorer = DataSourceScorer(db_path)
        self.logger = logging.getLogger(__name__)
        
    def load_and_score_all_sources(self) -> List[DataSourceScore]:
        """Load all YAML configs and score them"""
        scores = []
        
        for yaml_file in self.datasources_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                score = self.scorer.score_data_source(config)
                scores.append(score)
                
                self.logger.info(f"Scored {config['id']}: {score.priority_score:.2f}")
                
            except Exception as e:
                self.logger.error(f"Error scoring {yaml_file}: {e}")
                
        return sorted(scores, key=lambda x: x.priority_score, reverse=True)
    
    def update_database_scores(self, scores: List[DataSourceScore]):
        """Update the database with calculated scores"""
        with sqlite3.connect(self.db_path) as conn:
            for score in scores:
                conn.execute("""
                    UPDATE datasource_registry 
                    SET score_value = ?, score_legality = ?, score_effort = ?, score_risk = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (score.value, score.legality, score.effort, score.risk, score.source_id))
                
            conn.commit()
    
    def generate_priority_report(self, scores: List[DataSourceScore]) -> str:
        """Generate a priority report for stakeholders"""
        report = ["# Data Source Priority Report", ""]
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Total Sources Evaluated: {len(scores)}")
        report.append("")
        
        # Top priorities
        report.append("## Top Priority Sources (Score >= 10.0)")
        report.append("")
        report.append("| Rank | Source ID | Priority Score | Value | Legality | Effort | Risk |")
        report.append("|------|-----------|----------------|-------|----------|--------|------|")
        
        for i, score in enumerate(scores[:10], 1):
            if score.priority_score >= 10.0:
                report.append(f"| {i} | {score.source_id} | {score.priority_score:.2f} | "
                            f"{score.value} | {score.legality} | {score.effort} | {score.risk} |")
        
        report.append("")
        
        # Rationale for top 5
        report.append("## Detailed Rationale (Top 5)")
        report.append("")
        
        for i, score in enumerate(scores[:5], 1):
            report.append(f"### {i}. {score.source_id} (Score: {score.priority_score:.2f})")
            report.append("")
            for axis, rationale in score.rationale.items():
                report.append(f"- **{axis.title()}**: {rationale}")
            report.append("")
        
        return "\n".join(report)

def main():
    """Main function for running the scoring system"""
    logging.basicConfig(level=logging.INFO)
    
    # Paths
    db_path = "data_source_registry.db"
    datasources_dir = "datasources"
    
    # Initialize registry
    registry = DataSourceRegistry(db_path, datasources_dir)
    
    # Score all sources
    scores = registry.load_and_score_all_sources()
    
    # Update database
    registry.update_database_scores(scores)
    
    # Generate report
    report = registry.generate_priority_report(scores)
    
    # Save report
    with open("data_source_priority_report.md", "w") as f:
        f.write(report)
    
    print(f"Scored {len(scores)} data sources")
    print(f"Top priority: {scores[0].source_id} ({scores[0].priority_score:.2f})")
    print("Report saved to data_source_priority_report.md")

if __name__ == "__main__":
    main()
