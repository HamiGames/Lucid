"""Auth Service Client"""
from .service_base import ServiceBaseClient

class AuthServiceClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("auth-service", config.AUTH_SERVICE_URL, config)
