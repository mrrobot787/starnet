import copy
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from registry import AgentRegistryService  # noqa: E402

SAMPLE_AGENT = {
    "agent_id": "rotation-test-agent",
    "title": "Rotation Test Agent",
    "version": "1.0.0",
    "owner": {"unit": "Test Lab", "contact": "test@aml.university"},
    "environment": {
        "name": "Coding Lab",
        "runtime": ["python3.11"],
        "network": {"egress": ["intranet"], "ingress": ["none"], "restrictions": []},
    },
    "tools": [
        {
            "name": "code_reader",
            "capabilities": ["read"],
            "limits": {},
            "scopes": [],
            "policy": {"allow_pii": False},
        }
    ],
    "system_prompt": "You are a test agent used to verify ward rotation.",
    "reasoning_overlays": ["Deterministic"],
    "autonomy": {"level": 1, "description": "assist"},
    "guardrails": {
        "red_lines": ["no dangerous operations"],
        "escalation": {"triggers": ["error"], "to": "admin"},
        "rollback": {"supported": True, "procedure": "Restore the previous registration version."},
    },
    "audit": {"logging": ["actions"]},
}

NEW_TOOLS = [
    {
        "name": "ward_dashboard",
        "capabilities": ["read", "write"],
        "limits": {},
        "scopes": [],
        "policy": {"allow_pii": False},
    }
]


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "registry.db")


def _register(db_path):
    service = AgentRegistryService(db_path)
    ok, _, errors = service.register_agent(copy.deepcopy(SAMPLE_AGENT), created_by="test")
    assert ok, errors
    return service


def test_rotation_is_persisted(db_path):
    service = _register(db_path)
    ok, errors = service.rotate_agent(SAMPLE_AGENT["agent_id"], "Data Engineering Bay", NEW_TOOLS, user="test")
    assert ok, errors
    service.close()

    reopened = AgentRegistryService(db_path)
    agent = reopened.get_agent(SAMPLE_AGENT["agent_id"])
    assert agent.environment.name == "Data Engineering Bay"
    assert [t.name for t in agent.tools] == ["ward_dashboard"]
    assert agent.version == "1.1.0"
    assert [a.agent_id for a in reopened.list_agents(environment="Data Engineering Bay")] == [SAMPLE_AGENT["agent_id"]]
    assert reopened.list_agents(environment="Coding Lab") == []
    reopened.close()

    row = sqlite3.connect(db_path).execute(
        "SELECT environment_name, version FROM agent_registrations WHERE agent_id = ?",
        (SAMPLE_AGENT["agent_id"],),
    ).fetchone()
    assert row == ("Data Engineering Bay", "1.1.0")


def test_rotation_audit_records_previous_state(db_path):
    service = _register(db_path)
    ok, errors = service.rotate_agent(SAMPLE_AGENT["agent_id"], "Data Engineering Bay", NEW_TOOLS, user="test")
    assert ok, errors
    event = sqlite3.connect(db_path).execute(
        "SELECT event_data FROM audit_logs WHERE agent_id = ? AND event_type = 'rotation'",
        (SAMPLE_AGENT["agent_id"],),
    ).fetchone()
    assert event is not None
    assert '"previous_environment": "Coding Lab"' in event[0]
    assert '"new_version": "1.1.0"' in event[0]
    service.close()


def test_rotation_of_unknown_agent_fails(db_path):
    service = AgentRegistryService(db_path)
    ok, errors = service.rotate_agent("missing-agent", "Data Engineering Bay", NEW_TOOLS)
    assert not ok
    assert errors == ["Agent not found: missing-agent"]
    service.close()


def test_invalid_rotation_leaves_stored_state_unchanged(db_path):
    service = _register(db_path)
    ok, errors = service.rotate_agent(SAMPLE_AGENT["agent_id"], "Data Engineering Bay", [{"name": "bad_tool", "capabilities": ["teleport"]}])
    assert not ok
    agent = service.get_agent(SAMPLE_AGENT["agent_id"])
    assert agent.environment.name == "Coding Lab"
    assert agent.version == "1.0.0"
    service.close()
