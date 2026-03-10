"""Node Management Client"""
from gui_api_bridge.gui_api_bridge.service_base import ServiceBaseClient

class NodeManagementClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("node-management", config.NODE_MANAGEMENT_URL, config)
