"""TRON Payment Client"""
from .service_base import ServiceBaseClient

class TronClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("tron-client", config.TRON_PAYMENT_URL, config)
