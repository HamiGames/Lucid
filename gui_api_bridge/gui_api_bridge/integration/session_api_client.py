"""Session API Client
file: /app/gui_api_bridge/gui_api_bridge/integration/session_api_client.py
x-lucid-file-path: /app/gui_api_bridge/gui_api_bridge/integration/session_api_client.py
x-lucid-file-type: python"""
from ...gui_api_bridge.integration.service_base import ServiceBaseClient

class SessionAPIClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("session-api", config.SESSION_API_URL, config)
