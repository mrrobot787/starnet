"""
Agent Registry Database Models

SQLite database for storing agent registrations, audit logs, and runtime metrics.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json


class AgentRegistryDB:
    """Database for agent registry"""

    def __init__(self, db_path: str = "agent_registry.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn = None
        self.initialize()

    def initialize(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()

        # Agent registrations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                version TEXT NOT NULL,
                owner_unit TEXT NOT NULL,
                owner_contact TEXT NOT NULL,
                environment_name TEXT NOT NULL,
                autonomy_level INTEGER NOT NULL,
                status TEXT DEFAULT 'draft',
                registration_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                UNIQUE(agent_id, version)
            )
        """)

        # Audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user TEXT,
                FOREIGN KEY (agent_id) REFERENCES agent_registrations(agent_id)
            )
        """)

        # Runtime metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runtime_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agent_registrations(agent_id)
            )
        """)

        # Guardrail violations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guardrail_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                red_line TEXT NOT NULL,
                context TEXT,
                severity TEXT DEFAULT 'high',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                resolution_note TEXT,
                FOREIGN KEY (agent_id) REFERENCES agent_registrations(agent_id)
            )
        """)

        # Tool usage logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                capability TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                duration_ms INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agent_registrations(agent_id)
            )
        """)

        # M&M reviews table (Morbidity & Mortality - incident reviews)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mm_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                review_date DATE NOT NULL,
                reviewer TEXT NOT NULL,
                incidents_count INTEGER DEFAULT 0,
                near_misses_count INTEGER DEFAULT 0,
                rollbacks_count INTEGER DEFAULT 0,
                findings TEXT,
                recommendations TEXT,
                status TEXT DEFAULT 'open',
                FOREIGN KEY (agent_id) REFERENCES agent_registrations(agent_id)
            )
        """)

        # Escalations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS escalations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                trigger TEXT NOT NULL,
                escalated_to TEXT NOT NULL,
                context TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                resolution_time TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agent_registrations(agent_id)
            )
        """)

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_status ON agent_registrations(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_logs(agent_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metrics_agent ON runtime_metrics(agent_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_violations_agent ON guardrail_violations(agent_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_usage_agent ON tool_usage(agent_id)"
        )

        self.conn.commit()

    def register_agent(self, registration_data: Dict[str, Any], created_by: str = "") -> int:
        """
        Register a new agent
        
        Args:
            registration_data: Complete agent registration dictionary
            created_by: User who created the registration
            
        Returns:
            Database ID of the registration
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_registrations 
            (agent_id, title, version, owner_unit, owner_contact, 
             environment_name, autonomy_level, registration_data, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            registration_data['agent_id'],
            registration_data['title'],
            registration_data['version'],
            registration_data['owner']['unit'],
            registration_data['owner']['contact'],
            registration_data['environment']['name'],
            registration_data['autonomy']['level'],
            json.dumps(registration_data),
            created_by
        ))
        
        self.conn.commit()
        
        # Log the registration
        self.log_audit_event(
            registration_data['agent_id'],
            'registration',
            {'version': registration_data['version']},
            created_by
        )
        
        return cursor.lastrowid

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent registration by ID"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM agent_registrations WHERE agent_id = ?",
            (agent_id,)
        )
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            data['registration_data'] = json.loads(data['registration_data'])
            return data
        return None

    def list_agents(
        self,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        autonomy_level: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List agents with optional filters"""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM agent_registrations WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if environment:
            query += " AND environment_name = ?"
            params.append(environment)
        
        if autonomy_level is not None:
            query += " AND autonomy_level = ?"
            params.append(autonomy_level)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            data = dict(row)
            data['registration_data'] = json.loads(data['registration_data'])
            results.append(data)
        
        return results

    def update_agent_status(self, agent_id: str, status: str, user: str = ""):
        """Update agent status"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE agent_registrations 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE agent_id = ?
        """, (status, agent_id))
        self.conn.commit()
        
        self.log_audit_event(agent_id, 'status_change', {'new_status': status}, user)

    def update_registration(self, registration_data: Dict[str, Any]):
        """
        Persist an updated registration for an existing agent.

        Rewrites the stored JSON payload and keeps the denormalized columns
        (title, version, owner, environment_name, autonomy_level) in sync with it,
        so filters such as list_agents(environment=...) see the new state.

        Raises:
            LookupError: if no registration exists for the agent_id
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE agent_registrations
            SET title = ?, version = ?, owner_unit = ?, owner_contact = ?,
                environment_name = ?, autonomy_level = ?, registration_data = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE agent_id = ?
        """, (
            registration_data['title'],
            registration_data['version'],
            registration_data['owner']['unit'],
            registration_data['owner']['contact'],
            registration_data['environment']['name'],
            registration_data['autonomy']['level'],
            json.dumps(registration_data),
            registration_data['agent_id']
        ))
        if cursor.rowcount != 1:
            self.conn.rollback()
            raise LookupError(f"Agent not found: {registration_data['agent_id']}")
        self.conn.commit()

    def log_audit_event(
        self,
        agent_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
        user: str = ""
    ):
        """Log an audit event"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (agent_id, event_type, event_data, user)
            VALUES (?, ?, ?, ?)
        """, (
            agent_id,
            event_type,
            json.dumps(event_data) if event_data else None,
            user
        ))
        self.conn.commit()

    def log_metric(
        self,
        agent_id: str,
        metric_name: str,
        metric_value: float,
        metric_unit: str = ""
    ):
        """Log a runtime metric"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO runtime_metrics (agent_id, metric_name, metric_value, metric_unit)
            VALUES (?, ?, ?, ?)
        """, (agent_id, metric_name, metric_value, metric_unit))
        self.conn.commit()

    def log_violation(
        self,
        agent_id: str,
        violation_type: str,
        red_line: str,
        context: str = "",
        severity: str = "high"
    ) -> int:
        """Log a guardrail violation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO guardrail_violations 
            (agent_id, violation_type, red_line, context, severity)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, violation_type, red_line, context, severity))
        self.conn.commit()
        
        # Also log as audit event
        self.log_audit_event(agent_id, 'violation', {
            'type': violation_type,
            'red_line': red_line,
            'severity': severity
        })
        
        return cursor.lastrowid

    def log_tool_usage(
        self,
        agent_id: str,
        tool_name: str,
        capability: str,
        success: bool,
        duration_ms: Optional[int] = None
    ):
        """Log tool usage"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO tool_usage (agent_id, tool_name, capability, success, duration_ms)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, tool_name, capability, success, duration_ms))
        self.conn.commit()

    def log_escalation(
        self,
        agent_id: str,
        trigger: str,
        escalated_to: str,
        context: str = ""
    ) -> int:
        """Log an escalation event"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO escalations (agent_id, trigger, escalated_to, context)
            VALUES (?, ?, ?, ?)
        """, (agent_id, trigger, escalated_to, context))
        self.conn.commit()
        
        return cursor.lastrowid

    def create_mm_review(
        self,
        agent_id: str,
        reviewer: str,
        review_date: Optional[str] = None
    ) -> int:
        """Create a new M&M review"""
        if review_date is None:
            review_date = datetime.now().date().isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO mm_reviews (agent_id, review_date, reviewer)
            VALUES (?, ?, ?)
        """, (agent_id, review_date, reviewer))
        self.conn.commit()
        
        return cursor.lastrowid

    def get_agent_metrics(
        self,
        agent_id: str,
        metric_name: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get agent metrics"""
        cursor = self.conn.cursor()
        
        query = """
            SELECT * FROM runtime_metrics 
            WHERE agent_id = ? 
            AND timestamp >= datetime('now', '-' || ? || ' days')
        """
        params = [agent_id, days]
        
        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_violations(
        self,
        agent_id: Optional[str] = None,
        resolved: Optional[bool] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get guardrail violations"""
        cursor = self.conn.cursor()
        
        query = """
            SELECT * FROM guardrail_violations 
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
        """
        params = [days]
        
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        
        if resolved is not None:
            query += " AND resolved = ?"
            params.append(1 if resolved else 0)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_audit_trail(
        self,
        agent_id: Optional[str] = None,
        event_type: Optional[str] = None,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit trail"""
        cursor = self.conn.cursor()
        
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

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
