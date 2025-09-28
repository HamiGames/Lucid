# Path: gui/node_gui.py

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import asyncio
import threading
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
import requests
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NodeGUI:
    """
    Lucid RDP Node Management GUI.
    Provides interface for monitoring node status, peer connections, and work credits.
    """
    
    def __init__(self, root: tk.Tk, node_api_url: str = "http://localhost:8080"):
        self.root = root
        self.node_api_url = node_api_url.rstrip('/')
        self.update_interval = 5000  # 5 seconds
        
        # Data storage
        self.node_status: Dict[str, Any] = {}
        self.peer_data: Dict[str, Any] = {}
        self.work_credits_data: Dict[str, Any] = {}
        
        # Setup GUI
        self.setup_gui()
        self.setup_menu()
        
        # Start periodic updates
        self.start_updates()
        
    def setup_gui(self) -> None:
        """Setup the main GUI interface."""
        self.root.title("Lucid RDP - Node Management")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_status_tab()
        self.create_peers_tab()
        self.create_work_credits_tab()
        self.create_sessions_tab()
        self.create_logs_tab()
        
        # Status bar
        self.status_bar = tk.Label(
            self.root,
            text="Disconnected",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg='#e0e0e0'
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_menu(self) -> None:
        """Setup menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Connect...", command=self.connect_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Node menu
        node_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Node", menu=node_menu)
        node_menu.add_command(label="Start Node", command=self.start_node)
        node_menu.add_command(label="Stop Node", command=self.stop_node)
        node_menu.add_command(label="Restart Node", command=self.restart_node)
        node_menu.add_separator()
        node_menu.add_command(label="Join Pool...", command=self.join_pool_dialog)
        node_menu.add_command(label="Leave Pool", command=self.leave_pool)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
    def create_status_tab(self) -> None:
        """Create node status tab."""
        self.status_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.status_frame, text="Node Status")
        
        # Node information section
        info_frame = ttk.LabelFrame(self.status_frame, text="Node Information")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create labels for node info
        self.node_id_label = tk.Label(info_frame, text="Node ID: N/A", anchor='w')
        self.node_id_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.role_label = tk.Label(info_frame, text="Role: N/A", anchor='w')
        self.role_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.pool_label = tk.Label(info_frame, text="Pool: None", anchor='w')
        self.pool_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.uptime_label = tk.Label(info_frame, text="Uptime: N/A", anchor='w')
        self.uptime_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Metrics section
        metrics_frame = ttk.LabelFrame(self.status_frame, text="Performance Metrics")
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview for metrics
        self.metrics_tree = ttk.Treeview(metrics_frame, columns=('value',), show='tree headings')
        self.metrics_tree.heading('#0', text='Metric')
        self.metrics_tree.heading('value', text='Value')
        self.metrics_tree.column('#0', width=200)
        self.metrics_tree.column('value', width=150)
        
        metrics_scroll = ttk.Scrollbar(metrics_frame, orient=tk.VERTICAL, command=self.metrics_tree.yview)
        self.metrics_tree.configure(yscrollcommand=metrics_scroll.set)
        
        self.metrics_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        metrics_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_peers_tab(self) -> None:
        """Create peers tab."""
        self.peers_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.peers_frame, text="Network Peers")
        
        # Toolbar
        toolbar = ttk.Frame(self.peers_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Refresh", command=self.refresh_peers).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Add Peer", command=self.add_peer_dialog).pack(side=tk.LEFT, padx=5)
        
        # Peers treeview
        self.peers_tree = ttk.Treeview(
            self.peers_frame,
            columns=('role', 'address', 'status', 'work_credits', 'uptime'),
            show='headings'
        )
        
        # Configure columns
        self.peers_tree.heading('role', text='Role')
        self.peers_tree.heading('address', text='Address')
        self.peers_tree.heading('status', text='Status')
        self.peers_tree.heading('work_credits', text='Work Credits')
        self.peers_tree.heading('uptime', text='Uptime %')
        
        self.peers_tree.column('role', width=80)
        self.peers_tree.column('address', width=300)
        self.peers_tree.column('status', width=80)
        self.peers_tree.column('work_credits', width=100)
        self.peers_tree.column('uptime', width=80)
        
        # Scrollbar for peers
        peers_scroll = ttk.Scrollbar(self.peers_frame, orient=tk.VERTICAL, command=self.peers_tree.yview)
        self.peers_tree.configure(yscrollcommand=peers_scroll.set)
        
        self.peers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        peers_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
    def create_work_credits_tab(self) -> None:
        """Create work credits tab."""
        self.credits_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.credits_frame, text="Work Credits")
        
        # Current rank section
        rank_frame = ttk.LabelFrame(self.credits_frame, text="Current Ranking")
        rank_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.rank_label = tk.Label(rank_frame, text="Rank: N/A", font=('Arial', 12, 'bold'))
        self.rank_label.pack(pady=5)
        
        self.credits_label = tk.Label(rank_frame, text="Credits: 0.0", font=('Arial', 10))
        self.credits_label.pack(pady=2)
        
        # Top performers section
        top_frame = ttk.LabelFrame(self.credits_frame, text="Top Performers")
        top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.top_tree = ttk.Treeview(
            top_frame,
            columns=('rank', 'credits', 'live_score'),
            show='tree headings'
        )
        
        self.top_tree.heading('#0', text='Entity ID')
        self.top_tree.heading('rank', text='Rank')
        self.top_tree.heading('credits', text='Credits')
        self.top_tree.heading('live_score', text='Live Score')
        
        self.top_tree.column('#0', width=200)
        self.top_tree.column('rank', width=60)
        self.top_tree.column('credits', width=100)
        self.top_tree.column('live_score', width=100)
        
        top_scroll = ttk.Scrollbar(top_frame, orient=tk.VERTICAL, command=self.top_tree.yview)
        self.top_tree.configure(yscrollcommand=top_scroll.set)
        
        self.top_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        top_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_sessions_tab(self) -> None:
        """Create sessions tab."""
        self.sessions_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sessions_frame, text="Active Sessions")
        
        # Sessions treeview
        self.sessions_tree = ttk.Treeview(
            self.sessions_frame,
            columns=('started', 'participants', 'size', 'status'),
            show='tree headings'
        )
        
        self.sessions_tree.heading('#0', text='Session ID')
        self.sessions_tree.heading('started', text='Started')
        self.sessions_tree.heading('participants', text='Participants')
        self.sessions_tree.heading('size', text='Size')
        self.sessions_tree.heading('status', text='Status')
        
        self.sessions_tree.column('#0', width=200)
        self.sessions_tree.column('started', width=150)
        self.sessions_tree.column('participants', width=100)
        self.sessions_tree.column('size', width=100)
        self.sessions_tree.column('status', width=80)
        
        sessions_scroll = ttk.Scrollbar(self.sessions_frame, orient=tk.VERTICAL, command=self.sessions_tree.yview)
        self.sessions_tree.configure(yscrollcommand=sessions_scroll.set)
        
        self.sessions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        sessions_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
    def create_logs_tab(self) -> None:
        """Create logs tab."""
        self.logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_frame, text="Logs")
        
        # Toolbar
        log_toolbar = ttk.Frame(self.logs_frame)
        log_toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(log_toolbar, text="Clear", command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_toolbar, text="Save", command=self.save_logs).pack(side=tk.LEFT, padx=5)
        
        # Log level filter
        ttk.Label(log_toolbar, text="Level:").pack(side=tk.LEFT, padx=(20, 5))
        self.log_level_var = tk.StringVar(value="INFO")
        log_level_combo = ttk.Combobox(
            log_toolbar,
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARN", "ERROR"],
            width=10
        )
        log_level_combo.pack(side=tk.LEFT, padx=5)
        
        # Logs text area
        self.logs_text = scrolledtext.ScrolledText(
            self.logs_frame,
            wrap=tk.WORD,
            width=80,
            height=20,
            font=('Consolas', 9)
        )
        self.logs_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def start_updates(self) -> None:
        """Start periodic updates."""
        self.update_data()
        self.root.after(self.update_interval, self.start_updates)
        
    def update_data(self) -> None:
        """Update all data from API."""
        try:
            # Update node status
            response = requests.get(f"{self.node_api_url}/api/node/status", timeout=5)
            if response.status_code == 200:
                self.node_status = response.json()
                self.update_status_display()
                self.status_bar.config(text=f"Connected - Last update: {datetime.now().strftime('%H:%M:%S')}")
            else:
                self.status_bar.config(text=f"API Error: {response.status_code}")
                
        except Exception as e:
            self.status_bar.config(text=f"Connection Error: {str(e)}")
            self.log_message(f"ERROR: Failed to update data: {e}")
            
    def update_status_display(self) -> None:
        """Update status tab display."""
        if not self.node_status:
            return
            
        # Update node information
        self.node_id_label.config(text=f"Node ID: {self.node_status.get('node_id', 'N/A')}")
        self.role_label.config(text=f"Role: {self.node_status.get('role', 'N/A')}")
        self.pool_label.config(text=f"Pool: {self.node_status.get('pool_id', 'None')}")
        
        # Format uptime
        uptime_seconds = self.node_status.get('uptime_seconds', 0)
        uptime_str = self.format_uptime(uptime_seconds)
        self.uptime_label.config(text=f"Uptime: {uptime_str}")
        
        # Update metrics tree
        self.metrics_tree.delete(*self.metrics_tree.get_children())
        
        metrics = self.node_status.get('metrics', {})
        for key, value in metrics.items():
            if key == 'uptime_start':
                continue  # Skip raw timestamp
            display_value = self.format_metric_value(key, value)
            self.metrics_tree.insert('', 'end', text=key.replace('_', ' ').title(), values=(display_value,))
            
        # Update work credits
        rank = self.node_status.get('work_credits_rank')
        if rank:
            self.rank_label.config(text=f"Rank: #{rank}")
            
    def format_uptime(self, seconds: float) -> str:
        """Format uptime seconds to readable string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}d {hours}h"
            
    def format_metric_value(self, key: str, value: Any) -> str:
        """Format metric values for display."""
        if key in ['bytes_relayed', 'total_size_bytes']:
            return self.format_bytes(value)
        elif isinstance(value, float):
            return f"{value:.2f}"
        elif isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return str(value)
            
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes to readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.1f} PB"
        
    def refresh_peers(self) -> None:
        """Refresh peers data."""
        try:
            response = requests.get(f"{self.node_api_url}/api/peers", timeout=5)
            if response.status_code == 200:
                self.peer_data = response.json()
                self.update_peers_display()
        except Exception as e:
            self.log_message(f"ERROR: Failed to refresh peers: {e}")
            
    def update_peers_display(self) -> None:
        """Update peers display."""
        self.peers_tree.delete(*self.peers_tree.get_children())
        
        peers = self.peer_data.get('peers', [])
        for peer in peers:
            self.peers_tree.insert('', 'end', values=(
                peer.get('role', 'N/A'),
                f"{peer.get('onion_address', 'N/A')}:{peer.get('port', 'N/A')}",
                'Active' if peer.get('node_id') in peer.get('active_connections', set()) else 'Inactive',
                f"{peer.get('work_credits', 0):.2f}",
                f"{peer.get('uptime_percentage', 0):.1f}%"
            ))
            
    def log_message(self, message: str) -> None:
        """Add message to logs."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_line = f"[{timestamp}] {message}\\n"
        self.logs_text.insert(tk.END, log_line)
        self.logs_text.see(tk.END)
        
    # Dialog methods
    def connect_dialog(self) -> None:
        """Show connection dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Connect to Node")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        
        tk.Label(dialog, text="Node API URL:").pack(pady=5)
        url_entry = tk.Entry(dialog, width=40)
        url_entry.insert(0, self.node_api_url)
        url_entry.pack(pady=5)
        
        def connect():
            self.node_api_url = url_entry.get().rstrip('/')
            dialog.destroy()
            self.update_data()
            
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Connect", command=connect).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
    def join_pool_dialog(self) -> None:
        """Show join pool dialog."""
        pool_id = tk.simpledialog.askstring("Join Pool", "Enter Pool ID:")
        if pool_id:
            try:
                response = requests.post(f"{self.node_api_url}/api/node/join_pool", 
                                       json={"pool_id": pool_id}, timeout=5)
                if response.status_code == 200:
                    messagebox.showinfo("Success", f"Joined pool: {pool_id}")
                else:
                    messagebox.showerror("Error", f"Failed to join pool: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to join pool: {e}")
                
    # Menu action methods
    def start_node(self) -> None:
        """Start node."""
        try:
            response = requests.post(f"{self.node_api_url}/api/node/start", timeout=10)
            if response.status_code == 200:
                messagebox.showinfo("Success", "Node started successfully")
            else:
                messagebox.showerror("Error", f"Failed to start node: {response.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start node: {e}")
            
    def stop_node(self) -> None:
        """Stop node."""
        if messagebox.askyesno("Confirm", "Are you sure you want to stop the node?"):
            try:
                response = requests.post(f"{self.node_api_url}/api/node/stop", timeout=10)
                if response.status_code == 200:
                    messagebox.showinfo("Success", "Node stopped successfully")
                else:
                    messagebox.showerror("Error", f"Failed to stop node: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop node: {e}")
                
    def restart_node(self) -> None:
        """Restart node."""
        if messagebox.askyesno("Confirm", "Are you sure you want to restart the node?"):
            try:
                response = requests.post(f"{self.node_api_url}/api/node/restart", timeout=15)
                if response.status_code == 200:
                    messagebox.showinfo("Success", "Node restarted successfully")
                else:
                    messagebox.showerror("Error", f"Failed to restart node: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restart node: {e}")
                
    def leave_pool(self) -> None:
        """Leave current pool."""
        if messagebox.askyesno("Confirm", "Leave current pool?"):
            try:
                response = requests.post(f"{self.node_api_url}/api/node/leave_pool", timeout=5)
                if response.status_code == 200:
                    messagebox.showinfo("Success", "Left pool successfully")
                else:
                    messagebox.showerror("Error", f"Failed to leave pool: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to leave pool: {e}")
                
    def add_peer_dialog(self) -> None:
        """Show add peer dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Peer")
        dialog.geometry("400x200")
        
        tk.Label(dialog, text="Peer Address (node_id@onion_address:port):").pack(pady=5)
        addr_entry = tk.Entry(dialog, width=50)
        addr_entry.pack(pady=5)
        
        def add_peer():
            peer_addr = addr_entry.get()
            if peer_addr:
                try:
                    response = requests.post(f"{self.node_api_url}/api/peers/add",
                                           json={"peer_address": peer_addr}, timeout=5)
                    if response.status_code == 200:
                        messagebox.showinfo("Success", "Peer added successfully")
                        dialog.destroy()
                        self.refresh_peers()
                    else:
                        messagebox.showerror("Error", f"Failed to add peer: {response.text}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add peer: {e}")
                    
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Add", command=add_peer).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
    def clear_logs(self) -> None:
        """Clear logs display."""
        self.logs_text.delete(1.0, tk.END)
        
    def save_logs(self) -> None:
        """Save logs to file."""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.logs_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Logs saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs: {e}")
                
    def show_about(self) -> None:
        """Show about dialog."""
        messagebox.showinfo(
            "About Lucid RDP",
            "Lucid RDP Node Management GUI\\n\\n"
            "Version: 1.0.0\\n"
            "A decentralized remote desktop platform\\n"
            "with blockchain integration and privacy focus.\\n\\n"
            "© 2025 Lucid RDP Project"
        )


def main():
    """Main entry point."""
    import sys
    import tkinter.simpledialog
    
    # Create root window
    root = tk.Tk()
    root.withdraw()  # Hide while setting up
    
    # Get node API URL
    api_url = "http://localhost:8080"
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    else:
        # Ask user for API URL
        api_url = tkinter.simpledialog.askstring(
            "Node Connection",
            "Enter Node API URL:",
            initialvalue="http://localhost:8080"
        )
        if not api_url:
            return
    
    # Show root window and start GUI
    root.deiconify()
    app = NodeGUI(root, api_url)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("GUI shutting down...")


if __name__ == "__main__":
    main()