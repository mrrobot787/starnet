"""
M&M (Morbidity & Mortality) Review Dashboard

Monthly review dashboard for agent incidents, near-misses, and rollbacks.
Inspired by medical M&M conferences where cases are reviewed for learning.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import json

from .database import AgentRegistryDB
from .monitoring import MonitoringSystem


class MMReviewDashboard:
    """M&M Review Dashboard for agent incidents"""

    def __init__(self, db_path: str = "agent_registry.db"):
        self.db = AgentRegistryDB(db_path)
        self.monitoring = MonitoringSystem(db_path)

    def create_review(
        self,
        agent_id: str,
        reviewer: str,
        review_date: Optional[str] = None
    ) -> int:
        """Create a new M&M review"""
        return self.db.create_mm_review(agent_id, reviewer, review_date)

    def get_review_candidates(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get agents that need M&M review"""
        candidates = []
        
        # Get all active agents
        agents = self.db.list_agents(status='active')
        
        for agent_data in agents:
            agent_id = agent_data['agent_id']
            
            # Count incidents
            violations = self.db.get_violations(agent_id=agent_id, days=days, resolved=False)
            
            # Get metrics for near-misses
            anomalies = self.monitoring.detect_anomalies(agent_id, days)
            
            # Get escalations
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM escalations
                WHERE agent_id = ?
                AND timestamp >= datetime('now', '-' || ? || ' days')
            """, (agent_id, days))
            escalation_count = cursor.fetchone()[0]
            
            # Check if review is needed
            needs_review = (
                len(violations) > 0 or
                len(anomalies) > 2 or
                escalation_count > 5
            )
            
            if needs_review:
                candidates.append({
                    'agent_id': agent_id,
                    'title': agent_data['title'],
                    'environment': agent_data['environment_name'],
                    'violations': len(violations),
                    'anomalies': len(anomalies),
                    'escalations': escalation_count,
                    'priority': self._calculate_priority(
                        len(violations),
                        len(anomalies),
                        escalation_count
                    )
                })
        
        # Sort by priority
        candidates.sort(key=lambda x: x['priority'], reverse=True)
        
        return candidates

    def _calculate_priority(
        self,
        violations: int,
        anomalies: int,
        escalations: int
    ) -> int:
        """Calculate review priority score"""
        return (violations * 10) + (anomalies * 5) + (escalations * 2)

    def generate_review_report(
        self,
        agent_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate comprehensive review report for an agent"""
        agent = self.db.get_agent(agent_id)
        
        if not agent:
            return {'error': f'Agent not found: {agent_id}'}
        
        # Get violations
        violations = self.db.get_violations(agent_id=agent_id, days=days)
        
        # Categorize violations
        critical_violations = [v for v in violations if v['severity'] == 'high']
        resolved_violations = [v for v in violations if v['resolved']]
        
        # Get escalations
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM escalations
            WHERE agent_id = ?
            AND timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp DESC
        """, (agent_id, days))
        escalations = [dict(row) for row in cursor.fetchall()]
        
        # Get rollback events (from audit logs)
        audit_trail = self.monitoring.get_audit_trail(
            agent_id=agent_id,
            event_type='rollback',
            days=days
        )
        
        # Get anomalies
        anomalies = self.monitoring.detect_anomalies(agent_id, days)
        
        # Get tool failure patterns
        tool_stats = self.monitoring.get_tool_usage_stats(agent_id, days)
        failed_tools = [
            t for t in tool_stats.get('tool_stats', [])
            if t['success_rate'] < 0.9 and t['total_calls'] > 5
        ]
        
        # Generate insights
        insights = self._generate_insights(
            violations,
            escalations,
            anomalies,
            failed_tools
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            agent,
            violations,
            escalations,
            anomalies
        )
        
        return {
            'agent_id': agent_id,
            'title': agent['title'],
            'environment': agent['environment_name'],
            'review_period': {
                'days': days,
                'start': (datetime.now() - timedelta(days=days)).isoformat(),
                'end': datetime.now().isoformat()
            },
            'summary': {
                'total_violations': len(violations),
                'critical_violations': len(critical_violations),
                'resolved_violations': len(resolved_violations),
                'escalations': len(escalations),
                'rollbacks': len(audit_trail),
                'anomalies': len(anomalies)
            },
            'violations': violations[:20],  # Top 20
            'escalations': escalations[:20],
            'rollbacks': audit_trail,
            'anomalies': anomalies,
            'failed_tools': failed_tools,
            'insights': insights,
            'recommendations': recommendations,
            'generated_at': datetime.now().isoformat()
        }

    def _generate_insights(
        self,
        violations: List[Dict],
        escalations: List[Dict],
        anomalies: List[Dict],
        failed_tools: List[Dict]
    ) -> List[str]:
        """Generate insights from the data"""
        insights = []
        
        if violations:
            # Find patterns in violations
            violation_types = defaultdict(int)
            for v in violations:
                violation_types[v['violation_type']] += 1
            
            most_common = max(violation_types.items(), key=lambda x: x[1])
            insights.append(
                f"Most common violation: {most_common[0]} ({most_common[1]} occurrences)"
            )
        
        if escalations:
            # Find escalation patterns
            triggers = defaultdict(int)
            for e in escalations:
                triggers[e['trigger']] += 1
            
            if triggers:
                most_common_trigger = max(triggers.items(), key=lambda x: x[1])
                insights.append(
                    f"Most frequent escalation trigger: {most_common_trigger[0]} "
                    f"({most_common_trigger[1]} times)"
                )
        
        if failed_tools:
            insights.append(
                f"{len(failed_tools)} tool(s) showing below-target success rates"
            )
        
        if anomalies:
            high_severity = [a for a in anomalies if a.get('severity') == 'high']
            if high_severity:
                insights.append(
                    f"{len(high_severity)} high-severity anomalies detected"
                )
        
        if not insights:
            insights.append("No significant patterns detected")
        
        return insights

    def _generate_recommendations(
        self,
        agent: Dict,
        violations: List[Dict],
        escalations: List[Dict],
        anomalies: List[Dict]
    ) -> List[Dict[str, str]]:
        """Generate recommendations based on review"""
        recommendations = []
        
        # Check for high violation rate
        if len(violations) > 10:
            recommendations.append({
                'type': 'guardrails',
                'priority': 'high',
                'action': 'Review and strengthen guardrails',
                'rationale': f'{len(violations)} violations in review period exceeds threshold'
            })
        
        # Check for frequent escalations
        if len(escalations) > 5:
            recommendations.append({
                'type': 'autonomy',
                'priority': 'medium',
                'action': 'Consider reducing autonomy level',
                'rationale': f'{len(escalations)} escalations suggest agent needs more oversight'
            })
        
        # Check for performance issues
        exec_time_anomalies = [
            a for a in anomalies 
            if a.get('type') == 'execution_time_spike'
        ]
        if len(exec_time_anomalies) > 3:
            recommendations.append({
                'type': 'performance',
                'priority': 'medium',
                'action': 'Investigate performance degradation',
                'rationale': 'Multiple execution time spikes detected'
            })
        
        # Check for tool issues
        tool_anomalies = [
            a for a in anomalies 
            if a.get('type') == 'low_tool_success_rate'
        ]
        if tool_anomalies:
            recommendations.append({
                'type': 'tools',
                'priority': 'medium',
                'action': 'Review tool configurations and access',
                'rationale': f"{len(tool_anomalies)} tool(s) with low success rates"
            })
        
        # General recommendations
        if not recommendations:
            recommendations.append({
                'type': 'general',
                'priority': 'low',
                'action': 'Continue monitoring',
                'rationale': 'Agent operating within normal parameters'
            })
        
        return recommendations

    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Get monthly M&M summary"""
        # Calculate date range
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        days_in_month = (end_date - start_date).days
        
        # Get all active agents
        agents = self.db.list_agents(status='active')
        
        agent_summaries = []
        total_violations = 0
        total_escalations = 0
        total_rollbacks = 0
        
        for agent_data in agents:
            agent_id = agent_data['agent_id']
            
            # Get violations
            violations = self.db.get_violations(agent_id=agent_id, days=days_in_month)
            
            # Get escalations
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM escalations
                WHERE agent_id = ?
                AND timestamp >= ?
                AND timestamp < ?
            """, (agent_id, start_date.isoformat(), end_date.isoformat()))
            escalation_count = cursor.fetchone()[0]
            
            # Get rollbacks
            cursor.execute("""
                SELECT COUNT(*) FROM audit_logs
                WHERE agent_id = ?
                AND event_type = 'rollback'
                AND timestamp >= ?
                AND timestamp < ?
            """, (agent_id, start_date.isoformat(), end_date.isoformat()))
            rollback_count = cursor.fetchone()[0]
            
            total_violations += len(violations)
            total_escalations += escalation_count
            total_rollbacks += rollback_count
            
            agent_summaries.append({
                'agent_id': agent_id,
                'title': agent_data['title'],
                'violations': len(violations),
                'escalations': escalation_count,
                'rollbacks': rollback_count
            })
        
        return {
            'year': year,
            'month': month,
            'total_agents': len(agents),
            'total_violations': total_violations,
            'total_escalations': total_escalations,
            'total_rollbacks': total_rollbacks,
            'agent_summaries': agent_summaries,
            'generated_at': datetime.now().isoformat()
        }

    def export_review(self, agent_id: str, filepath: str, days: int = 30):
        """Export M&M review to file"""
        report = self.generate_review_report(agent_id, days)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

    def print_review_summary(self, agent_id: str, days: int = 30):
        """Print human-readable review summary"""
        report = self.generate_review_report(agent_id, days)
        
        print(f"\n{'=' * 80}")
        print(f"M&M REVIEW REPORT")
        print(f"{'=' * 80}")
        print(f"\nAgent: {report['title']} ({report['agent_id']})")
        print(f"Environment: {report['environment']}")
        print(f"Period: {days} days\n")
        
        print(f"{'—' * 80}")
        print("SUMMARY")
        print(f"{'—' * 80}")
        summary = report['summary']
        print(f"  Violations: {summary['total_violations']} "
              f"({summary['critical_violations']} critical, "
              f"{summary['resolved_violations']} resolved)")
        print(f"  Escalations: {summary['escalations']}")
        print(f"  Rollbacks: {summary['rollbacks']}")
        print(f"  Anomalies: {summary['anomalies']}\n")
        
        print(f"{'—' * 80}")
        print("INSIGHTS")
        print(f"{'—' * 80}")
        for insight in report['insights']:
            print(f"  • {insight}")
        print()
        
        print(f"{'—' * 80}")
        print("RECOMMENDATIONS")
        print(f"{'—' * 80}")
        for rec in report['recommendations']:
            priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
            emoji = priority_emoji.get(rec['priority'], '⚪')
            print(f"\n  {emoji} [{rec['priority'].upper()}] {rec['action']}")
            print(f"     Type: {rec['type']}")
            print(f"     Rationale: {rec['rationale']}")
        
        print(f"\n{'=' * 80}\n")

    def close(self):
        """Close database connection"""
        self.db.close()
        self.monitoring.close()
