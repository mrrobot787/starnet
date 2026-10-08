"""
Observability & KPI Dashboard for Agent Registry

Tracks checkpoint funnel, policy health, and reliability metrics.
Implements Ivy 4-D observability requirements.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import json

from .database import AgentRegistryDB
from .monitoring import MonitoringSystem


class ObservabilityDashboard:
    """Observability and KPI tracking for agent registry"""

    def __init__(self, db_path: str = "agent_registry.db"):
        self.db = AgentRegistryDB(db_path)
        self.monitoring = MonitoringSystem(db_path)
        # Ensure checkpoint table exists
        self._ensure_checkpoint_table()
    
    def _ensure_checkpoint_table(self):
        """Ensure human_checkpoints table exists"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS human_checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checkpoint_id TEXT UNIQUE NOT NULL,
                checkpoint_type TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                required_authority TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                context TEXT,
                decided_by TEXT,
                decided_at TIMESTAMP,
                decision_rationale TEXT,
                expires_at TIMESTAMP,
                escalated_to TEXT,
                escalation_reason TEXT
            )
        """)
        self.db.conn.commit()

    def get_checkpoint_funnel(self, days: int = 7) -> Dict[str, Any]:
        """
        Checkpoint funnel: created → acknowledged → approved/denied → elapsed time
        
        Returns:
            Funnel metrics by checkpoint type and tier
        """
        cursor = self.db.conn.cursor()
        
        # Get all checkpoints in timeframe
        cursor.execute("""
            SELECT checkpoint_type, status, required_authority,
                   created_at, decided_at, expires_at
            FROM human_checkpoints
            WHERE created_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        
        checkpoints = cursor.fetchall()
        
        funnel = {
            'period_days': days,
            'total_created': len(checkpoints),
            'by_type': defaultdict(lambda: {
                'created': 0,
                'pending': 0,
                'approved': 0,
                'rejected': 0,
                'escalated': 0,
                'timeout': 0,
                'avg_resolution_hours': 0
            }),
            'by_tier': defaultdict(lambda: {
                'created': 0,
                'approved': 0,
                'rejected': 0,
                'avg_resolution_hours': 0
            })
        }
        
        resolution_times_by_type = defaultdict(list)
        resolution_times_by_tier = defaultdict(list)
        
        for checkpoint in checkpoints:
            cp_type, status, required_auth, created_at, decided_at, expires_at = checkpoint
            
            funnel['by_type'][cp_type]['created'] += 1
            funnel['by_type'][cp_type][status] += 1
            
            # Determine tier from required authority
            auth_list = json.loads(required_auth)
            tier = self._determine_tier(auth_list)
            
            funnel['by_tier'][tier]['created'] += 1
            if status in ['approved', 'rejected']:
                funnel['by_tier'][tier][status] += 1
            
            # Calculate resolution time
            if decided_at:
                created = datetime.fromisoformat(created_at)
                decided = datetime.fromisoformat(decided_at)
                resolution_hours = (decided - created).total_seconds() / 3600
                
                resolution_times_by_type[cp_type].append(resolution_hours)
                resolution_times_by_tier[tier].append(resolution_hours)
        
        # Calculate averages
        for cp_type, times in resolution_times_by_type.items():
            if times:
                funnel['by_type'][cp_type]['avg_resolution_hours'] = sum(times) / len(times)
        
        for tier, times in resolution_times_by_tier.items():
            if times:
                funnel['by_tier'][tier]['avg_resolution_hours'] = sum(times) / len(times)
        
        # Convert defaultdicts to regular dicts
        funnel['by_type'] = dict(funnel['by_type'])
        funnel['by_tier'] = dict(funnel['by_tier'])
        
        return funnel

    def _determine_tier(self, authorities: List[str]) -> str:
        """Determine tier from authority list"""
        if 'dean' in authorities:
            return 'tier_3_executive'
        elif 'senior_reviewer' in authorities or 'security_officer' in authorities:
            return 'tier_2_senior'
        elif 'senior_operator' in authorities:
            return 'tier_1_senior_ops'
        else:
            return 'tier_0_operator'

    def get_policy_health(self, days: int = 7) -> Dict[str, Any]:
        """
        Policy health: violations/week, top rules, mean time to approve
        """
        violations = self.monitoring.get_violation_summary(days=days)
        
        # Get top violated rules
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT red_line, COUNT(*) as count
            FROM guardrail_violations
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY red_line
            ORDER BY count DESC
            LIMIT 10
        """, (days,))
        
        top_rules = [
            {'red_line': row[0], 'violation_count': row[1]}
            for row in cursor.fetchall()
        ]
        
        # Get mean time to approve
        cursor.execute("""
            SELECT AVG(
                (julianday(decided_at) - julianday(created_at)) * 24
            ) as mean_hours
            FROM human_checkpoints
            WHERE created_at >= datetime('now', '-' || ? || ' days')
            AND status IN ('approved', 'rejected')
        """, (days,))
        
        mean_time_hours = cursor.fetchone()[0] or 0
        
        # Calculate violations per week
        violations_per_week = (violations['total_violations'] / days) * 7
        
        return {
            'period_days': days,
            'violations_per_week': violations_per_week,
            'total_violations': violations['total_violations'],
            'unresolved_count': len([
                v for v in self.db.get_violations(days=days)
                if not v['resolved']
            ]),
            'top_violated_rules': top_rules,
            'mean_time_to_approve_hours': mean_time_hours,
            'by_severity': violations['by_severity'],
            'by_type': violations['by_type']
        }

    def get_reliability_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        Reliability: success rate, error rate, orphaned checkpoints
        """
        cursor = self.db.conn.cursor()
        
        # Total checkpoints
        cursor.execute("""
            SELECT COUNT(*) FROM human_checkpoints
            WHERE created_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        total = cursor.fetchone()[0]
        
        # Successful resolutions
        cursor.execute("""
            SELECT COUNT(*) FROM human_checkpoints
            WHERE created_at >= datetime('now', '-' || ? || ' days')
            AND status IN ('approved', 'rejected')
        """, (days,))
        successful = cursor.fetchone()[0]
        
        # Orphaned checkpoints (pending but expired)
        cursor.execute("""
            SELECT COUNT(*) FROM human_checkpoints
            WHERE status = 'pending'
            AND expires_at < datetime('now')
        """, ())
        orphaned = cursor.fetchone()[0]
        
        # Alert error rate (audit logs with errors)
        cursor.execute("""
            SELECT COUNT(*) FROM audit_logs
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            AND event_type LIKE '%error%'
        """, (days,))
        errors = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM audit_logs
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
        """, (days,))
        total_events = cursor.fetchone()[0]
        
        success_rate = successful / total if total > 0 else 1.0
        error_rate = errors / total_events if total_events > 0 else 0.0
        
        # SLO compliance by tier
        slo_compliance = self._calculate_slo_compliance(days)
        
        return {
            'period_days': days,
            'total_checkpoints': total,
            'successful_resolutions': successful,
            'success_rate': success_rate,
            'slo_target': 0.98,
            'slo_met': success_rate >= 0.98,
            'orphaned_checkpoints': orphaned,
            'alert_error_rate': error_rate,
            'total_events': total_events,
            'slo_compliance_by_tier': slo_compliance
        }

    def _calculate_slo_compliance(self, days: int) -> Dict[str, Any]:
        """Calculate SLO compliance by tier"""
        cursor = self.db.conn.cursor()
        
        # SLA targets by tier (hours)
        sla_targets = {
            'critical': 0.25,  # 15 minutes
            'high': 4,
            'medium': 24,
            'low': 72
        }
        
        compliance = {}
        
        for tier, target_hours in sla_targets.items():
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE 
                           WHEN (julianday(decided_at) - julianday(created_at)) * 24 <= ?
                           THEN 1 ELSE 0 
                       END) as within_sla
                FROM human_checkpoints
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                AND status IN ('approved', 'rejected')
            """, (target_hours, days))
            
            row = cursor.fetchone()
            total, within_sla = row[0], row[1] or 0
            
            compliance[tier] = {
                'target_hours': target_hours,
                'total': total,
                'within_sla': within_sla,
                'compliance_rate': within_sla / total if total > 0 else 1.0,
                'target_rate': 0.95
            }
        
        return compliance

    def get_full_dashboard(self, days: int = 7) -> Dict[str, Any]:
        """Get complete observability dashboard"""
        return {
            'generated_at': datetime.now().isoformat(),
            'period_days': days,
            'checkpoint_funnel': self.get_checkpoint_funnel(days),
            'policy_health': self.get_policy_health(days),
            'reliability': self.get_reliability_metrics(days),
            'system_health': self.monitoring.get_system_health()
        }

    def print_dashboard(self, days: int = 7):
        """Print human-readable dashboard"""
        dashboard = self.get_full_dashboard(days)
        
        print("\n" + "="*80)
        print("AGENT REGISTRY OBSERVABILITY DASHBOARD")
        print("="*80)
        print(f"\nPeriod: Last {days} days")
        print(f"Generated: {dashboard['generated_at']}\n")
        
        # Checkpoint Funnel
        print("─"*80)
        print("CHECKPOINT FUNNEL")
        print("─"*80)
        funnel = dashboard['checkpoint_funnel']
        print(f"Total Created: {funnel['total_created']}")
        print(f"\nBy Type:")
        for cp_type, metrics in funnel['by_type'].items():
            print(f"  {cp_type}:")
            print(f"    Created: {metrics['created']}")
            print(f"    Approved: {metrics['approved']} | Rejected: {metrics['rejected']}")
            print(f"    Pending: {metrics['pending']} | Timeout: {metrics['timeout']}")
            print(f"    Avg Resolution: {metrics['avg_resolution_hours']:.1f}h")
        
        # Policy Health
        print("\n" + "─"*80)
        print("POLICY HEALTH")
        print("─"*80)
        policy = dashboard['policy_health']
        print(f"Violations per Week: {policy['violations_per_week']:.1f}")
        print(f"Unresolved: {policy['unresolved_count']}")
        print(f"Mean Time to Approve: {policy['mean_time_to_approve_hours']:.1f}h")
        print(f"\nTop Violated Rules:")
        for rule in policy['top_violated_rules'][:5]:
            print(f"  - {rule['red_line']}: {rule['violation_count']} violations")
        
        # Reliability
        print("\n" + "─"*80)
        print("RELIABILITY METRICS")
        print("─"*80)
        reliability = dashboard['reliability']
        print(f"Success Rate: {reliability['success_rate']:.2%} (Target: ≥98%)")
        if reliability['slo_met']:
            print("  ✅ SLO MET")
        else:
            print(f"  ❌ SLO VIOLATED (Gap: {0.98 - reliability['success_rate']:.2%})")
        print(f"Orphaned Checkpoints: {reliability['orphaned_checkpoints']} (Target: 0)")
        print(f"Alert Error Rate: {reliability['alert_error_rate']:.2%}")
        
        print(f"\nSLO Compliance by Tier:")
        for tier, metrics in reliability['slo_compliance_by_tier'].items():
            if metrics['total'] > 0:
                status = "✅" if metrics['compliance_rate'] >= 0.95 else "❌"
                print(f"  {status} {tier}: {metrics['compliance_rate']:.1%} " 
                      f"(Target: {metrics['target_rate']:.0%}, "
                      f"{metrics['within_sla']}/{metrics['total']} within {metrics['target_hours']}h)")
        
        # System Health
        print("\n" + "─"*80)
        print("SYSTEM HEALTH")
        print("─"*80)
        health = dashboard['system_health']
        print(f"Status: {health['health_status'].upper()}")
        print(f"Active Agents: {health['active_agents']}/{health['total_agents']}")
        print(f"Violations (24h): {health['violations_24h']}")
        print(f"Unresolved: {health['unresolved_violations']}")
        
        print("\n" + "="*80 + "\n")

    def export_metrics_to_mlflow(self, days: int = 7):
        """Export metrics to MLflow for tracking"""
        try:
            import mlflow
            
            dashboard = self.get_full_dashboard(days)
            
            with mlflow.start_run(run_name=f"registry_observability_{datetime.now().strftime('%Y%m%d')}"):
                # Log reliability metrics
                mlflow.log_metric("success_rate", dashboard['reliability']['success_rate'])
                mlflow.log_metric("orphaned_checkpoints", dashboard['reliability']['orphaned_checkpoints'])
                mlflow.log_metric("alert_error_rate", dashboard['reliability']['alert_error_rate'])
                
                # Log policy health
                mlflow.log_metric("violations_per_week", dashboard['policy_health']['violations_per_week'])
                mlflow.log_metric("unresolved_violations", dashboard['policy_health']['unresolved_count'])
                mlflow.log_metric("mean_time_to_approve_hours", dashboard['policy_health']['mean_time_to_approve_hours'])
                
                # Log funnel metrics
                mlflow.log_metric("checkpoints_created", dashboard['checkpoint_funnel']['total_created'])
                
                # Log as artifact
                with open("observability_dashboard.json", "w") as f:
                    json.dump(dashboard, f, indent=2)
                mlflow.log_artifact("observability_dashboard.json")
                
                print("✅ Metrics exported to MLflow")
        except ImportError:
            print("⚠️  MLflow not available, skipping export")

    def export_metrics_to_wandb(self, days: int = 7):
        """Export metrics to W&B for tracking"""
        try:
            import wandb
            
            dashboard = self.get_full_dashboard(days)
            
            wandb.init(project="agent-registry", name=f"observability_{datetime.now().strftime('%Y%m%d')}")
            
            # Log metrics
            wandb.log({
                "success_rate": dashboard['reliability']['success_rate'],
                "orphaned_checkpoints": dashboard['reliability']['orphaned_checkpoints'],
                "alert_error_rate": dashboard['reliability']['alert_error_rate'],
                "violations_per_week": dashboard['policy_health']['violations_per_week'],
                "unresolved_violations": dashboard['policy_health']['unresolved_count'],
                "mean_time_to_approve_hours": dashboard['policy_health']['mean_time_to_approve_hours'],
                "checkpoints_created": dashboard['checkpoint_funnel']['total_created'],
            })
            
            # Log dashboard as artifact
            wandb.log_artifact("observability_dashboard.json", type="dashboard")
            
            wandb.finish()
            print("✅ Metrics exported to W&B")
        except ImportError:
            print("⚠️  W&B not available, skipping export")

    def close(self):
        """Close database connections"""
        self.db.close()
        self.monitoring.close()


def generate_weekly_report(db_path: str = "agent_registry.db"):
    """Generate weekly observability report"""
    dashboard = ObservabilityDashboard(db_path)
    
    print("\n📊 WEEKLY OBSERVABILITY REPORT\n")
    dashboard.print_dashboard(days=7)
    
    # Export to tracking systems
    dashboard.export_metrics_to_mlflow(days=7)
    dashboard.export_metrics_to_wandb(days=7)
    
    dashboard.close()


if __name__ == "__main__":
    generate_weekly_report()
