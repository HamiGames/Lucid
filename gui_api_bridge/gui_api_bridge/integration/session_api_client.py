"""Session API Client"""
from gui_api_bridge.gui_api_bridge.service_base import ServiceBaseClient

class SessionAPIClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("session-api", config.SESSION_API_URL, config)
