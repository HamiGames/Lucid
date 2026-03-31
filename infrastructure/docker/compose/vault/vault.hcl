# Repo path: infrastructure/docker/compose/vault/vault.hcl
# x-files.json section_to_canonical: infrastructure/docker/compose/vault/vault.hcl → /app/configs/docker/compose/vault/vault.hcl
# Canonical (image layout): /app/configs/docker/compose/vault/vault.hcl
# Referenced from: infrastructure/docker/compose/docker-compose*.yml
# host-config.yml: cross-check vault-facing service ports exposed in compose

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
