"""
Lucid GUI Main Launcher
Platform-aware GUI launcher with automatic interface detection and service routing.
Supports multiple GUI modes: User, Admin, and Node interfaces.
"""

import sys
import os
import platform
import logging
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from typing import Optional, Dict, Any
import subprocess
import threading
import time
import json
import requests
from dataclasses import dataclass
from enum import Enum


def safe_int_env(key: str, default: int) -> int:
    """Safely convert environment variable to int."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        logging.warning(f"Invalid {key}, using default: {default}")
        return default


def safe_float_env(key: str, default: float) -> float:
    """Safely convert environment variable to float."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        logging.warning(f"Invalid {key}, using default: {default}")
        return default

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.config.manager import get_config_manager, get_settings, is_production, is_development
except ImportError:
    # Fallback for development
    def get_settings():
        class MockSettings:
            environment = "development"
            debug = True
            gui_port = 8083
        return MockSettings()
    
    def is_production():
        return False
    
    def is_development():
        return True


class GuiMode(str, Enum):
    """GUI mode enumeration."""
    USER = "user"
    ADMIN = "admin"
    NODE = "node"
    AUTO = "auto"


@dataclass
class ServiceStatus:
    """Service status information."""
    name: str
    running: bool = False
    port: int = 0
    pid: Optional[int] = None
    last_check: float = 0.0
    error: Optional[str] = None


class PlatformDetector:
    """Platform detection and compatibility utilities."""
    
    @staticmethod
    def get_platform_info() -> Dict[str, Any]:
        """Get comprehensive platform information."""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'architecture': platform.architecture(),
            'python_version': platform.python_version(),
            'is_windows': platform.system() == 'Windows',
            'is_linux': platform.system() == 'Linux',
            'is_macos': platform.system() == 'Darwin',
            'is_arm': platform.machine().lower() in ['arm', 'aarch64', 'arm64'],
            'is_x86': platform.machine().lower() in ['x86', 'x86_64', 'amd64']
        }
    
    @staticmethod
    def is_raspberry_pi() -> bool:
        """Detect if running on Raspberry Pi."""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'BCM' in cpuinfo or 'Raspberry Pi' in cpuinfo
        except (FileNotFoundError, PermissionError):
            return False
    
    @staticmethod
    def get_display_info() -> Dict[str, Any]:
        """Get display information."""
        info = {
            'has_display': True,
            'display_type': 'unknown',
            'resolution': None,
            'color_depth': None
        }
        
        try:
            # Check for display environment variables (distroless-safe)
            if os.getenv('DISPLAY'):
                info['display_type'] = 'X11'
            elif os.getenv('WAYLAND_DISPLAY'):
                info['display_type'] = 'Wayland'
            
            # Get resolution from environment variables (distroless-safe)
            resolution = os.getenv('LUCID_DISPLAY_RESOLUTION')
            if resolution:
                info['resolution'] = resolution
            else:
                # Fallback to default resolution for distroless environments
                info['resolution'] = os.getenv('DISPLAY_RESOLUTION', '1920x1080')
            
            # Check if running in distroless container
            if os.getenv('DISTROLESS_CONTAINER'):
                info['display_type'] = 'distroless'
                info['has_display'] = False  # No display in distroless
            
        except Exception as e:
            logging.warning(f"Could not detect display info: {e}")
        
        return info
    
    @staticmethod
    def get_system_resources() -> Dict[str, Any]:
        """Get system resource information."""
        # Default values for distroless environments
        default_resources = {
            'cpu_count': safe_int_env('LUCID_CPU_COUNT', 1),
            'cpu_percent': safe_float_env('LUCID_CPU_PERCENT', 0.0),
            'memory_total': safe_int_env('LUCID_MEMORY_TOTAL', 0),
            'memory_available': safe_int_env('LUCID_MEMORY_AVAILABLE', 0),
            'memory_percent': safe_float_env('LUCID_MEMORY_PERCENT', 0.0),
            'disk_total': safe_int_env('LUCID_DISK_TOTAL', 0),
            'disk_free': safe_int_env('LUCID_DISK_FREE', 0),
            'disk_percent': safe_float_env('LUCID_DISK_PERCENT', 0.0)
        }
        
        # Check if running in distroless container
        if os.getenv('DISTROLESS_CONTAINER'):
            return default_resources
        
        try:
            import psutil
            
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available,
                'memory_percent': psutil.virtual_memory().percent,
                'disk_total': psutil.disk_usage('/').total,
                'disk_free': psutil.disk_usage('/').free,
                'disk_percent': psutil.disk_usage('/').percent
            }
        except ImportError:
            return default_resources


class ServiceMonitor:
    """Service monitoring and management."""
    
    def __init__(self):
        self.services: Dict[str, ServiceStatus] = {}
        self.check_interval = 5.0  # seconds
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
    
    def add_service(self, name: str, port: int) -> None:
        """Add a service to monitor."""
        self.services[name] = ServiceStatus(name=name, port=port)
    
    def check_service(self, name: str) -> bool:
        """Check if a service is running."""
        if name not in self.services:
            return False
        
        service = self.services[name]
        current_time = time.time()
        
        # Don't check too frequently
        if current_time - service.last_check < self.check_interval:
            return service.running
        
        try:
            # Try to connect to the service
            response = requests.get(f"http://localhost:{service.port}/health", timeout=2)
            service.running = response.status_code == 200
            service.error = None
        except requests.exceptions.RequestException as e:
            service.running = False
            service.error = str(e)
        
        service.last_check = current_time
        return service.running
    
    def start_monitoring(self) -> None:
        """Start service monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop service monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
    
    def _monitor_loop(self) -> None:
        """Service monitoring loop."""
        while self._monitoring:
            for service_name in self.services:
                self.check_service(service_name)
            time.sleep(self.check_interval)
    
    def get_service_status(self, name: str) -> Optional[ServiceStatus]:
        """Get service status."""
        return self.services.get(name)
    
    def get_all_status(self) -> Dict[str, ServiceStatus]:
        """Get all service statuses."""
        return self.services.copy()


class GuiLauncher:
    """Main GUI launcher with platform detection and service routing."""
    
    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.config = get_settings()
        self.platform_info = PlatformDetector.get_platform_info()
        self.display_info = PlatformDetector.get_display_info()
        self.system_resources = PlatformDetector.get_system_resources()
        self.service_monitor = ServiceMonitor()
        self.selected_mode: Optional[GuiMode] = None
        
        # Setup logging
        self._setup_logging()
        
        # Add services to monitor
        self.service_monitor.add_service('api', 8000)
        self.service_monitor.add_service('blockchain', 8080)
        self.service_monitor.add_service('node', 8084)
        self.service_monitor.add_service('gui', 8083)
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_level = logging.DEBUG if is_development() else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('lucid_gui.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def run(self, mode: GuiMode = GuiMode.AUTO) -> None:
        """Run the GUI launcher."""
        try:
            self.logger.info(f"Starting Lucid GUI Launcher in {mode} mode")
            self.logger.info(f"Platform: {self.platform_info['system']} {self.platform_info['release']}")
            self.logger.info(f"Architecture: {self.platform_info['machine']}")
            self.logger.info(f"Environment: {self.config.environment}")
            
            # Start service monitoring
            self.service_monitor.start_monitoring()
            
            # Auto-detect mode if needed
            if mode == GuiMode.AUTO:
                mode = self._detect_gui_mode()
            
            self.selected_mode = mode
            
            # Launch appropriate GUI
            if mode == GuiMode.USER:
                self._launch_user_gui()
            elif mode == GuiMode.ADMIN:
                self._launch_admin_gui()
            elif mode == GuiMode.NODE:
                self._launch_node_gui()
            else:
                self._launch_mode_selector()
                
        except Exception as e:
            self.logger.error(f"Failed to start GUI launcher: {e}")
            messagebox.showerror("Error", f"Failed to start GUI: {e}")
        finally:
            self.service_monitor.stop_monitoring()
    
    def _detect_gui_mode(self) -> GuiMode:
        """Auto-detect appropriate GUI mode."""
        # Check for command line arguments
        if len(sys.argv) > 1:
            arg_mode = sys.argv[1].lower()
            if arg_mode in ['user', 'admin', 'node']:
                return GuiMode(arg_mode)
        
        # Check environment variables
        env_mode = os.getenv('LUCID_GUI_MODE', '').lower()
        if env_mode in ['user', 'admin', 'node']:
            return GuiMode(env_mode)
        
        # Check if running on Raspberry Pi
        if PlatformDetector.is_raspberry_pi():
            return GuiMode.NODE
        
        # Check system resources
        if self.system_resources['cpu_count'] < 2 or self.system_resources['memory_total'] < 2 * 1024**3:
            return GuiMode.USER
        
        # Default to mode selector
        return GuiMode.AUTO
    
    def _launch_mode_selector(self) -> None:
        """Launch GUI mode selector."""
        self.root = tk.Tk()
        self.root.title("Lucid - Select Interface Mode")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Center window
        self._center_window()
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Lucid Interface Selector", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Platform info
        info_frame = ttk.LabelFrame(main_frame, text="System Information", padding="10")
        info_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        platform_text = f"Platform: {self.platform_info['system']} {self.platform_info['release']}\n"
        platform_text += f"Architecture: {self.platform_info['machine']}\n"
        platform_text += f"Environment: {self.config.environment}\n"
        platform_text += f"Display: {self.display_info['display_type']}"
        
        if self.display_info['resolution']:
            platform_text += f" ({self.display_info['resolution']})"
        
        ttk.Label(info_frame, text=platform_text, justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)
        
        # Service status
        status_frame = ttk.LabelFrame(main_frame, text="Service Status", padding="10")
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self._create_service_status_display(status_frame)
        
        # Mode selection
        mode_frame = ttk.LabelFrame(main_frame, text="Select Interface Mode", padding="10")
        mode_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # User mode button
        user_btn = ttk.Button(mode_frame, text="User Interface", 
                             command=lambda: self._select_mode(GuiMode.USER),
                             width=20)
        user_btn.grid(row=0, column=0, padx=5, pady=5)
        
        # Admin mode button
        admin_btn = ttk.Button(mode_frame, text="Admin Interface", 
                              command=lambda: self._select_mode(GuiMode.ADMIN),
                              width=20)
        admin_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # Node mode button
        node_btn = ttk.Button(mode_frame, text="Node Interface", 
                             command=lambda: self._select_mode(GuiMode.NODE),
                             width=20)
        node_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Mode descriptions
        desc_frame = ttk.Frame(mode_frame)
        desc_frame.grid(row=1, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Label(desc_frame, text="User: Session management and remote desktop access", 
                 font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(desc_frame, text="Admin: System administration and configuration", 
                 font=("Arial", 9)).grid(row=1, column=0, sticky=tk.W)
        ttk.Label(desc_frame, text="Node: Distributed node operations and monitoring", 
                 font=("Arial", 9)).grid(row=2, column=0, sticky=tk.W)
        
        # Auto-detect button
        auto_btn = ttk.Button(main_frame, text="Auto-detect Mode", 
                             command=lambda: self._select_mode(self._detect_gui_mode()),
                             width=20)
        auto_btn.grid(row=4, column=1, pady=10)
        
        # Exit button
        exit_btn = ttk.Button(main_frame, text="Exit", 
                             command=self.root.quit,
                             width=20)
        exit_btn.grid(row=4, column=2, pady=10)
        
        # Start refresh timer
        self._schedule_status_refresh()
        
        # Start main loop
        self.root.mainloop()
    
    def _create_service_status_display(self, parent: ttk.Widget) -> None:
        """Create service status display."""
        self.status_labels = {}
        
        for i, (name, service) in enumerate(self.service_monitor.services.items()):
            ttk.Label(parent, text=f"{name.title()}:").grid(row=i, column=0, sticky=tk.W, padx=(0, 10))
            
            status_label = ttk.Label(parent, text="Checking...", foreground="orange")
            status_label.grid(row=i, column=1, sticky=tk.W)
            
            self.status_labels[name] = status_label
    
    def _schedule_status_refresh(self) -> None:
        """Schedule service status refresh."""
        if self.root and self.root.winfo_exists():
            self._refresh_service_status()
            self.root.after(5000, self._schedule_status_refresh)
    
    def _refresh_service_status(self) -> None:
        """Refresh service status display."""
        for name, label in self.status_labels.items():
            service = self.service_monitor.get_service_status(name)
            if service:
                if service.running:
                    label.config(text="Running", foreground="green")
                else:
                    label.config(text="Stopped", foreground="red")
    
    def _select_mode(self, mode: GuiMode) -> None:
        """Select GUI mode and close selector."""
        self.selected_mode = mode
        if self.root:
            self.root.quit()
        
        # Launch selected mode
        if mode == GuiMode.USER:
            self._launch_user_gui()
        elif mode == GuiMode.ADMIN:
            self._launch_admin_gui()
        elif mode == GuiMode.NODE:
            self._launch_node_gui()
    
    def _launch_user_gui(self) -> None:
        """Launch user interface."""
        self.logger.info("Launching User Interface")
        try:
            # Import and launch user GUI
            from src.gui.user.user_gui import UserGui
            user_gui = UserGui()
            user_gui.run()
        except ImportError as e:
            self.logger.error(f"Failed to import user GUI: {e}")
            self._launch_fallback_gui("User Interface", "src/gui/user/user_gui.py")
    
    def _launch_admin_gui(self) -> None:
        """Launch admin interface."""
        self.logger.info("Launching Admin Interface")
        try:
            # Import and launch admin GUI
            from src.gui.admin.admin_gui import AdminGui
            admin_gui = AdminGui()
            admin_gui.run()
        except ImportError as e:
            self.logger.error(f"Failed to import admin GUI: {e}")
            self._launch_fallback_gui("Admin Interface", "src/gui/admin/admin_gui.py")
    
    def _launch_node_gui(self) -> None:
        """Launch node interface."""
        self.logger.info("Launching Node Interface")
        try:
            # Import and launch node GUI
            from src.gui.node.node_gui import NodeGui
            node_gui = NodeGui()
            node_gui.run()
        except ImportError as e:
            self.logger.error(f"Failed to import node GUI: {e}")
            self._launch_fallback_gui("Node Interface", "src/gui/node/node_gui.py")
    
    def _launch_fallback_gui(self, title: str, module_path: str) -> None:
        """Launch fallback GUI when imports fail."""
        self.root = tk.Tk()
        self.root.title(f"Lucid - {title}")
        self.root.geometry("400x300")
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"Loading {title}...", 
                 font=("Arial", 14)).pack(pady=20)
        
        ttk.Label(frame, text="If this interface doesn't load properly,", 
                 font=("Arial", 10)).pack()
        ttk.Label(frame, text="please check that all dependencies are installed.", 
                 font=("Arial", 10)).pack()
        
        ttk.Button(frame, text="Exit", command=self.root.quit).pack(pady=20)
        
        self.root.mainloop()
    
    def _center_window(self) -> None:
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')


def main():
    """Main entry point for GUI launcher."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Lucid GUI Launcher')
    parser.add_argument('--mode', choices=['user', 'admin', 'node', 'auto'], 
                       default='auto', help='GUI mode to launch')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Set debug mode
    if args.debug:
        os.environ['LUCID_DEBUG'] = '1'
    
    # Launch GUI
    launcher = GuiLauncher()
    launcher.run(GuiMode(args.mode))


if __name__ == '__main__':
    main()
