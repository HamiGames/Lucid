# Path: vm/__init__.py
"""
File: /app/vm/__init__.py
x-lucid-file-path: /app/vm/__init__.py
x-lucid-file-type: python

Virtual Machine package for Lucid RDP.
Handles lightweight VM orchestration using Docker containers.
"""

from vm.vm_manager import VMManager, VMInstance

__all__ = ["VMManager", "VMInstance"]
