"""Auth Service Client"""
from gui_api_bridge.gui_api_bridge.service_base import ServiceBaseClient

class AuthServiceClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("auth-service", config.AUTH_SERVICE_URL, config)
