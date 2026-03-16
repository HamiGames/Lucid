"""TRON Payment Client"""
from ...gui_api_bridge.integration.service_base import ServiceBaseClient

class TronClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("tron-client", config.TRON_PAYMENT_URL, config)
