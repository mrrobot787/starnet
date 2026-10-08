"""
Agent Registry Monitoring and Audit System

Real-time monitoring, metrics collection, and audit trail analysis.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import json

from .database import AgentRegistryDB


class MonitoringSystem:
    """Monitoring and audit system for agent registry"""

    def __init__(self, db_path: str = "agent_registry.db"):
        self.db = AgentRegistryDB(db_path)

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        total_agents = len(self.db.list_agents())
        active_agents = len(self.db.list_agents(status='active'))
        
        # Get violations in last 24h
        recent_violations = self.db.get_violations(days=1)
        unresolved = len([v for v in recent_violations if not v['resolved']])
        
        # Get high-risk agents
        high_autonomy = len(self.db.list_agents(autonomy_level=3))
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_agents': total_agents,
            'active_agents': active_agents,
            'violations_24h': len(recent_violations),
            'unresolved_violations': unresolved,
            'high_autonomy_agents': high_autonomy,
            'health_status': 'healthy' if unresolved == 0 else 'warning' if unresolved < 5 else 'critical'
        }

    def get_agent_metrics_summary(
        self,
        agent_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get aggregated metrics for an agent"""
        metrics = self.db.get_agent_metrics(agent_id, days=days)
        
        if not metrics:
            return {
                'agent_id': agent_id,
                'period_days': days,
                'no_data': True
            }
        
        # Group by metric name
        by_name = defaultdict(list)
        for metric in metrics:
            by_name[metric['metric_name']].append(metric['metric_value'])
        
        # Calculate stats for each metric
        stats = {}
        for name, values in by_name.items():
            stats[name] = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': values[0] if values else None
            }
        
        return {
            'agent_id': agent_id,
            'period_days': days,
            'metrics': stats,
            'total_datapoints': len(metrics)
        }

    def get_violation_summary(
        self,
        agent_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get violation summary"""
        violations = self.db.get_violations(agent_id=agent_id, days=days)
        
        # Group by type and severity
        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        by_agent = defaultdict(int)
        
        for violation in violations:
            by_type[violation['violation_type']] += 1
            by_severity[violation['severity']] += 1
            by_agent[violation['agent_id']] += 1
        
        return {
            'period_days': days,
            'total_violations': len(violations),
            'by_type': dict(by_type),
            'by_severity': dict(by_severity),
            'by_agent': dict(by_agent),
            'top_violators': sorted(by_agent.items(), key=lambda x: x[1], reverse=True)[:5]
        }

    def get_tool_usage_stats(
        self,
        agent_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get tool usage statistics"""
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT tool_name, capability, 
                   COUNT(*) as total_calls,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                   AVG(duration_ms) as avg_duration_ms
            FROM tool_usage
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
        """
        params = [days]
        
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        
        query += " GROUP BY tool_name, capability ORDER BY total_calls DESC"
        
        cursor.execute(query, params)
        
        stats = []
        for row in cursor.fetchall():
            stats.append({
                'tool_name': row[0],
                'capability': row[1],
                'total_calls': row[2],
                'successful_calls': row[3],
                'success_rate': row[3] / row[2] if row[2] > 0 else 0,
                'avg_duration_ms': row[4]
            })
        
        return {
            'period_days': days,
            'agent_id': agent_id,
            'tool_stats': stats
        }

    def get_audit_trail(
        self,
        agent_id: Optional[str] = None,
        event_type: Optional[str] = None,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit trail"""
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT * FROM audit_logs
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
        """
        params = [days]
        
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]

    def get_escalation_report(self, days: int = 30) -> Dict[str, Any]:
        """Get escalation report"""
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT agent_id, trigger, escalated_to, resolved,
                   COUNT(*) as count
            FROM escalations
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY agent_id, trigger, escalated_to, resolved
            ORDER BY count DESC
        """, (days,))
        
        escalations = []
        total_escalations = 0
        unresolved = 0
        
        for row in cursor.fetchall():
            escalations.append({
                'agent_id': row[0],
                'trigger': row[1],
                'escalated_to': row[2],
                'resolved': bool(row[3]),
                'count': row[4]
            })
            total_escalations += row[4]
            if not row[3]:
                unresolved += row[4]
        
        return {
            'period_days': days,
            'total_escalations': total_escalations,
            'unresolved_escalations': unresolved,
            'escalations': escalations
        }

    def get_performance_dashboard(self, days: int = 7) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data"""
        return {
            'system_health': self.get_system_health(),
            'violation_summary': self.get_violation_summary(days=days),
            'tool_usage': self.get_tool_usage_stats(days=days),
            'escalations': self.get_escalation_report(days=days),
            'period_days': days,
            'generated_at': datetime.now().isoformat()
        }

    def get_agent_report(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive agent report"""
        agent = self.db.get_agent(agent_id)
        
        if not agent:
            return {'error': f'Agent not found: {agent_id}'}
        
        return {
            'agent_id': agent_id,
            'title': agent['title'],
            'status': agent['status'],
            'environment': agent['environment_name'],
            'metrics': self.get_agent_metrics_summary(agent_id, days),
            'violations': self.get_violation_summary(agent_id, days),
            'tool_usage': self.get_tool_usage_stats(agent_id, days),
            'audit_trail': self.get_audit_trail(agent_id, days=days, limit=50),
            'period_days': days,
            'generated_at': datetime.now().isoformat()
        }

    def detect_anomalies(self, agent_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Detect anomalous behavior patterns"""
        anomalies = []
        
        # Get metrics
        metrics = self.db.get_agent_metrics(agent_id, days=days)
        
        # Check for sudden spikes in execution time
        exec_times = [
            m['metric_value'] for m in metrics 
            if m['metric_name'] == 'execution_time'
        ]
        
        if len(exec_times) > 10:
            avg = sum(exec_times) / len(exec_times)
            std = (sum((x - avg) ** 2 for x in exec_times) / len(exec_times)) ** 0.5
            
            for time in exec_times[-10:]:  # Check last 10
                if time > avg + 3 * std:
                    anomalies.append({
                        'type': 'execution_time_spike',
                        'value': time,
                        'threshold': avg + 3 * std,
                        'severity': 'medium'
                    })
        
        # Check for violation patterns
        violations = self.db.get_violations(agent_id=agent_id, days=days)
        
        if len(violations) > 10:
            anomalies.append({
                'type': 'high_violation_count',
                'value': len(violations),
                'threshold': 10,
                'severity': 'high'
            })
        
        # Check for failed tool usage
        tool_stats = self.get_tool_usage_stats(agent_id, days)
        for tool in tool_stats.get('tool_stats', []):
            if tool['success_rate'] < 0.8 and tool['total_calls'] > 5:
                anomalies.append({
                    'type': 'low_tool_success_rate',
                    'tool': tool['tool_name'],
                    'success_rate': tool['success_rate'],
                    'threshold': 0.8,
                    'severity': 'medium'
                })
        
        return anomalies

    def generate_compliance_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate compliance report"""
        # Get all agents
        agents = self.db.list_agents(status='active')
        
        compliance_issues = []
        
        for agent_data in agents:
            agent_id = agent_data['agent_id']
            
            # Check audit logging
            audit_logs = self.get_audit_trail(agent_id, days=days)
            if len(audit_logs) == 0:
                compliance_issues.append({
                    'agent_id': agent_id,
                    'issue': 'no_audit_logs',
                    'severity': 'high',
                    'description': 'Agent has no audit logs in the period'
                })
            
            # Check for violations
            violations = self.db.get_violations(agent_id=agent_id, resolved=False)
            if violations:
                compliance_issues.append({
                    'agent_id': agent_id,
                    'issue': 'unresolved_violations',
                    'severity': 'high',
                    'count': len(violations),
                    'description': f'{len(violations)} unresolved violation(s)'
                })
        
        return {
            'period_days': days,
            'total_active_agents': len(agents),
            'compliance_issues': compliance_issues,
            'issue_count': len(compliance_issues),
            'generated_at': datetime.now().isoformat()
        }

    def export_metrics(
        self,
        filepath: str,
        agent_id: Optional[str] = None,
        days: int = 30
    ):
        """Export metrics to JSON file"""
        if agent_id:
            data = self.get_agent_report(agent_id, days)
        else:
            data = self.get_performance_dashboard(days)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def close(self):
        """Close database connection"""
        self.db.close()
