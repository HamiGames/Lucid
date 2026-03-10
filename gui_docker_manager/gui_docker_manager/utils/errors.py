"""
Error Definitions
File: gui_docker_manager/gui_docker_manager/utils/errors.py
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
