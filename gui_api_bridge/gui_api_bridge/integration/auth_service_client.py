"""Auth Service Client
file: /app/gui_api_bridge/gui_api_bridge/integration/auth_service_client.py
x-lucid-file-path: /app/gui_api_bridge/gui_api_bridge/integration/auth_service_client.py

"""
from ...gui_api_bridge.integration.service_base import ServiceBaseClient

class AuthServiceClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("auth-service", config.AUTH_SERVICE_URL, config)
