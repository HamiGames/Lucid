"""
Example usage of Lucid core widgets.

This script demonstrates how to use the status and progress widgets
in the Lucid application.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime

from .status import (
    StatusGrid, StatusInfo, StatusLevel, ComponentType,
    create_lucid_status_grid
)
from .progress import (
    ProgressManager, ProgressInfo, ProgressType, ProgressStyle, 
    OperationType, create_progress_info
)


class WidgetDemo:
    """Demo application showing widget usage."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Lucid Core Widgets Demo")
        self.root.geometry("800x600")
        
        # Create main notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status widgets tab
        self.status_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.status_frame, text="Status Widgets")
        self._create_status_demo()
        
        # Progress widgets tab
        self.progress_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.progress_frame, text="Progress Widgets")
        self._create_progress_demo()
        
        # Demo controls
        self.control_frame = ttk.Frame(self.root)
        self.control_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(
            self.control_frame,
            text="Start Demo",
            command=self.start_demo
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            self.control_frame,
            text="Stop Demo",
            command=self.stop_demo
        ).pack(side=tk.LEFT)
        
        self.demo_running = False
    
    def _create_status_demo(self):
        """Create status widgets demo."""
        # Create status grid
        self.status_grid = create_lucid_status_grid(self.status_frame)
        self.status_grid.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add some demo components
        self.status_grid.add_component(
            "demo_service", "Demo Service", ComponentType.SERVICE
        )
        self.status_grid.add_component(
            "demo_api", "Demo API", ComponentType.API
        )
    
    def _create_progress_demo(self):
        """Create progress widgets demo."""
        # Create progress manager
        self.progress_manager = ProgressManager(self.progress_frame)
        self.progress_manager.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add some demo operations
        self.demo_operations = []
    
    def start_demo(self):
        """Start the demo simulation."""
        if self.demo_running:
            return
        
        self.demo_running = True
        
        # Start status monitoring thread
        self.status_thread = threading.Thread(target=self._status_demo_loop, daemon=True)
        self.status_thread.start()
        
        # Start progress demo thread
        self.progress_thread = threading.Thread(target=self._progress_demo_loop, daemon=True)
        self.progress_thread.start()
    
    def stop_demo(self):
        """Stop the demo simulation."""
        self.demo_running = False
    
    def _status_demo_loop(self):
        """Status demo simulation loop."""
        import random
        
        while self.demo_running:
            # Update Lucid components with random statuses
            components = [
                ("lucid_api", "API Service"),
                ("lucid_gui", "GUI Interface"),
                ("lucid_database", "MongoDB"),
                ("lucid_blockchain", "Blockchain Node"),
                ("lucid_tor", "Tor Proxy"),
                ("lucid_rdp", "RDP Server"),
                ("lucid_node", "Consensus Node"),
                ("lucid_storage", "Storage Service"),
                ("demo_service", "Demo Service"),
                ("demo_api", "Demo API")
            ]
            
            for component_id, name in components:
                if not self.demo_running:
                    break
                
                # Random status
                status_levels = [
                    StatusLevel.ONLINE,
                    StatusLevel.WARNING,
                    StatusLevel.ERROR,
                    StatusLevel.OFFLINE
                ]
                status = random.choice(status_levels)
                
                # Create status info
                status_info = StatusInfo(
                    component_id=component_id,
                    component_type=ComponentType.SERVICE,
                    name=name,
                    status=status,
                    message=f"{name} is {status.value}",
                    last_updated=datetime.now(),
                    health_score=random.uniform(0.0, 1.0),
                    response_time=random.uniform(10.0, 500.0),
                    uptime=f"{random.randint(1, 24)}h {random.randint(0, 59)}m"
                )
                
                # Update in main thread
                self.root.after(0, lambda info=status_info: 
                    self.status_grid.update_component_status(info.component_id, info))
                
                time.sleep(0.5)
    
    def _progress_demo_loop(self):
        """Progress demo simulation loop."""
        operation_counter = 0
        
        while self.demo_running:
            operation_counter += 1
            
            # Create a new operation
            operation_id = f"demo_op_{operation_counter}"
            operation_types = [
                OperationType.DOWNLOAD,
                OperationType.UPLOAD,
                OperationType.BUILD,
                OperationType.SYNC,
                OperationType.BACKUP
            ]
            
            operation_type = operation_types[operation_counter % len(operation_types)]
            
            # Start operation
            widget = self.progress_manager.start_operation(
                operation_id=operation_id,
                title=f"Demo {operation_type.value.title()}",
                operation_type=operation_type,
                progress_type=ProgressType.DETERMINATE,
                style=ProgressStyle.BAR
            )
            
            # Simulate progress
            for progress in range(0, 101, 5):
                if not self.demo_running:
                    break
                
                progress_info = create_progress_info(
                    operation_id=operation_id,
                    title=f"Demo {operation_type.value.title()}",
                    operation_type=operation_type,
                    current_value=progress,
                    max_value=100.0,
                    status_message=f"Processing {operation_type.value}... {progress}%"
                )
                
                # Update in main thread
                self.root.after(0, lambda info=progress_info: 
                    self.progress_manager.update_operation(info.operation_id, info))
                
                time.sleep(0.2)
            
            # Mark as complete
            if self.demo_running:
                complete_info = create_progress_info(
                    operation_id=operation_id,
                    title=f"Demo {operation_type.value.title()}",
                    operation_type=operation_type,
                    current_value=100.0,
                    max_value=100.0,
                    status_message="Operation completed successfully!"
                )
                
                self.root.after(0, lambda info=complete_info: 
                    self.progress_manager.update_operation(info.operation_id, info))
            
            time.sleep(2)  # Pause between operations
    
    def run(self):
        """Run the demo application."""
        self.root.mainloop()


def main():
    """Main function to run the demo."""
    demo = WidgetDemo()
    demo.run()


if __name__ == "__main__":
    main()
