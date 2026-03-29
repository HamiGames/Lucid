"""
File: /app/gui_docker_manager/gui_docker_manager/utils/errors.py
x-lucid-file-path: /app/gui_docker_manager/gui_docker_manager/utils/errors.py
x-lucid-file-type: python

Error Definitions
"""


class DockerManagerError(Exception):
    """Base exception for Docker Manager"""
    pass


class PermissionDeniedError(DockerManagerError):
    """Permission denied error"""
    pass


class ContainerNotFoundError(DockerManagerError):
    """Container not found error"""
    pass


class DockerDaemonError(DockerManagerError):
    """Docker daemon connection error"""
    pass
