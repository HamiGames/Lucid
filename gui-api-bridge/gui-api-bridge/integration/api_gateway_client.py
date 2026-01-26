"""API Gateway Client"""
from .service_base import ServiceBaseClient

class APIGatewayClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("api-gateway", config.API_GATEWAY_URL, config)
