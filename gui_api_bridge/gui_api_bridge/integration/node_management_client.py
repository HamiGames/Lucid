"""Node Management Client

file: /app/gui_api_bridge/gui_api_bridge/integration/node_management_client.py
x-lucid-file-path: /app/gui_api_bridge/gui_api_bridge/integration/node_management_client.py
x-lucid-file-type: python
"""
from ...gui_api_bridge.integration.service_base import ServiceBaseClient

class NodeManagementClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("node-management", config.NODE_MANAGEMENT_URL, config)
