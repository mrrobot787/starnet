#!/usr/bin/env python3
"""
Agent Registry System Demo

Demonstrates the full capabilities of the AML University Agent Registry.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.registry import (
    AgentRegistryService,
    AgentRuntime,
    MonitoringSystem,
    MMReviewDashboard,
    GuardrailViolation
)


def demo_registration():
    """Demo: Register agents"""
    print("\n" + "="*80)
    print("DEMO 1: Agent Registration")
    print("="*80)
    
    service = AgentRegistryService("demo_registry.db")
    
    # Register agents from examples directory
    examples_dir = Path(__file__).parent / "agents"
    
    if examples_dir.exists():
        print(f"\n📁 Registering agents from {examples_dir}...")
        results = service.register_from_directory(str(examples_dir), user="demo")
        
        success_count = sum(1 for (success, _, _) in results.values() if success)
        print(f"✅ Registered {success_count}/{len(results)} agents")
        
        # Show any failures
        for name, (success, _, errors) in results.items():
            if not success:
                print(f"\n❌ {name}:")
                for error in errors:
                    print(f"   {error}")
    else:
        print(f"⚠️  Examples directory not found: {examples_dir}")
        print("   Using a sample agent instead...")
        
        # Create a simple agent
        sample_agent = {
            "agent_id": "demo-agent",
            "title": "Demo Agent",
            "version": "1.0.0",
            "owner": {"unit": "Demo Lab", "contact": "demo@aml.university"},
            "environment": {
                "name": "Coding Lab",
                "runtime": ["python3.11"],
                "network": {"egress": ["intranet"], "ingress": ["none"], "restrictions": []}
            },
            "tools": [
                {
                    "name": "test_tool",
                    "capabilities": ["read"],
                    "limits": {},
                    "scopes": [],
                    "policy": {"allow_pii": False}
                }
            ],
            "system_prompt": "You are a demo agent for testing purposes.",
            "reasoning_overlays": ["Deterministic"],
            "autonomy": {"level": 1, "description": "assist"},
            "guardrails": {
                "red_lines": ["no dangerous operations"],
                "escalation": {"triggers": ["error"], "to": "admin"},
                "rollback": {"supported": True}
            },
            "audit": {"logging": ["actions"]}
        }
        
        success, db_id, errors = service.register_agent(sample_agent, "demo")
        if success:
            print(f"✅ Registered demo agent (ID: {db_id})")
        else:
            print(f"❌ Failed to register: {errors}")
    
    service.close()


def demo_listing_and_filtering():
    """Demo: List and filter agents"""
    print("\n" + "="*80)
    print("DEMO 2: Listing and Filtering")
    print("="*80)
    
    service = AgentRegistryService("demo_registry.db")
    
    # List all agents
    all_agents = service.list_agents()
    print(f"\n📋 Total agents: {len(all_agents)}")
    
    for agent in all_agents[:5]:  # Show first 5
        print(f"   - {agent.agent_id}: {agent.title}")
        print(f"     Environment: {agent.environment.name}, Autonomy: {agent.autonomy.level}")
    
    # Filter by environment
    coding_agents = service.list_agents(environment="Coding Lab")
    print(f"\n🔬 Agents in Coding Lab: {len(coding_agents)}")
    for agent in coding_agents:
        print(f"   - {agent.agent_id}")
    
    # High-risk agents
    high_risk = service.get_high_risk_agents()
    print(f"\n⚠️  High-risk agents: {len(high_risk)}")
    for agent in high_risk:
        print(f"   - {agent['agent_id']}: Autonomy {agent['autonomy_level']}")
    
    service.close()


def demo_runtime_guardrails():
    """Demo: Runtime guardrails"""
    print("\n" + "="*80)
    print("DEMO 3: Runtime Guardrails")
    print("="*80)
    
    service = AgentRegistryService("demo_registry.db")
    agents = service.list_agents()
    
    if not agents:
        print("⚠️  No agents registered for demo")
        service.close()
        return
    
    agent = agents[0]
    print(f"\n🛡️  Testing guardrails for: {agent.agent_id}")
    
    runtime = AgentRuntime(agent, "demo_registry.db")
    
    # Test 1: Safe action
    print("\n✅ Test 1: Safe action")
    try:
        def safe_function(x):
            return x * 2
        
        result = runtime.execute_with_guardrails(
            safe_function,
            5,
            action_name="safe_calculation",
            context={}
        )
        print(f"   Result: {result}")
        print(f"   Execution count: {runtime.execution_count}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Guardrail violation
    print("\n❌ Test 2: Guardrail violation")
    try:
        runtime.check_guardrails("dangerous operations", {})
        print("   No violation detected (unexpected)")
    except GuardrailViolation as e:
        print(f"   Violation caught: {e.red_line}")
        print(f"   Violation count: {runtime.violation_count}")
    
    # Test 3: Tool permission
    print("\n🔧 Test 3: Tool permissions")
    for tool in agent.tools[:2]:  # Test first 2 tools
        for cap in tool.capabilities:
            has_perm = runtime.check_tool_permission(tool.name, cap)
            status = "✅" if has_perm else "❌"
            print(f"   {status} {tool.name}.{cap}")
    
    runtime.close()
    service.close()


def demo_monitoring():
    """Demo: Monitoring and metrics"""
    print("\n" + "="*80)
    print("DEMO 4: Monitoring & Metrics")
    print("="*80)
    
    monitor = MonitoringSystem("demo_registry.db")
    
    # System health
    print("\n🏥 System Health:")
    health = monitor.get_system_health()
    print(f"   Status: {health['health_status']}")
    print(f"   Total agents: {health['total_agents']}")
    print(f"   Active agents: {health['active_agents']}")
    print(f"   Violations (24h): {health['violations_24h']}")
    print(f"   Unresolved: {health['unresolved_violations']}")
    
    # Violation summary
    print("\n⚠️  Violation Summary (last 30 days):")
    violations = monitor.get_violation_summary(days=30)
    print(f"   Total violations: {violations['total_violations']}")
    if violations['by_type']:
        print("   By type:")
        for vtype, count in violations['by_type'].items():
            print(f"      - {vtype}: {count}")
    
    # Tool usage
    print("\n🔧 Tool Usage:")
    tool_stats = monitor.get_tool_usage_stats(days=30)
    if tool_stats['tool_stats']:
        for stat in tool_stats['tool_stats'][:5]:
            print(f"   - {stat['tool_name']}.{stat['capability']}: "
                  f"{stat['total_calls']} calls, "
                  f"{stat['success_rate']:.1%} success")
    else:
        print("   No tool usage data yet")
    
    monitor.close()


def demo_mm_review():
    """Demo: M&M Review"""
    print("\n" + "="*80)
    print("DEMO 5: M&M (Morbidity & Mortality) Review")
    print("="*80)
    
    mm = MMReviewDashboard("demo_registry.db")
    
    # Get review candidates
    print("\n🏥 Agents needing M&M review:")
    candidates = mm.get_review_candidates(days=30)
    
    if candidates:
        for candidate in candidates[:5]:
            print(f"\n   {candidate['agent_id']} (Priority: {candidate['priority']})")
            print(f"      Violations: {candidate['violations']}")
            print(f"      Anomalies: {candidate['anomalies']}")
            print(f"      Escalations: {candidate['escalations']}")
    else:
        print("   ✅ No agents need review - all operating normally")
    
    # Generate report for first agent (if any)
    service = AgentRegistryService("demo_registry.db")
    agents = service.list_agents()
    
    if agents:
        agent = agents[0]
        print(f"\n📊 Generating review report for: {agent.agent_id}")
        mm.print_review_summary(agent.agent_id, days=30)
    
    service.close()
    mm.close()


def demo_lifecycle():
    """Demo: Agent lifecycle management"""
    print("\n" + "="*80)
    print("DEMO 6: Agent Lifecycle Management")
    print("="*80)
    
    service = AgentRegistryService("demo_registry.db")
    agents = service.list_agents()
    
    if not agents:
        print("⚠️  No agents for lifecycle demo")
        service.close()
        return
    
    agent = agents[0]
    agent_id = agent.agent_id
    
    print(f"\n📋 Agent: {agent_id}")
    print(f"   Current status: {agent.metadata.status if agent.metadata else 'unknown'}")
    
    # Approval workflow
    print("\n🔄 Approval workflow:")
    success, errors = service.approve_agent(agent_id, user="demo")
    if success:
        print("   ✅ Approved (advanced status)")
    else:
        print(f"   ⚠️  {errors}")
    
    # Get updated agent
    updated_agent = service.get_agent(agent_id)
    print(f"   New status: {updated_agent.metadata.status if updated_agent.metadata else 'unknown'}")
    
    service.close()


def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("AML UNIVERSITY AGENT REGISTRY - COMPREHENSIVE DEMO")
    print("="*80)
    
    try:
        demo_registration()
        demo_listing_and_filtering()
        demo_runtime_guardrails()
        demo_monitoring()
        demo_mm_review()
        demo_lifecycle()
        
        print("\n" + "="*80)
        print("DEMO COMPLETE")
        print("="*80)
        print("\n✅ All demonstrations completed successfully!")
        print("\n💡 Next steps:")
        print("   - Explore the CLI: python -m agents.registry.cli --help")
        print("   - Start the API: python -m agents.registry.api")
        print("   - Run tests: pytest tests/test_agent_registry.py -v")
        print("   - Read docs: agents/registry/README.md")
        print()
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
