# SPEC-4 — Clustered Build Stages & Content Inclusion (GitOps Console)

## Background

This document prescribes **what to build, package, and include** per **container cluster** using the **GitOps single-console** model. It aligns with platform constraints: Tor-only transport, plane isolation (ops/chain/wallet), MongoDB 7 (replica/shard), immutable anchoring via the On‑System Data Chain, isolated TRON interaction, and domain-based clusters with a common `beta` sidecar.

---

## Cluster taxonomy (profiles)

Each physical/virtual site runs the same `infrastructure/compose/docker-compose.yml`; **profiles** enable the role for that site. All clusters run the **`beta` sidecar** and expose onion endpoints per plane (no plane bridging).

- **Blockchain Group**: `blockchain-core`, `blockchain-ledger`, `blockchain-virtual-machine`, `blockchain-sessions-data`, `blockchain-governances`.

- **Sessions Group**: `sessions-gateway`, `sessions-manifests`, `sessions-index`.

- **Node Systems Group**: `node-worker`, `node-data-host`, `node-economy`, `node-governances`.

- **Admin/Wallet Group**: `admin-api`, `admin-ui`, `walletd`, `tron-node`, `observer`.

- **Observability Group**: `metrics`, `logs`, `anomaly`.

- **Relay/Directory (optional)**: `cloud-relay`, `mongos-onion`.

**Interdependencies (plane-scoped links)**

- `sessions-manifests@chain` ↔ `blockchain-virtual-machine@chain` (anchoring/contracts)

- `node-worker@ops` ↔ `sessions-gateway@ops` (session join/control)

- `node-economy@wallet` → `tron-node@wallet` (payouts)

- `sessions-index@chain` → `blockchain-sessions-data@chain` (reads)

---

## Build stages — overview

Each stage yields **signed, pinned-digest images**, encrypted config, and profile-scoped manifests. Stages are designed to **roll forward independently** with health‑gated promotion.

1. **Stage 0 — Common & Base**: base images, `beta` sidecar, shared libraries, CI policy.

1. **Stage 1 — Blockchain Group**: consensus, ledger, VM, governance, session-data indexers.

1. **Stage 2 — Sessions Group**: ingress, manifests, index/query services.

1. **Stage 3 — Node Systems Group**: recorder pipeline, storage/DHT, economy.

1. **Stage 4 — Admin/Wallet Group**: admin APIs/UI, walletd, tron-node.

1. **Stage 5 — Observability Group**: metrics, logs, anomaly.

1. **Stage 6 — Relay/Directory (optional)**: onion relay, mongos router.

Each stage lists **content inclusion** (what must ship in each container), **secrets/env**, **tests**, **health**, **rollout**.

---

## Stage 0 — Common & Base

**Artifacts**

- `docker/Dockerfile.base` (build toolchain; Node 20 + Python 3.12; FFmpeg toolchain; libsodium/BLAKE3)

- `beta` sidecar image (Tor runtime, onion publisher, discovery, name resolution, ACLs)

- Policy & CI: cosign verification, SBOM scan, compose/profile lint, SOPS secrets check

**Content inclusion**

- **Beta**: Tor v3 HS; per‑plane onion services; label watcher (`com.lucid.plane`, `com.lucid.service`, `com.lucid.expose`); resolution API; QUIC/UDP ban; fail‑closed; per‑plane ACLs

- **Base**: non‑root runtime users; read‑only rootfs where possible; seccomp/caps drop

**Secrets/Env**

- `AGE_PRIVATE_KEY` for SOPS; `BETA_CLUSTER_ID`; per‑plane onion keys

**Tests/Health**

- `betactl health` must pass; onion publish per plane; CI policy gates must pass

**Rollout**

- Always deploy **Stage 0** first; all later stages depend on `beta` availability

---

## Stage 1 — Blockchain Group

**Services**: `blockchain-core`, `blockchain-ledger`, `blockchain-virtual-machine`, `blockchain-sessions-data`, `blockchain-governances`

**Content inclusion**

- *blockchain-core*: validator/consensus node; block gossip; governance hooks; read‑only onion metrics

- *blockchain-ledger*: archival/state; snapshot importer/exporter; compaction jobs

- *blockchain-virtual-machine*: contract execution layer (TVM/EVM‑compatible); ABI services for anchors/payout routers

- *blockchain-sessions-data*: indexer that tails anchor events and mirrors minimal manifest fields for fast read

- *blockchain-governances*: proposal/vote/timelock executor; ParamRegistry writer; read‑only public endpoints

**Secrets/Env**

- Validator keys (sealed); ParamRegistry bounds; indexer RPC endpoints; read pins for sessions-data

**Tests/Health**

- Unit: contract interfaces; governance bounds; indexer parsers

- Integration: anchor + chunk event ingestion; replay from block N; consensus liveness under churn

- Health: VM latency budget; indexer caught‑up; governance timelock status

**Rollout**

- Canary 1 node → quorum ≥3 validators; enable sessions-data after core is healthy

---

## Stage 2 — Sessions Group

**Services**: `sessions-gateway`, `sessions-manifests`, `sessions-index`

**Content inclusion**

- *sessions-gateway*: mint single‑use Session IDs; ingress control; privacy policy negotiation; ops plane onion

- *sessions-manifests*: Merkle builder & anchor orchestrator; writes to On‑System Data Chain; optional per‑chunk anchors

- *sessions-index*: read‑only API for manifests/proofs; token‑scoped; pagination and filters

**Secrets/Env**

- Session key derivation salt; JWT signing keys; policy snapshot pins; plane allow‑lists

**Tests/Health**

- Unit: Merkle root vectors (BLAKE3); ID minting; token scopes

- Integration: end‑to‑end anchor path (manifest → events); index queries vs sample data

- Health: onion availability; anchor queue depth; index query SLOs

**Rollout**

- Deploy next to Blockchain Group (low latency chain plane); verify anchor latency before scaling out

---

## Stage 3 — Node Systems Group

**Services**: `node-worker`, `node-data-host`, `node-economy`, `node-governances`

**Content inclusion**

- *node-worker*: recorder (xrdp/FFmpeg with Pi HW encode), chunker (8–16 MB, Zstd), encryptor (XChaCha20‑Poly1305), Merkle builder (BLAKE3); emits incident flags on AEAD failure

- *node-data-host*: encrypted chunk store; DHT/CRDT peer; availability beacons; repair jobs

- *node-economy*: payout aggregator; reason‑code encoder; monthly batching; writes receipts

- *node-governances*: consumes governance snapshots; exposes read‑only status

**Secrets/Env**

- Encoder caps; DHT seeds; S3/MinIO creds (client‑side encrypted); payout policy; cluster labels (site/hardware)

**Tests/Health**

- Unit: chunk boundaries; nonce uniqueness; HKDF vectors; Zstd ratios

- Integration: record→chunk→encrypt→anchor golden path on Pi; DHT 3‑node gossip; payouts on testnet

- Health: CPU budget under encode; DHT availability; payout queue age

**Rollout**

- Edge sites first; autoscale `node-worker`; gate on encode CPU and DHT health

---

## Stage 4 — Admin/Wallet Group

**Services**: `admin-api`, `admin-ui`, `walletd`, `tron-node`, `observer`

**Content inclusion**

- *admin-api*: read‑only endpoints for manifests/proofs; diagnostics; token scopes; observer role

- *admin-ui*: provisioning wizard; manifests/proofs viewer; payout tools; key rotation; backups; OTA

- *walletd*: keystore (Ledger or SW vault), role‑based signing; multisig flows; rotation

- *tron-node*: isolated TRON client; payout routers (PR0/PRKYC) bindings; circuit breakers; rate‑limited

- *observer*: read‑only views; no wallet plane access

**Secrets/Env**

- Admin accounts (magic link + TOTP); Ledger derivations; TRON RPC onion; payout caps; OTA signing keys

**Tests/Health**

- Unit: UI reducers/forms; router ABI; keystore lock/unlock; 2‑of‑3 flows

- Integration: Shasta payouts (PR0/PRKYC); key rotation; observer access scoping

- Health: onion reachability; wallet plane deny‑by‑default verified; payout tx receipts

**Rollout**

- Bring up **after** Blockchain + Sessions; wallet plane isolated; enable payouts only after dry‑run

---

## Stage 5 — Observability Group

**Services**: `metrics`, `logs`, `anomaly`

**Content inclusion**

- *metrics*: Prometheus‑compatible scrape targets via onion; per‑plane views; SLO burn alerts

- *logs*: Tor‑egressed log shipper; privacy filters; redaction before export

- *anomaly*: session abuse heuristics; rate limits; alerts (no write‑paths to wallet)

**Secrets/Env**

- Scrape tokens; log signing keys; alert routes

**Tests/Health**

- Integration: scrape over Tor; log redaction; anomaly triggers; rate limit enforcement

- Health: dashboards reachable via onion; alert delivery SLOs

**Rollout**

- Deploy alongside each group; read‑only ACLs enforced by `beta`

---

## Stage 6 — Relay/Directory (optional)

**Services**: `cloud-relay`, `mongos-onion`

**Content inclusion**

- *cloud-relay*: rendezvous/directory shard; rate‑limited metadata relay; DHT bootstrap

- *mongos-onion*: proxy/router for MongoDB behind onion; read‑only auth where applicable

**Secrets/Env**

- Relay keys; directory shard ranges; mongos credentials

**Tests/Health**

- Integration: onion rendezvous; directory convergence; mongos cross‑cluster queries

- Health: relay throttle; directory freshness

**Rollout**

- Optional; deploy after core groups; can be withdrawn without breaking P2P paths

---

## GitOps assets & repos

**Config Repo** (single source of truth)

- `/infrastructure/compose/docker-compose.yml` (multi‑profile)

- `/clusters/clusters.yaml` (inventory, waves)

- `/clusters/<id>/.env` (plane pins, onions, shard roles)

- `/policies/` (signatures, SBOM, profile allow‑lists)

- `/secrets/*.enc.yaml` (SOPS/age)

**Reconciler loop (per cluster)**

1. Pull latest commit via onion Git

1. Verify signatures & SBOM; fetch images from onion registry mirror

1. Render compose with this cluster’s profiles/env

1. `docker compose up -d --remove-orphans`

1. Wait on service health; promote on success or auto‑rollback

---

## Content inclusion matrix (by container)

| Container | Must include | Should include |

|---|---|---|

| `node-worker` | xrdp + FFmpeg (Pi HW encode); chunker(Zstd 8–16MB); encryptor(XChaCha20‑Poly1305); Merkle(BLAKE3) | adaptive bitrate; privacy shield presets |

| `node-data-host` | encrypted chunk store; DHT/CRDT; repair | S3/MinIO encrypted export |

| `sessions-manifests` | manifest schema; anchor(manifest/root) | per‑chunk anchors toggle |

| `blockchain-virtual-machine` | anchor & payout ABIs | gas/energy budgeting metrics |

| `blockchain-ledger` | archival/state; snapshot tools | compaction scheduler |

| `admin-api` | read‑only manifests/proofs; observer role | diagnostics export |

| `walletd` | keystore; role‑based signing; multisig | Ledger integration |

| `tron-node` | PR0/PRKYC bindings; circuit breakers | energy staking controls |

| `metrics/logs/anomaly` | Tor-only scrape/ship; rate limit heuristics | privacy redaction rules |

| `cloud-relay` | directory shards; rendezvous; throttling | mongos onion helper |

---

## Rollout & waves (suggested)

- **Wave canary**: 1× Blockchain + 1× Sessions

- **Wave core**: all Blockchain + Sessions sites

- **Wave edge**: Node clusters by region

- **Wave admin**: Admin/Wallet

- **Wave obs/relay**: Observability and optional Relay

Gates: healthchecks pass; `beta` published onions per plane; anchor latency < budget; wallet plane isolation verified.

---

## Acceptance checks (per cluster)

- **Blockchain**: consensus stable; VM ABI tests pass; sessions-data caught up

- **Sessions**: Merkle vectors match; anchors present; index queries OK

- **Node**: encode CPU within budget; DHT availability ≥ target; sample payloads anchored

- **Admin/Wallet**: payout dry-run passes; keys rotate; observer scoped

- **Observability**: scrapes via onion; alerts deliver; anomaly rate within threshold

- **Relay**: directory converges; mongos queries cross-cluster

---

## Appendix — profile map & env

**Profiles**: `blockchain`, `sessions`, `node`, `admin`, `observability`, `relay`

**Env template (`clusters/<id>/.env`)**

```javascript

CLUSTER_ID=<id>
PROFILES=<comma-separated>
BETA_PLANES=ops,chain,wallet
TOR_SOCKS=beta:9050
MONGO_RS=rs0
MONGO_SHARD_RANGE=<low>-<high>
TRON_MODE=shasta|mainnet
S3_ENDPOINT=<onion>
S3_ACCESS_KEY=enc:sops
S3_SECRET_KEY=enc:sops
LEDGER_PUBKEYS=enc:sops

```

---

## Notes

- All cross‑cluster traffic rides Tor v3; **no QUIC/UDP** and **fail‑closed** when Tor is down.

- The `wallet` plane is deny‑by‑default; only `walletd` ↔ `tron-node` are permitted, via `beta` ACLs.

- Everything is **idempotent** under the reconciler; manual drift is corrected by the next commit.
