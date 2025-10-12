# Path: vm/__init__.py
"""
Virtual Machine package for Lucid RDP.
Handles lightweight VM orchestration using Docker containers.
"""

from vm.vm_manager import VMManager, VMInstance

__all__ = ["VMManager", "VMInstance"]
