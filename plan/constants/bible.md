# Lucid Container Operations Guide

## Foundation & Infrastructure

- **`pickme/lucid-tor-proxy`**  
  Distroless Tor gateway. Builds a full Tor system on Debian 12, copies the binaries into a minimal runtime, and runs `entrypoint.sh` to start Tor, monitor bootstrap progress, and optionally create ephemeral `.onion` addresses. Compose launches it under `tini` and expects health via `/usr/local/bin/tor-health`.

- **`pickme/lucid-base` / `pickme/lucid-base:python-distroless-arm64` / `pickme/lucid-base:java-distroless-arm64`**  
  Hardened base toolboxes. Each image copies a curated Python virtual environment, exposes a bootstrap script (`lucid-base-bootstrap`, `python-base-bootstrap`, `java-base-bootstrap`) that idles until exec’d, and enforces `no-new-privileges`, read-only root, and tmpfs `/tmp`. Compose keeps them running as auxiliary nodes for diagnostics and just-in-time commands.

- **`pickme/lucid-server-tools`**  
  Operations toolbox. Stages a Debian builder with networking utilities (curl, jq, tcpdump, nmap, MongoDB tools, etc.), then repackages into a distroless runtime with a `server-tools-bootstrap` script that blocks until commands are fed in.

- **`pickme/lucid-mongodb`**  
  Distroless MongoDB. Copies the upstream MongoDB binary plus required libraries into `gcr.io/distroless/base-debian12`; runs `mongod` with authentication, read-only rootfs, tmpfs `/tmp`, and `python3` socket health checks.

- **`pickme/lucid-redis`**  
  Distroless Redis. Pulls `redis:7.2` as a builder, copies `redis-server`/`redis-cli`, and adds a Python socket health check. Compose sets `--requirepass`, stores data under `/data`, and keeps the container read-only with tmpfs `/tmp`.

- **`pickme/lucid-elasticsearch`**  
  Distroless Elasticsearch 8.11.0. Uses the official image as a builder, copies Java 17 runtime and Elasticsearch libraries into `distroless/java17`, and starts Elasticsearch via `java -Des.*` options from compose.

- **`pickme/lucid-auth-service`**  
  Python auth API running on a distroless base. Compose launches `python3 main.py`, wiring MongoDB, Redis, and Tor.

- **`pickme/lucid-service-mesh-controller`**  
  Python-based Consul/Envoy controller packaged in `distroless/python3`. All configuration (ports 8500/8501/8502/8600/8088, Connect support, TLS) comes from environment files; compose runs the async `controller.main`.

- **Shared logging & env management**  
  `pickme/lucid-server-tools`, the `pickme/lucid-base*` images, `pickme/lucid-service-mesh-controller`, and related containers mount logs to `/mnt/myssd/Lucid/Lucid/logs/<service>` and rely on `.env.foundation`, `.env.distroless`, and service-specific env files for runtime values.

## Core Services

- **`pickme/lucid-api-gateway`**  
  API ingress (FastAPI/NGINX). Accepts HTTP requests from clients or Tor proxy and fans out to internal services; compose typically publishes port 8080.

- **`pickme/lucid-blockchain-engine`, `pickme/lucid-block-manager`, `pickme/lucid-data-chain`, `pickme/lucid-session-anchoring`**  
  Distroless Python services managing Lucid’s PoOT consensus, block lifecycle, data pipelines, and anchoring. They run read-only, use tmpfs `/tmp`, and depend on the base toolboxes plus service mesh discovery.

- **Session microservices**  
  `pickme/lucid-session-pipeline`, `pickme/lucid-session-recorder`, `pickme/lucid-session-storage`, `pickme/lucid-session-processor`, `pickme/lucid-session-api` capture, process, and expose session data. Each image packages a Python app in a distroless base, resolves peers via service mesh, and writes logs under `/var/log/<service>`.

- **`pickme/lucid-service-mesh-controller`**  
  Orchestrates service discovery and mTLS (Consul/Envoy). Handles sidecar registration, certificate issuance, and exposes health endpoints for compose and monitoring systems.

## Application & GUI

- **`pickme/lucid-admin-interface`**  
  Admin dashboard (distroless Node/Electron/React). `docker-compose.foundation.yml` publishes it on TCP 8083.

- **`pickme/lucid-gui` / `pickme/lucid-rdp-*`**  
  Containers for the Electron GUI and XRDP environment. The XRDP stack is split into controller, monitor, server-manager, and xrdp binaries with explicit port exposure (e.g., 3389, 8095). Each mounts GUI configuration/logs and depends on the Tor proxy for secure remote access.

- **`pickme/tron-*` (or `pickme/lucid-tron-*`)**  
  TRON blockchain payment microservices—client, payment gateway, payout router, staking, USDT manager. Distroless Python/Node containers that talk to TronGrid. Compose uses a separate TRON network `lucid-tron-isolated` (172.21.0.0/16).

## Security & Monitoring

- **`pickme/lucid-tor-proxy` (revisited)**  
  Front-door security. Compose ties it to `.env.tor-proxy`, `.env.secrets`, `.env.foundation`, persists Tor data at `/mnt/myssd/Lucid/Lucid/data/tor`, and logs under `/logs/tor`.

- **Monitoring jobs**  
  Prometheus, Grafana, and exporters (referenced in `ops/monitoring`) scrape `lucid-service-mesh-controller`, the Tor proxy, and core services via their exposed health endpoints.

## Supporting Images

- **`pickme/lucid-server-tools`**  
  Maintenance shell packed with diagnostics utilities (curl, jq, tcpdump, python3) for on-device troubleshooting.

- **`pickme/lucid-redis` & `pickme/lucid-mongodb`**  
  Backbone for caching and persistence across auth/session/blockchain systems.

- **`pickme/lucid-base` series**  
  Exec-friendly utility containers for migrations, debugging, and shared scripts.

## Operational Alignment

- **Environment**  
  All containers pull configuration from `/mnt/myssd/Lucid/Lucid/configs/environment/.env.*`, with secrets stored in `.env.secrets`. `.env.distroless` supplies hardening flags (`SECURITY_OPT_NO_NEW_PRIVILEGES`, `CAP_DROP=ALL`), network assignments, and registry details.

- **Networking**  
  Default production bridge is `lucid-pi-network` (172.20.0.0/16). Specialized networks include `lucid-tron-isolated`, `lucid-distroless-production`, and `lucid-gui-network`.

- **Security posture**  
  Distroless base images, UID/GID 65532, read-only root filesystems, `no-new-privileges`, minimal `cap_add` (typically `NET_BIND_SERVICE`), and tmpfs `/tmp` to prevent writes on the root filesystem.

- **Compose & Kubernetes**  
  `configs/docker/docker-compose.foundation.yml` orchestrates the Pi deployment; Kubernetes manifests under `infrastructure/kubernetes` reference the same images/tags with native health checks and ConfigMaps for full-cluster operations.