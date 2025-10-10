# Vault configuration file for Lucid project

# Storage backend
storage "file" {
  path = "/vault/data"
}

# Listener configuration
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true
}

# API address
api_addr = "http://0.0.0.0:8200"

# Cluster address
cluster_addr = "http://0.0.0.0:8201"

# UI
ui = true

# Log level
log_level = "INFO"

# Default lease TTL
default_lease_ttl = "168h"

# Max lease TTL
max_lease_ttl = "720h"
