"""API Gateway Client
file: /app/gui_api_bridge/gui_api_bridge/integration/api_gateway_client.py
x-lucid-file-path: /app/gui_api_bridge/gui_api_bridge/integration/api_gateway_client.py
x-lucid-file-type: python

"""
from ...gui_api_bridge.integration.service_base import ServiceBaseClient

class APIGatewayClient(ServiceBaseClient):
    def __init__(self, config):
        super().__init__("api-gateway", config.API_GATEWAY_URL, config)
