"""TRON Payment Client
file: /app/gui_api_bridge/gui_api_bridge/integration/tron_client.py
x-lucid-file-path: /app/gui_api_bridge/gui_api_bridge/integration/tron_client.py
x-lucid-file-type: python
"""
from ...gui_api_bridge.integration.service_base import ServiceBaseClient

class TronClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("tron-client", config.TRON_PAYMENT_URL, config)
