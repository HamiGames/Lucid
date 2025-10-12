# API Build Architecture Document

## Overview

Create a comprehensive API Creators Document that consolidates all API architecture, designs, REST endpoints, and blockchain protocol methods from the Lucid project documentation.

## Document Structure

### 1. Executive Summary

- Project overview and API ecosystem
- Architecture principles (microservices, distroless, Tor-only)
- Service isolation (Ops Plane, Chain Plane, Wallet Plane)

### 2. Core API Architecture

- **Three-Tier Architecture**
- Blockchain Tier (On-System Data Chain)
- Payment Tier (TRON - ISOLATED)
- Container Tier (Distroless)
- **Service Topology**
- API Gateway (Cluster A) - Port 8080/8081
- Blockchain Core (Cluster B) - Port 8084
- Supporting services (RDP, Sessions, Admin, Node)

### 3. REST API Endpoints by Service

#### 3.1 API Gateway Service

- Meta endpoints (/, /health, /meta/ping)
- Authentication endpoints (/auth/*)
- User management (/users/*)
- Session management (/sessions/*)
- Manifest & proof retrieval (/sessions/{id}/manifest, /sessions/{id}/merkle-proof)
- Trust policy enforcement (/sessions/{id}/policy)
- Proxy endpoints (chain, wallets)

#### 3.2 Blockchain Core Service

- Chain information (/chain/info, /chain/height, /chain/balance)
- Wallet operations (/wallets/*, /wallets/{id}/transfer)
- Contract deployment endpoints

#### 3.3 RDP Server Management

- Session lifecycle (/sessions/create, /sessions/{id}/start, /sessions/{id}/stop)
- XRDP integration (/start, /stop, /restart, /status)

#### 3.4 Session Management

- Recording control (/recordings/start, /recordings/{id}/stop)
- Session state transitions

#### 3.5 Node Management

- Node status and control (/api/node/status, /api/node/start, /api/node/stop)
- Pool management (/api/node/join_pool, /api/node/leave_pool)

#### 3.6 Admin Interface

- Dashboard and monitoring
- Session administration
- Blockchain anchoring and payout triggers

### 4. Blockchain Protocol Methods

#### 4.1 On-System Data Chain RPC

- **Session Anchoring**
- anchor_session_manifest(session_id, merkle_root, chunk_count)
- anchor_chunk(session_id, chunk_hash, sequence)
- verify_anchor(txid)

- **Consensus (PoOT)**
- get_leader_schedule(epoch)
- submit_task_proof(proof_type, entity_id, value)
- calculate_work_credits(epoch)

- **Chain Operations**
- get_chain_info()
- get_block_height()
- get_transaction_status(txid)

#### 4.2 TRON Network RPC (Isolated)

- **Payout Operations**
- initiate_payout(recipient, amount_usdt)
- check_payout_status(txid)
- get_balance(address)

- **Contract Interactions**
- call_payout_router(method, params)
- call_payout_router_kyc(method, params)

#### 4.3 Merkle Tree & Verification

- build_merkle_tree(chunk_hashes)
- get_merkle_proof(chunk_id)
- verify_merkle_proof(chunk_hash, proof, root)

### 5. Data Flow Architecture

#### 5.1 Session Lifecycle Flow

1. Session Creation → Initialization
2. Recording Start → Chunk Processing
3. Chunk Encryption → Storage
4. Merkle Tree Building → Manifest Creation
5. Blockchain Anchoring → Verification
6. Payout Calculation → Distribution

#### 5.2 State Transitions

- Session states: INITIALIZING → RECORDING → FINALIZING → ANCHORING → COMPLETED
- Chunk states: CREATED → ENCRYPTED → ANCHORED
- Payout states: PENDING → CONFIRMED → FAILED

### 6. API Design Patterns

#### 6.1 RESTful Design

- HTTP methods: GET, POST, PUT, DELETE
- Resource-based URLs
- Standard status codes (200, 201, 400, 401, 403, 404, 409, 422, 500)
- Pagination for list endpoints
- Query parameters for filtering

#### 6.2 Error Handling

- Standard error response format
- Error codes and messages
- Request tracking (X-Request-ID)

#### 6.3 API Versioning

- OpenAPI 3.0 specification
- Version in URL or headers
- Backward compatibility considerations

### 7. Integration Patterns

#### 7.1 Inter-Service Communication

- API Gateway → Blockchain Core (proxy routing)
- Session Manager → Blockchain Core (anchoring)
- Admin UI → All Services (monitoring)
- RDP Manager → Session Recorder (coordination)
- Node Manager → Blockchain Core (registration)

#### 7.2 External Integrations

- TRON Network (blockchain operations)
- MongoDB (persistence)
- Tor Network (secure communication)
- File System (chunk storage)

### 8. Network Architecture

#### 8.1 Service Planes

- **Ops Plane**: API Gateway, monitoring, orchestration
- **Chain Plane**: Blockchain services, consensus, anchoring
- **Wallet Plane**: Payment processing, TRON integration

#### 8.2 Network Isolation

- Separate Docker networks per plane
- Tor-only ingress/egress
- Internal service communication

### 9. Database Schema (MongoDB)

#### 9.1 Collections

- sessions (session metadata and state)
- chunks (chunk data and encryption info)
- control_policies (trust policies)
- anchors (blockchain anchor receipts)
- payouts (payment transactions)

#### 9.2 Indexes

- Performance-optimized indexes for queries
- Compound indexes for filtering

### 10. OpenAPI Specification Structure

#### 10.1 API Documentation

- Swagger/ReDoc endpoints
- Request/response schemas
- Authentication requirements
- Example requests and responses

#### 10.2 Schema Definitions

- Common data models
- Request bodies
- Response formats
- Error schemas

## Source Documentation References

### Key Files to Extract From:

1. `docs/guides/API_IMPLEMENTATION_GUIDE.md` - Session Management API details
2. `docs/analysis/LUCID_API_ELEMENTS_COMPREHENSIVE_SUMMARY.md` - Complete API inventory
3. `03-api-gateway/gateway/openapi.yaml` - OpenAPI specification
4. `docs/guides/AUTHENTICATION_IMPLEMENTATION_GUIDE.md` - Auth endpoints (security ref only)
5. `blockchain/core/blockchain_engine.py` - Blockchain RPC methods
6. `docs/build-docs/Build_guide_docs/Spec-1d` - Component connectivity
7. Service files (RDP, Sessions, Node, Admin) - Endpoint definitions

## Output Location

- **File**: `plan/API_plans/API_BUILD_ARCH.md`
- **Format**: Markdown with clear sections, tables, and code blocks
- **Style**: Architectural focus, no implementation code

## Deliverable

A comprehensive API architecture document that serves as a reference for all API designs, methods, REST endpoints, and blockchain protocol methods in the Lucid RDP project.
