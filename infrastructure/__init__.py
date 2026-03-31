# Infrastructure Module
# Infrastructure as Code components for the Lucid RDP platform

"""
File: /app/infrastructure/__init__.py
x-lucid-file-path: /app/infrastructure/__init__.py
x-lucid-file-directory: /app/infrastructure
x-lucid-file-type: python

Infrastructure package for Lucid RDP.
Contains Docker, Kubernetes, Terraform, and service mesh configurations.
"""

# Import submodules when they exist
try:
    from .service_mesh import *
except ImportError:
    pass

__all__ = []
