"""Session API Client"""
from .service_base import ServiceBaseClient

class SessionAPIClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("session-api", config.SESSION_API_URL, config)
