"""Admin Interface Client
file: /app/gui_api_bridge/gui_api_bridge/integration/admin_interface_client.py
purpose: Admin interface client for the GUI API bridge
x-lucid-file-id: 1234567890
x-lucid-file-name: admin_interface_client.py
x-lucid-file-path: /app/gui_api_bridge/gui_api_bridge/integration/admin_interface_client.py
x-lucid-file-type: python
x-lucid-file-size: 100
x-lucid-file-hash: 1234567890
x-lucid-file-created: 2021-01-01
x-lucid-file-modified: 2021-01-01
"""
from ...gui_api_bridge.integration.service_base import ServiceBaseClient

class AdminInterfaceClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("admin-interface", config.ADMIN_INTERFACE_URL, config)
