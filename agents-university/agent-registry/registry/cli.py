#!/usr/bin/env python3
"""
Agent Registry CLI

Command-line interface for managing the AML University Agent Registry.
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Optional
from tabulate import tabulate

try:
    from . import service, validator, models, database
    from .service import AgentRegistryService
    from .validator import AgentValidator
    from .models import AgentRegistration
except ImportError:
    # Fallback for direct execution
    import service
    import validator
    import models
    import database
    from service import AgentRegistryService
    from validator import AgentValidator
    from models import AgentRegistration


class RegistryCLI:
    """CLI for agent registry management"""

    def __init__(self, db_path: str = "agent_registry.db"):
        self.service = AgentRegistryService(db_path)

    def register(self, filepath: str, user: str = "") -> int:
        """Register agent from file"""
        print(f"📝 Registering agent from {filepath}...")
        
        success, db_id, errors = self.service.register_from_file(filepath, user)
        
        if success:
            print(f"✅ Agent registered successfully (ID: {db_id})")
            return 0
        else:
            print(f"❌ Registration failed:")
            for error in errors:
                print(f"   - {error}")
            return 1

    def register_directory(self, dirpath: str, user: str = "") -> int:
        """Register all agents from directory"""
        print(f"📁 Registering agents from {dirpath}...")
        
        results = self.service.register_from_directory(dirpath, user)
        
        success_count = sum(1 for (success, _, _) in results.values() if success)
        total = len(results)
        
        print(f"\n✅ Registered {success_count}/{total} agents")
        
        # Show failures
        failures = [(name, errors) for name, (success, _, errors) in results.items() if not success]
        if failures:
            print("\n❌ Failed registrations:")
            for name, errors in failures:
                print(f"\n{name}:")
                for error in errors:
                    print(f"  - {error}")
        
        return 0 if success_count == total else 1

    def list_agents(
        self,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        autonomy: Optional[int] = None
    ) -> int:
        """List agents"""
        agents = self.service.list_agents(status, environment, autonomy)
        
        if not agents:
            print("No agents found matching criteria")
            return 0
        
        # Format as table
        rows = []
        for agent in agents:
            rows.append([
                agent.agent_id,
                agent.title,
                agent.version,
                agent.environment.name,
                agent.autonomy.level,
                agent.metadata.status if agent.metadata else "unknown"
            ])
        
        headers = ["ID", "Title", "Version", "Environment", "Autonomy", "Status"]
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        print(f"\nTotal: {len(agents)} agent(s)")
        
        return 0

    def show(self, agent_id: str) -> int:
        """Show agent details"""
        agent = self.service.get_agent(agent_id)
        
        if not agent:
            print(f"❌ Agent not found: {agent_id}")
            return 1
        
        print(f"\n{'=' * 60}")
        print(f"Agent: {agent.title} ({agent.agent_id})")
        print(f"{'=' * 60}\n")
        
        print(f"Version: {agent.version}")
        print(f"Owner: {agent.owner.unit} ({agent.owner.contact})")
        print(f"Environment: {agent.environment.name}")
        print(f"Autonomy Level: {agent.autonomy.level} ({agent.autonomy.description})")
        
        if agent.metadata:
            print(f"Status: {agent.metadata.status}")
            print(f"Created: {agent.metadata.created_at}")
        
        print(f"\nTools ({len(agent.tools)}):")
        for tool in agent.tools:
            caps = ", ".join(tool.capabilities)
            print(f"  - {tool.name}: {caps}")
        
        print(f"\nGuardrails:")
        print(f"  Red lines: {len(agent.guardrails.red_lines)}")
        for red_line in agent.guardrails.red_lines:
            print(f"    - {red_line}")
        
        if agent.guardrails.escalation:
            print(f"  Escalation to: {agent.guardrails.escalation.to}")
        
        print(f"\nKPIs: {', '.join(agent.kpis)}")
        
        print(f"\n{'=' * 60}\n")
        
        return 0

    def validate(self, filepath: Optional[str] = None, dirpath: Optional[str] = None) -> int:
        """Validate agent registration(s)"""
        val = AgentValidator()
        
        if filepath:
            print(f"🔍 Validating {filepath}...")
            is_valid, errors = val.validate_file(filepath)
            
            if is_valid:
                print("✅ Validation passed")
                return 0
            else:
                print("❌ Validation failed:")
                for error in errors:
                    print(f"   - {error}")
                return 1
        
        elif dirpath:
            print(f"🔍 Validating agents in {dirpath}...")
            results = val.validate_directory(dirpath)
            summary = val.get_validation_summary(results)
            print(summary)
            
            invalid_count = sum(1 for (is_valid, _) in results.values() if not is_valid)
            return 0 if invalid_count == 0 else 1
        
        else:
            print("❌ Must provide either --file or --dir")
            return 1

    def update_status(self, agent_id: str, status: str, user: str = "") -> int:
        """Update agent status"""
        print(f"🔄 Updating {agent_id} status to {status}...")
        
        success, errors = self.service.update_status(agent_id, status, user)
        
        if success:
            print(f"✅ Status updated successfully")
            return 0
        else:
            print(f"❌ Update failed:")
            for error in errors:
                print(f"   - {error}")
            return 1

    def approve(self, agent_id: str, user: str = "") -> int:
        """Approve agent"""
        print(f"✅ Approving {agent_id}...")
        
        success, errors = self.service.approve_agent(agent_id, user)
        
        if success:
            print(f"✅ Agent approved")
            return 0
        else:
            print(f"❌ Approval failed:")
            for error in errors:
                print(f"   - {error}")
            return 1

    def deprecate(self, agent_id: str, user: str = "") -> int:
        """Deprecate agent"""
        print(f"⚠️  Deprecating {agent_id}...")
        
        success, errors = self.service.deprecate_agent(agent_id, user)
        
        if success:
            print(f"✅ Agent deprecated")
            return 0
        else:
            print(f"❌ Deprecation failed:")
            for error in errors:
                print(f"   - {error}")
            return 1

    def health(self, agent_id: str, days: int = 30) -> int:
        """Show agent health metrics"""
        health = self.service.get_agent_health(agent_id, days)
        
        print(f"\n{'=' * 60}")
        print(f"Health Report: {agent_id} (last {days} days)")
        print(f"{'=' * 60}\n")
        
        print(f"Metrics collected: {health['metrics_count']}")
        print(f"Violations (unresolved): {health['violations_count']}")
        
        if health['unresolved_violations']:
            print("\n⚠️  Unresolved Violations:")
            for violation in health['unresolved_violations']:
                print(f"  - {violation['violation_type']}: {violation['red_line']}")
                print(f"    @ {violation['timestamp']}")
        
        if health['recent_metrics']:
            print("\nRecent Metrics:")
            for metric in health['recent_metrics'][:5]:
                print(f"  - {metric['metric_name']}: {metric['metric_value']} {metric['metric_unit']}")
        
        print(f"\n{'=' * 60}\n")
        
        return 0

    def roster(self, environment: str) -> int:
        """Show ward roster"""
        agents = self.service.get_environment_roster(environment)
        
        print(f"\n{'=' * 60}")
        print(f"Ward Roster: {environment}")
        print(f"{'=' * 60}\n")
        
        if not agents:
            print("No active agents in this environment")
            return 0
        
        for agent in agents:
            print(f"  - {agent.agent_id}: {agent.title}")
            print(f"    Autonomy: Level {agent.autonomy.level}")
            print(f"    Tools: {', '.join(t.name for t in agent.tools[:3])}...")
            print()
        
        print(f"Total: {len(agents)} agent(s)")
        print(f"{'=' * 60}\n")
        
        return 0

    def high_risk(self) -> int:
        """Show high-risk agents"""
        agents = self.service.get_high_risk_agents()
        
        print(f"\n⚠️  HIGH RISK AGENTS")
        print(f"(Autonomy >= 2 + Internet Access)\n")
        
        if not agents:
            print("No high-risk agents found")
            return 0
        
        rows = []
        for agent in agents:
            rows.append([
                agent['agent_id'],
                agent['title'],
                agent['autonomy_level'],
                agent['environment']
            ])
        
        headers = ["ID", "Title", "Autonomy", "Environment"]
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        print(f"\nTotal: {len(agents)} high-risk agent(s)")
        
        return 0

    def export(self, agent_id: str, output: str) -> int:
        """Export agent to file"""
        print(f"💾 Exporting {agent_id} to {output}...")
        
        success = self.service.export_agent(agent_id, output)
        
        if success:
            print(f"✅ Export successful")
            return 0
        else:
            print(f"❌ Export failed")
            return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="AML University Agent Registry CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s register agent.json
  %(prog)s register-dir ./examples/agents/
  %(prog)s list --status active
  %(prog)s show scholar-r1
  %(prog)s validate --file agent.json
  %(prog)s approve scholar-r1 --user admin
  %(prog)s health scholar-r1 --days 30
  %(prog)s roster "Research Library"
        """
    )
    
    parser.add_argument(
        "--db",
        default="agent_registry.db",
        help="Database path (default: agent_registry.db)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # register
    p_register = subparsers.add_parser("register", help="Register agent from file")
    p_register.add_argument("file", help="Agent registration JSON file")
    p_register.add_argument("--user", default="", help="User performing registration")
    
    # register-dir
    p_register_dir = subparsers.add_parser("register-dir", help="Register agents from directory")
    p_register_dir.add_argument("dir", help="Directory containing agent JSONs")
    p_register_dir.add_argument("--user", default="", help="User performing registration")
    
    # list
    p_list = subparsers.add_parser("list", help="List agents")
    p_list.add_argument("--status", help="Filter by status")
    p_list.add_argument("--environment", help="Filter by environment")
    p_list.add_argument("--autonomy", type=int, help="Filter by autonomy level")
    
    # show
    p_show = subparsers.add_parser("show", help="Show agent details")
    p_show.add_argument("agent_id", help="Agent ID")
    
    # validate
    p_validate = subparsers.add_parser("validate", help="Validate agent registration")
    p_validate.add_argument("--file", help="Agent registration file")
    p_validate.add_argument("--dir", help="Directory of agent registrations")
    
    # update-status
    p_status = subparsers.add_parser("update-status", help="Update agent status")
    p_status.add_argument("agent_id", help="Agent ID")
    p_status.add_argument("status", help="New status")
    p_status.add_argument("--user", default="", help="User performing update")
    
    # approve
    p_approve = subparsers.add_parser("approve", help="Approve agent")
    p_approve.add_argument("agent_id", help="Agent ID")
    p_approve.add_argument("--user", default="", help="User performing approval")
    
    # deprecate
    p_deprecate = subparsers.add_parser("deprecate", help="Deprecate agent")
    p_deprecate.add_argument("agent_id", help="Agent ID")
    p_deprecate.add_argument("--user", default="", help="User performing deprecation")
    
    # health
    p_health = subparsers.add_parser("health", help="Show agent health")
    p_health.add_argument("agent_id", help="Agent ID")
    p_health.add_argument("--days", type=int, default=30, help="Days to look back")
    
    # roster
    p_roster = subparsers.add_parser("roster", help="Show environment roster")
    p_roster.add_argument("environment", help="Environment name")
    
    # high-risk
    subparsers.add_parser("high-risk", help="Show high-risk agents")
    
    # export
    p_export = subparsers.add_parser("export", help="Export agent to file")
    p_export.add_argument("agent_id", help="Agent ID")
    p_export.add_argument("output", help="Output file path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = RegistryCLI(args.db)
    
    try:
        if args.command == "register":
            return cli.register(args.file, args.user)
        elif args.command == "register-dir":
            return cli.register_directory(args.dir, args.user)
        elif args.command == "list":
            return cli.list_agents(args.status, args.environment, args.autonomy)
        elif args.command == "show":
            return cli.show(args.agent_id)
        elif args.command == "validate":
            return cli.validate(args.file, args.dir)
        elif args.command == "update-status":
            return cli.update_status(args.agent_id, args.status, args.user)
        elif args.command == "approve":
            return cli.approve(args.agent_id, args.user)
        elif args.command == "deprecate":
            return cli.deprecate(args.agent_id, args.user)
        elif args.command == "health":
            return cli.health(args.agent_id, args.days)
        elif args.command == "roster":
            return cli.roster(args.environment)
        elif args.command == "high-risk":
            return cli.high_risk()
        elif args.command == "export":
            return cli.export(args.agent_id, args.output)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
