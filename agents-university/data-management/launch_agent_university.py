"""
Agent University Data Management System - Desktop Launcher
Automated launcher with GUI preparation for future iterations

This script provides:
1. One-click system initialization and operation
2. Automated health checks and status reporting
3. GUI framework preparation for future development
4. Desktop integration with system tray support
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import subprocess
from pathlib import Path
from datetime import datetime
import logging

# Add the DataManagement directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from main_orchestrator import AgentUniversityDataManager
except ImportError:
    # Fallback if imports fail
    AgentUniversityDataManager = None

class AgentUniversityLauncher:
    """Desktop launcher with GUI for Agent University Data Management"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Agent University Data Management System")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Set icon if available
        try:
            self.root.iconbitmap(default="agent_university.ico")
        except:
            pass  # Icon file not found, continue without it
        
        self.manager = None
        self.setup_logging()
        self.create_gui()
        self.auto_initialize()
    
    def setup_logging(self):
        """Setup logging for the GUI application"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('agent_university_launcher.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def create_gui(self):
        """Create the main GUI interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Agent University Data Management System", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="System Status", padding="10")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky=tk.W)
        self.status_label = ttk.Label(status_frame, text="Initializing...", foreground="orange")
        self.status_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Data Sources:").grid(row=1, column=0, sticky=tk.W)
        self.sources_label = ttk.Label(status_frame, text="Loading...")
        self.sources_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Last Check:").grid(row=2, column=0, sticky=tk.W)
        self.last_check_label = ttk.Label(status_frame, text="Never")
        self.last_check_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.init_button = ttk.Button(button_frame, text="Initialize System", 
                                     command=self.initialize_system)
        self.init_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.score_button = ttk.Button(button_frame, text="Score Data Sources", 
                                      command=self.score_sources)
        self.score_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.governance_button = ttk.Button(button_frame, text="Run Governance Checks", 
                                           command=self.run_governance)
        self.governance_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_button = ttk.Button(button_frame, text="Refresh Status", 
                                       command=self.refresh_status)
        self.status_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Log output
        log_frame = ttk.LabelFrame(main_frame, text="System Log", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Menu bar
        self.create_menu()
    
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Config", command=self.open_config)
        file_menu.add_command(label="View Reports", command=self.view_reports)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Data Source Manager", command=self.open_source_manager)
        tools_menu.add_command(label="Governance Dashboard", command=self.open_governance_dashboard)
        tools_menu.add_command(label="System Diagnostics", command=self.run_diagnostics)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.open_documentation)
        help_menu.add_command(label="About", command=self.show_about)
    
    def auto_initialize(self):
        """Automatically initialize the system on startup"""
        self.log("Starting Agent University Data Management System...")
        
        # Run initialization in background thread
        threading.Thread(target=self._auto_init_worker, daemon=True).start()
    
    def _auto_init_worker(self):
        """Background worker for auto-initialization"""
        try:
            # Initialize manager
            config_path = "config.json"
            if not os.path.exists(config_path):
                self.log("Config file not found, using defaults")
            
            if AgentUniversityDataManager:
                self.manager = AgentUniversityDataManager(config_path)
                self.log("Data manager initialized successfully")
                
                # Update status
                self.root.after(0, lambda: self.status_label.config(text="Ready", foreground="green"))
                
                # Get initial status
                self.refresh_status_worker()
            else:
                self.log("Warning: Could not import AgentUniversityDataManager")
                self.root.after(0, lambda: self.status_label.config(text="Import Error", foreground="red"))
                
        except Exception as e:
            self.log(f"Auto-initialization failed: {e}")
            self.root.after(0, lambda: self.status_label.config(text="Error", foreground="red"))
    
    def initialize_system(self):
        """Initialize the complete system"""
        self.log("Initializing system...")
        self.start_progress()
        
        def worker():
            try:
                if not self.manager:
                    if AgentUniversityDataManager:
                        self.manager = AgentUniversityDataManager("config.json")
                    else:
                        raise Exception("AgentUniversityDataManager not available")
                
                results = self.manager.initialize_system()
                
                self.root.after(0, lambda: self.stop_progress())
                
                if results.get('status') == 'success':
                    self.log("✅ System initialization completed successfully")
                    self.log(f"Components initialized: {', '.join(results.get('components_initialized', []))}")
                    if 'data_sources_scored' in results:
                        self.log(f"Data sources scored: {results['data_sources_scored']}")
                    
                    self.root.after(0, lambda: self.status_label.config(text="Initialized", foreground="green"))
                    self.root.after(0, self.refresh_status)
                else:
                    self.log(f"❌ System initialization failed: {results.get('error', 'Unknown error')}")
                    self.root.after(0, lambda: self.status_label.config(text="Init Failed", foreground="red"))
                    
            except Exception as e:
                self.root.after(0, lambda: self.stop_progress())
                self.log(f"❌ Initialization error: {e}")
                self.root.after(0, lambda: self.status_label.config(text="Error", foreground="red"))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def score_sources(self):
        """Score and prioritize data sources"""
        self.log("Scoring data sources...")
        self.start_progress()
        
        def worker():
            try:
                if not self.manager:
                    raise Exception("System not initialized")
                
                results = self.manager.run_data_source_scoring()
                
                self.root.after(0, lambda: self.stop_progress())
                
                if results.get('status') == 'success':
                    self.log("✅ Data source scoring completed")
                    self.log(f"Sources scored: {results.get('sources_scored', 0)}")
                    if results.get('top_priority_source'):
                        self.log(f"Top priority: {results['top_priority_source']} (Score: {results.get('top_priority_score', 0):.2f})")
                    self.log(f"Report saved: {results.get('report_path', 'N/A')}")
                else:
                    self.log(f"❌ Scoring failed: {results.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self.root.after(0, lambda: self.stop_progress())
                self.log(f"❌ Scoring error: {e}")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def run_governance(self):
        """Run governance and compliance checks"""
        self.log("Running governance checks...")
        self.start_progress()
        
        def worker():
            try:
                if not self.manager:
                    raise Exception("System not initialized")
                
                results = self.manager.run_governance_checks()
                
                self.root.after(0, lambda: self.stop_progress())
                
                if results.get('status') == 'completed':
                    self.log("✅ Governance checks completed")
                    self.log(f"Checks performed: {', '.join(results.get('checks_performed', []))}")
                    
                    if 'gdpr_compliance_score' in results:
                        score = results['gdpr_compliance_score']
                        self.log(f"GDPR Compliance Score: {score:.1f}%")
                    
                    if 'quality_compliance_score' in results:
                        score = results['quality_compliance_score']
                        self.log(f"Data Quality Score: {score:.1f}%")
                    
                    issues = results.get('issues_found', 0)
                    if issues > 0:
                        self.log(f"⚠️ Issues found: {issues}")
                        actions = results.get('actions_required', [])
                        for action in actions[:3]:  # Show first 3 actions
                            self.log(f"  • {action}")
                    else:
                        self.log("✅ No compliance issues found")
                        
                    if 'dashboard_path' in results:
                        self.log(f"Dashboard saved: {results['dashboard_path']}")
                else:
                    self.log(f"❌ Governance checks failed: {results.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self.root.after(0, lambda: self.stop_progress())
                self.log(f"❌ Governance error: {e}")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def refresh_status(self):
        """Refresh system status"""
        self.log("Refreshing system status...")
        
        def worker():
            self.refresh_status_worker()
        
        threading.Thread(target=worker, daemon=True).start()
    
    def refresh_status_worker(self):
        """Worker function for status refresh"""
        try:
            if not self.manager:
                return
            
            status = self.manager.get_system_status()
            
            # Update UI on main thread
            def update_ui():
                if status.get('system_health') == 'healthy':
                    self.status_label.config(text="Healthy", foreground="green")
                else:
                    self.status_label.config(text="Issues Detected", foreground="orange")
                
                stats = status.get('statistics', {})
                active_sources = stats.get('active_data_sources', 0)
                total_datasets = stats.get('total_datasets', 0)
                self.sources_label.config(text=f"{active_sources} active, {total_datasets} datasets")
                
                self.last_check_label.config(text=datetime.now().strftime("%H:%M:%S"))
            
            self.root.after(0, update_ui)
            
            # Log key statistics
            stats = status.get('statistics', {})
            self.log(f"Status: {status.get('system_health', 'unknown').title()}")
            self.log(f"Active sources: {stats.get('active_data_sources', 0)}")
            self.log(f"Total datasets: {stats.get('total_datasets', 0)}")
            self.log(f"Ingestions (24h): {stats.get('ingestions_last_24h', 0)}")
            
        except Exception as e:
            self.log(f"Status refresh error: {e}")
    
    def start_progress(self):
        """Start progress bar animation"""
        self.progress.start(10)
    
    def stop_progress(self):
        """Stop progress bar animation"""
        self.progress.stop()
    
    def log(self, message):
        """Add message to log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        def update_log():
            self.log_text.insert(tk.END, log_message)
            self.log_text.see(tk.END)
        
        if threading.current_thread() == threading.main_thread():
            update_log()
        else:
            self.root.after(0, update_log)
        
        # Also log to file
        self.logger.info(message)
    
    # Menu command implementations
    def open_config(self):
        """Open configuration file"""
        config_path = "config.json"
        if os.path.exists(config_path):
            if sys.platform.startswith('win'):
                os.startfile(config_path)
            else:
                subprocess.call(['open', config_path])
        else:
            messagebox.showwarning("File Not Found", f"Configuration file not found: {config_path}")
    
    def view_reports(self):
        """Open reports directory"""
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
        
        if sys.platform.startswith('win'):
            os.startfile(reports_dir)
        else:
            subprocess.call(['open', reports_dir])
    
    def open_source_manager(self):
        """Open data source manager (placeholder for future GUI)"""
        messagebox.showinfo("Coming Soon", 
                           "Data Source Manager GUI will be available in future iterations.\n\n"
                           "For now, you can:\n"
                           "• Edit YAML files in the datasources/ directory\n"
                           "• Use the 'Score Data Sources' button to refresh priorities")
    
    def open_governance_dashboard(self):
        """Open governance dashboard (placeholder for future GUI)"""
        messagebox.showinfo("Coming Soon", 
                           "Governance Dashboard GUI will be available in future iterations.\n\n"
                           "For now, you can:\n"
                           "• Use the 'Run Governance Checks' button\n"
                           "• Check the generated JSON dashboard files")
    
    def run_diagnostics(self):
        """Run system diagnostics"""
        self.log("Running system diagnostics...")
        
        diagnostics = []
        
        # Check file system
        required_files = ["config.json", "main_orchestrator.py", "datasources/"]
        for file_path in required_files:
            if os.path.exists(file_path):
                diagnostics.append(f"✅ {file_path} - Found")
            else:
                diagnostics.append(f"❌ {file_path} - Missing")
        
        # Check Python modules
        modules = ["sqlite3", "pandas", "yaml", "pathlib"]
        for module in modules:
            try:
                __import__(module)
                diagnostics.append(f"✅ {module} - Available")
            except ImportError:
                diagnostics.append(f"❌ {module} - Missing")
        
        # Display results
        result = "\n".join(diagnostics)
        messagebox.showinfo("System Diagnostics", result)
        
        for diag in diagnostics:
            self.log(diag)
    
    def open_documentation(self):
        """Open documentation"""
        readme_path = "README.md"
        if os.path.exists(readme_path):
            if sys.platform.startswith('win'):
                os.startfile(readme_path)
            else:
                subprocess.call(['open', readme_path])
        else:
            messagebox.showwarning("File Not Found", "README.md not found")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Agent University Data Management System
Version 1.0

A comprehensive data management system for Agent University / ClosedLoopSecuritySystem.

Features:
• 4-axis data source scoring and prioritization
• Bronze/Silver/Gold data lake architecture  
• PII redaction and security scanning
• Double Helix tagging integration
• GDPR compliance and governance framework
• Automated data ingestion pipelines

Built for enterprise-grade AI/ML operations with complete audit trails and compliance controls."""
        
        messagebox.showinfo("About", about_text)
    
    def run(self):
        """Start the GUI application"""
        self.log("Agent University Data Management System started")
        self.root.mainloop()

def create_desktop_shortcut():
    """Create desktop shortcut for the launcher"""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        shortcut_path = os.path.join(desktop, "Agent University Data Management.lnk")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = f'"{os.path.abspath(__file__)}"'
        shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(__file__))
        shortcut.IconLocation = sys.executable
        shortcut.Description = "Agent University Data Management System"
        shortcut.save()
        
        print(f"Desktop shortcut created: {shortcut_path}")
        return True
        
    except ImportError:
        print("Windows shell extensions not available. Manual shortcut creation required.")
        return False
    except Exception as e:
        print(f"Failed to create desktop shortcut: {e}")
        return False

def main():
    """Main entry point"""
    # Check if running with GUI flag
    if len(sys.argv) > 1 and sys.argv[1] == "--create-shortcut":
        create_desktop_shortcut()
        return
    
    # Check if running in command line mode
    if len(sys.argv) > 1 and sys.argv[1] in ["init", "score", "governance", "status"]:
        # Run in command line mode
        try:
            from main_orchestrator import main as cli_main
            cli_main()
        except ImportError:
            print("Command line interface not available. Starting GUI...")
            app = AgentUniversityLauncher()
            app.run()
    else:
        # Run GUI
        app = AgentUniversityLauncher()
        app.run()

if __name__ == "__main__":
    main()
