"""
Service mesh package for Lucid RDP.
Contains service mesh controller and orchestration components.

Modules:
- config: Environment-based configuration
- consul_manager: Consul service discovery integration
- certificate_manager: mTLS certificate management
- envoy_config_generator: Envoy proxy configuration
- service_mesh_translator: Host-config aligned routes, auth principals, Tor/tunnel endpoints
- main: FastAPI application entry point
- controller: Controller module for Docker CMD
"""

