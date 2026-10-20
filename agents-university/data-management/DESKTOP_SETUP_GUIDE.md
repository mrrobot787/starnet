# Desktop Setup Guide - Agent University Data Management System

## One-Click Desktop Integration

This guide will help you set up desktop shortcuts and automation for the Agent University Data Management System.

## Quick Setup (Recommended)

### Step 1: Create Desktop Shortcut

1. **Run the batch file:**
   ```
   Double-click: create_desktop_shortcut.bat
   ```

2. **What this creates:**
   - Desktop shortcut with GUI launcher
   - Quick launch batch files for common operations
   - System initialization scripts
   - Governance check automation

### Step 2: Launch the System

1. **Double-click the desktop shortcut:** `Agent University Data Management`
2. **The GUI will automatically:**
   - Initialize the system
   - Load data source configurations
   - Display system status
   - Provide one-click access to all features

## Available Launch Options

### 🖥️ GUI Interface (Recommended)
- **Desktop Shortcut**: `Agent University Data Management.lnk`
- **Direct Launch**: `quick_launch.bat`
- **Python Command**: `python launch_agent_university.py`

**Features:**
- Real-time system status monitoring
- One-click data source scoring
- Governance compliance dashboard
- Interactive log viewer
- Menu-driven operations

### ⚡ Quick Automation Scripts

1. **System Initialization**
   ```
   initialize_system.bat
   ```
   - Sets up database schema
   - Creates directory structure
   - Loads and scores data sources
   - Generates initial reports

2. **Data Source Scoring**
   ```
   score_data_sources.bat
   ```
   - Runs 4-axis scoring rubric
   - Generates priority report
   - Updates database with scores

3. **Governance Checks**
   ```
   run_governance_checks.bat
   ```
   - GDPR compliance assessment
   - Data quality evaluation
   - Generates compliance dashboard

### 💻 Command Line Interface
```bash
# Initialize system
python main_orchestrator.py init

# Score data sources
python main_orchestrator.py score

# Run governance checks
python main_orchestrator.py governance

# Check system status
python main_orchestrator.py status

# Ingest data from file
python main_orchestrator.py ingest --source-id sharepoint_engineering --data-file data.json
```

## GUI Features Overview

### Main Dashboard
- **System Status**: Real-time health monitoring
- **Data Sources**: Active source count and dataset statistics
- **Last Check**: Timestamp of most recent status update
- **Progress Tracking**: Visual progress bars for operations

### Action Buttons
- **Initialize System**: Complete system setup
- **Score Data Sources**: Run prioritization algorithm
- **Run Governance Checks**: Compliance monitoring
- **Refresh Status**: Update system metrics

### Menu System
- **File Menu**:
  - Open Config: Edit system configuration
  - View Reports: Access generated reports
  - Exit: Close application

- **Tools Menu**:
  - Data Source Manager: Configure data sources (Future)
  - Governance Dashboard: Compliance interface (Future)
  - System Diagnostics: Health check utilities

- **Help Menu**:
  - Documentation: Open README.md
  - About: System information

### Log Viewer
- Real-time operation logging
- Timestamped entries
- Automatic scrolling to latest entries
- Color-coded status messages

## System Requirements

### Required
- **Python 3.7+** with tkinter support
- **Windows 10/11** (for desktop shortcuts)
- **SQLite3** (included with Python)

### Recommended
- **8GB RAM** for large dataset processing
- **10GB free disk space** for data lake storage
- **Network access** for data source connections

### Optional Dependencies
```bash
pip install pandas pyarrow pyyaml matplotlib
```

## Configuration

### System Configuration (`config.json`)
```json
{
  "database_path": "agent_university.db",
  "data_lake_path": "data_lake",
  "datasources_dir": "datasources",
  "log_level": "INFO",
  "safety_gates_enabled": true,
  "double_helix_enabled": true,
  "governance_enabled": true
}
```

### Data Source Configuration
- Edit YAML files in `datasources/` directory
- Each source has complete configuration including:
  - Legal framework and compliance
  - Double Helix section/strand mappings
  - Processing rules and quality controls
  - Security and authentication settings

## Troubleshooting

### Common Issues

1. **"Python not found" error**
   - Ensure Python is installed and in PATH
   - Try: `python --version` in command prompt

2. **"Module not found" errors**
   - Install required dependencies: `pip install -r requirements.txt`
   - Check Python path configuration

3. **Desktop shortcut not working**
   - Right-click shortcut → Properties
   - Verify Target path points to correct Python and script location
   - Check Working Directory is set correctly

4. **GUI not starting**
   - Check if tkinter is available: `python -c "import tkinter"`
   - Try command line mode: `python main_orchestrator.py status`

### Diagnostic Commands
```bash
# Check system health
python launch_agent_university.py --diagnostics

# Verify configuration
python main_orchestrator.py status

# Test data source connections
python -c "from scoring_system import DataSourceRegistry; registry = DataSourceRegistry('agent_university.db', 'datasources'); print('Registry loaded successfully')"
```

## Future GUI Enhancements

The current GUI provides essential functionality with plans for advanced features:

### Planned for Next Iteration
- **Data Source Manager**: Visual configuration interface
- **Governance Dashboard**: Interactive compliance monitoring
- **Data Ingestion Wizard**: Step-by-step data import
- **System Monitoring**: Real-time metrics and alerting

### Advanced Features (Future)
- **Visual Data Lineage**: Interactive flow diagrams
- **Analytics Dashboard**: Performance and quality metrics
- **Drag-and-Drop Builder**: Visual connector creation
- **Mobile Interface**: Progressive Web App version

## Security Considerations

### Desktop Integration
- Shortcuts run with user permissions
- No elevated privileges required
- All data stored in user directory

### Data Protection
- PII redaction enabled by default
- Secrets scanning prevents data leakage
- GDPR compliance built-in
- Complete audit trail maintained

## Support and Maintenance

### Regular Tasks
1. **Weekly**: Run governance checks
2. **Monthly**: Review data source priorities
3. **Quarterly**: Update data source configurations
4. **As needed**: Process data subject requests

### Monitoring
- Check desktop shortcut functionality
- Verify system status regularly
- Monitor log files for errors
- Review compliance scores

### Updates
- Update data source YAML configurations
- Refresh system configuration as needed
- Install Python package updates
- Review and update governance policies

## Getting Help

1. Documentation: Check README.md and implementation summary
2. **Logs**: Review `agent_university_launcher.log` for errors
3. **Diagnostics**: Use built-in system diagnostics
4. **Status Check**: Run system status command

The desktop integration provides a seamless, one-click experience for managing the complete Agent University data pipeline while maintaining enterprise-grade security and compliance standards.
