#!/usr/bin/env python3
"""
AML University Training Hospital - Enhanced Desktop Launcher
Complete GUI launcher for Domain Pack teaching system and all services
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import webbrowser
import os
import sys
import time
from pathlib import Path
from datetime import datetime
import json

class AMLUniversityLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎓 AML University Training Hospital Launcher")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f0f0")
        
        # System status tracking
        self.processes = {}
        self.services_status = {}
        
        # Service configurations
        self.services = {
            "Domain Pack Dashboard": {
                "port": 8501,
                "url": "http://localhost:8501",
                "cmd": [sys.executable, "-m", "streamlit", "run", "streamlit_app/domain_pack_dashboard.py", "--server.port", "8501"],
                "category": "Teaching System"
            },
            "Agent Health Dashboard": {
                "port": 8502,
                "url": "http://localhost:8502",
                "cmd": [sys.executable, "-m", "streamlit", "run", "streamlit_dashboard.py", "--server.port", "8502"],
                "category": "Monitoring"
            },
            "Unified Analytics Hub": {
                "port": 8095,
                "url": "http://localhost:8095/healthz",
                "cmd": [sys.executable, "services/unified_analytics_hub.py"],
                "category": "Analytics"
            },
            "Hospital API": {
                "port": 8091,
                "url": "http://localhost:8091/healthz",
                "cmd": [sys.executable, "AgentHospital/start_hospital_api.py"],
                "category": "APIs"
            },
            "University API": {
                "port": 8088,
                "url": "http://localhost:8088/healthz",
                "cmd": [sys.executable, "DataManagement/launch_agent_university.py"],
                "category": "APIs"
            }
        }
        
        self.setup_ui()
        self.start_status_monitoring()
    
    def setup_ui(self):
        """Setup the main UI"""
        # Header
        header_frame = tk.Frame(self.root, bg="#667eea", height=100)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="🎓 AML University Training Hospital",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="#667eea"
        )
        title_label.pack(pady=10)
        
        subtitle_label = tk.Label(
            header_frame,
            text="Domain Pack Teaching System • Agent Health Monitoring",
            font=("Arial", 12),
            fg="white",
            bg="#667eea"
        )
        subtitle_label.pack()
        
        # Main content area with tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Services tab
        services_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(services_frame, text="🚀 Services")
        self.setup_services_tab(services_frame)
        
        # Dashboards tab
        dashboards_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(dashboards_frame, text="📊 Dashboards")
        self.setup_dashboards_tab(dashboards_frame)
        
        # Testing tab
        testing_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(testing_frame, text="🧪 Testing")
        self.setup_testing_tab(testing_frame)
        
        # Status log tab
        log_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(log_frame, text="📝 Logs")
        self.setup_log_tab(log_frame)
        
        # Footer
        footer_frame = tk.Frame(self.root, bg="#667eea", height=50)
        footer_frame.pack(fill="x", padx=0, pady=0)
        footer_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            footer_frame,
            text="Ready • System Status: Initializing...",
            fg="white",
            bg="#667eea",
            font=("Arial", 10)
        )
        self.status_label.pack(side="left", padx=10, pady=15)
        
        time_label = tk.Label(
            footer_frame,
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            fg="white",
            bg="#667eea",
            font=("Arial", 10)
        )
        time_label.pack(side="right", padx=10, pady=15)
        
        # Update time every second
        def update_time():
            time_label.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self.root.after(1000, update_time)
        
        update_time()
    
    def setup_services_tab(self, parent):
        """Setup services management tab"""
        # Group services by category
        categories = {}
        for service_name, config in self.services.items():
            category = config['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(service_name)
        
        # Create frames for each category
        row = 0
        self.service_labels = {}
        self.service_buttons = {}
        
        for category, services in categories.items():
            # Category header
            category_frame = tk.LabelFrame(
                parent,
                text=f"📦 {category}",
                font=("Arial", 12, "bold"),
                bg="#f0f0f0",
                fg="#667eea"
            )
            category_frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
            
            # Service entries
            for idx, service_name in enumerate(services):
                # Service name
                tk.Label(
                    category_frame,
                    text=service_name,
                    bg="#f0f0f0",
                    font=("Arial", 10)
                ).grid(row=idx, column=0, padx=10, pady=5, sticky="w")
                
                # Status label
                status_label = tk.Label(
                    category_frame,
                    text="❓ Unknown",
                    bg="#f0f0f0",
                    fg="#7f8c8d",
                    font=("Arial", 10)
                )
                status_label.grid(row=idx, column=1, padx=10, pady=5, sticky="w")
                self.service_labels[service_name] = status_label
                
                # Action button
                action_button = tk.Button(
                    category_frame,
                    text="▶ Start",
                    command=lambda s=service_name: self.toggle_service(s),
                    bg="#27ae60",
                    fg="white",
                    font=("Arial", 9, "bold"),
                    width=12
                )
                action_button.grid(row=idx, column=2, padx=10, pady=5)
                self.service_buttons[service_name] = action_button
            
            row += 1
        
        # Control buttons
        control_frame = tk.Frame(parent, bg="#f0f0f0")
        control_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        tk.Button(
            control_frame,
            text="🔄 Refresh All",
            command=self.check_all_services,
            bg="#3498db",
            fg="white",
            font=("Arial", 11, "bold"),
            width=15,
            height=2
        ).pack(side="left", padx=5)
        
        tk.Button(
            control_frame,
            text="🚀 Start All",
            command=self.start_all_services,
            bg="#27ae60",
            fg="white",
            font=("Arial", 11, "bold"),
            width=15,
            height=2
        ).pack(side="left", padx=5)
        
        tk.Button(
            control_frame,
            text="🛑 Stop All",
            command=self.stop_all_services,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 11, "bold"),
            width=15,
            height=2
        ).pack(side="left", padx=5)
    
    def setup_dashboards_tab(self, parent):
        """Setup dashboards quick access tab"""
        # Dashboard cards
        dashboards = [
            {
                "name": "🎓 Domain Pack Dashboard",
                "desc": "Teaching system monitoring with routing and telemetry",
                "url": "http://localhost:8501",
                "color": "#667eea"
            },
            {
                "name": "🏥 Agent Health Dashboard",
                "desc": "Real-time agent health and mental health monitoring",
                "url": "http://localhost:8502",
                "color": "#f093fb"
            },
            {
                "name": "📊 Unified Analytics Hub",
                "desc": "Consolidated analytics and metrics across all systems",
                "url": "http://localhost:8095",
                "color": "#4facfe"
            },
            {
                "name": "📈 W&B Dashboard",
                "desc": "Weights & Biases experiment tracking and reports",
                "url": "https://wandb.ai/sissa_ivy-suntari-comics-llc/intro-example",
                "color": "#43e97b"
            }
        ]
        
        for idx, dashboard in enumerate(dashboards):
            row = idx // 2
            col = idx % 2
            
            card = tk.Frame(parent, bg=dashboard['color'], relief="raised", bd=3)
            card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
            
            tk.Label(
                card,
                text=dashboard['name'],
                bg=dashboard['color'],
                fg="white",
                font=("Arial", 14, "bold")
            ).pack(pady=10)
            
            tk.Label(
                card,
                text=dashboard['desc'],
                bg=dashboard['color'],
                fg="white",
                font=("Arial", 10),
                wraplength=300
            ).pack(pady=5, padx=10)
            
            tk.Button(
                card,
                text="🚀 Open Dashboard",
                command=lambda url=dashboard['url']: webbrowser.open(url),
                bg="white",
                fg=dashboard['color'],
                font=("Arial", 11, "bold"),
                width=20,
                height=2
            ).pack(pady=10)
        
        # Configure grid weights
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
    
    def setup_testing_tab(self, parent):
        """Setup testing tools tab"""
        # Test buttons
        tests = [
            {
                "name": "🧪 Run Phase II Hardening Tests",
                "cmd": [sys.executable, "-m", "pytest", "tests/test_phase_ii_hardening.py", "-v"],
                "desc": "Test router, telemetry, and teaching invariants"
            },
            {
                "name": "🎯 Run Domain Pack Tests",
                "cmd": [sys.executable, "-m", "pytest", "tests/test_domain_pack_loader.py", "-v"],
                "desc": "Test domain pack loading and validation"
            },
            {
                "name": "📚 Run Agent Registry Tests",
                "cmd": [sys.executable, "-m", "pytest", "tests/test_agent_registry.py", "-v"],
                "desc": "Test agent registry functionality"
            },
            {
                "name": "🎮 Simulate Teaching Session",
                "cmd": [sys.executable, "examples/phase_iii_demo.py"],
                "desc": "Run a complete teaching session simulation"
            },
            {
                "name": "📝 Generate Test Events",
                "cmd": [sys.executable, "generate_test_events.py"],
                "desc": "Generate test audit events for dashboards"
            }
        ]
        
        for idx, test in enumerate(tests):
            test_frame = tk.Frame(parent, bg="white", relief="raised", bd=2)
            test_frame.pack(fill="x", padx=20, pady=10)
            
            tk.Label(
                test_frame,
                text=test['name'],
                bg="white",
                font=("Arial", 12, "bold")
            ).pack(anchor="w", padx=10, pady=5)
            
            tk.Label(
                test_frame,
                text=test['desc'],
                bg="white",
                fg="#7f8c8d",
                font=("Arial", 10)
            ).pack(anchor="w", padx=10, pady=2)
            
            tk.Button(
                test_frame,
                text="▶ Run Test",
                command=lambda cmd=test['cmd'], name=test['name']: self.run_test(cmd, name),
                bg="#667eea",
                fg="white",
                font=("Arial", 10, "bold"),
                width=15
            ).pack(anchor="e", padx=10, pady=10)
    
    def setup_log_tab(self, parent):
        """Setup logging tab"""
        self.log_text = scrolledtext.ScrolledText(
            parent,
            height=30,
            width=100,
            bg="#2c3e50",
            fg="#ecf0f1",
            font=("Consolas", 10)
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Clear log button
        tk.Button(
            parent,
            text="🗑️ Clear Log",
            command=lambda: self.log_text.delete(1.0, tk.END),
            bg="#e74c3c",
            fg="white",
            font=("Arial", 10, "bold")
        ).pack(pady=5)
    
    def log_message(self, message):
        """Add message to status log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_service_status(self, service_name, status_text, button_text, button_color):
        """Update service status display"""
        self.service_labels[service_name].config(text=status_text)
        self.service_buttons[service_name].config(text=button_text, bg=button_color)
        self.services_status[service_name] = status_text
    
    def check_service_status(self, service_name):
        """Check individual service status"""
        # For services that have been started by us, check if process is alive
        if service_name in self.processes:
            if self.processes[service_name].poll() is None:
                return "🟢 Running"
            else:
                return "🔴 Stopped"
        return "🔴 Stopped"
    
    def check_all_services(self):
        """Check status of all services"""
        self.log_message("Checking all services...")
        
        for service_name in self.services.keys():
            status = self.check_service_status(service_name)
            
            if status == "🟢 Running":
                self.update_service_status(service_name, status, "⏹ Stop", "#e74c3c")
            else:
                self.update_service_status(service_name, status, "▶ Start", "#27ae60")
        
        self.log_message("Service status check completed")
        
        # Update footer
        running = sum(1 for s in self.services_status.values() if "Running" in s)
        total = len(self.services)
        self.status_label.config(text=f"Ready • Services: {running}/{total} Running")
    
    def toggle_service(self, service_name):
        """Start or stop a service"""
        current_status = self.services_status.get(service_name, "🔴 Stopped")
        
        if "Running" in current_status:
            self.stop_service(service_name)
        else:
            self.start_service(service_name)
    
    def start_service(self, service_name):
        """Start a service"""
        config = self.services[service_name]
        
        self.log_message(f"Starting {service_name}...")
        self.update_service_status(service_name, "🟡 Starting", "⏳ Starting...", "#f39c12")
        
        try:
            # Change to the project directory
            project_dir = Path(__file__).parent
            os.chdir(project_dir)
            
            # Start process in background
            process = subprocess.Popen(
                config['cmd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            self.processes[service_name] = process
            
            # Check status after a delay
            self.root.after(3000, lambda: self.check_service_status_delayed(service_name))
            
        except Exception as e:
            self.log_message(f"Failed to start {service_name}: {str(e)}")
            self.update_service_status(service_name, "🔴 Error", "▶ Start", "#27ae60")
    
    def stop_service(self, service_name):
        """Stop a service"""
        self.log_message(f"Stopping {service_name}...")
        
        if service_name in self.processes:
            try:
                self.processes[service_name].terminate()
                del self.processes[service_name]
            except:
                pass
        
        self.update_service_status(service_name, "🔴 Stopped", "▶ Start", "#27ae60")
        self.log_message(f"{service_name} stopped")
        
        self.check_all_services()
    
    def start_all_services(self):
        """Start all services"""
        self.log_message("Starting all services...")
        
        for service_name in self.services.keys():
            if self.check_service_status(service_name) != "🟢 Running":
                self.start_service(service_name)
                time.sleep(1)  # Stagger starts
    
    def stop_all_services(self):
        """Stop all running services"""
        self.log_message("Stopping all services...")
        
        for service_name in list(self.processes.keys()):
            self.stop_service(service_name)
        
        self.log_message("All services stopped")
    
    def check_service_status_delayed(self, service_name):
        """Check service status after startup delay"""
        status = self.check_service_status(service_name)
        
        if status == "🟢 Running":
            self.update_service_status(service_name, status, "⏹ Stop", "#e74c3c")
            self.log_message(f"{service_name} started successfully")
        else:
            self.update_service_status(service_name, status, "▶ Start", "#27ae60")
            self.log_message(f"{service_name} may not have started correctly")
        
        self.check_all_services()
    
    def run_test(self, cmd, test_name):
        """Run a test command"""
        self.log_message(f"Running {test_name}...")
        
        def execute_test():
            try:
                project_dir = Path(__file__).parent
                os.chdir(project_dir)
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    self.log_message(f"✅ {test_name} completed successfully!")
                    if result.stdout:
                        self.log_message(result.stdout[:500])  # First 500 chars
                else:
                    self.log_message(f"❌ {test_name} failed!")
                    if result.stderr:
                        self.log_message(result.stderr[:500])
                
            except Exception as e:
                self.log_message(f"Error running {test_name}: {str(e)}")
        
        threading.Thread(target=execute_test, daemon=True).start()
    
    def start_status_monitoring(self):
        """Start periodic status monitoring"""
        def monitor():
            while True:
                try:
                    self.check_all_services()
                    time.sleep(30)  # Check every 30 seconds
                except:
                    pass
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def run(self):
        """Start the launcher GUI"""
        self.log_message("AML University Training Hospital Launcher started")
        self.check_all_services()
        self.root.mainloop()


def main():
    """Main entry point"""
    launcher = AMLUniversityLauncher()
    launcher.run()


if __name__ == "__main__":
    main()

