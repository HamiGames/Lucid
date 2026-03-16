"""Admin Interface Client"""
from ...gui_api_bridge.integration.service_base import ServiceBaseClient

class AdminInterfaceClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("admin-interface", config.ADMIN_INTERFACE_URL, config)
