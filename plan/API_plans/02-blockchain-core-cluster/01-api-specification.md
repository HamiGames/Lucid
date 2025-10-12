# Blockchain Core Cluster - API Specification

## OpenAPI 3.0 Specification

```yaml
openapi: 3.0.3
info:
  title: Lucid Blockchain Core (lucid_blocks)
  description: Core blockchain operations for the Lucid blockchain system - COMPLETELY ISOLATED from TRON
  version: 1.0.0
  contact:
    name: Lucid Development Team
    email: dev@lucid-blockchain.org
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://blockchain.lucid-blockchain.org/api/v1
    description: Production blockchain server
  - url: https://blockchain-dev.lucid-blockchain.org/api/v1
    description: Development blockchain server
  - url: http://localhost:8084/api/v1
    description: Local development server

security:
  - BearerAuth: []

paths:
  # Blockchain Information Endpoints
  /chain/info:
    get:
      tags: [Blockchain]
      summary: Get blockchain information
      description: Returns comprehensive information about the lucid_blocks blockchain network
      responses:
        '200':
          description: Blockchain information retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockchainInfo'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /chain/status:
    get:
      tags: [Blockchain]
      summary: Get blockchain status
      description: Returns the current status and health of the lucid_blocks blockchain
      responses:
        '200':
          description: Blockchain status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockchainStatus'
        '503':
          description: Blockchain service unavailable
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /chain/height:
    get:
      tags: [Blockchain]
      summary: Get current block height
      description: Returns the current height of the lucid_blocks blockchain
      responses:
        '200':
          description: Block height retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockHeight'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /chain/network:
    get:
      tags: [Blockchain]
      summary: Get network topology
      description: Returns information about the lucid_blocks network topology and peers
      responses:
        '200':
          description: Network information retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/NetworkInfo'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Block Management Endpoints
  /blocks:
    get:
      tags: [Blocks]
      summary: List blocks
      description: Returns a paginated list of blocks from the lucid_blocks blockchain
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            minimum: 1
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
        - name: height_from
          in: query
          schema:
            type: integer
            minimum: 0
        - name: height_to
          in: query
          schema:
            type: integer
            minimum: 0
        - name: sort
          in: query
          schema:
            type: string
            enum: [height_asc, height_desc, timestamp_asc, timestamp_desc]
            default: height_desc
      responses:
        '200':
          description: Blocks retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockListResponse'
        '400':
          description: Invalid query parameters
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /blocks/{block_id}:
    get:
      tags: [Blocks]
      summary: Get block by ID
      description: Returns detailed information about a specific block
      parameters:
        - name: block_id
          in: path
          required: true
          schema:
            type: string
            description: Block ID or hash
      responses:
        '200':
          description: Block details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockDetails'
        '404':
          description: Block not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /blocks/height/{height}:
    get:
      tags: [Blocks]
      summary: Get block by height
      description: Returns the block at the specified height
      parameters:
        - name: height
          in: path
          required: true
          schema:
            type: integer
            minimum: 0
      responses:
        '200':
          description: Block retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockDetails'
        '404':
          description: Block not found at specified height
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /blocks/latest:
    get:
      tags: [Blocks]
      summary: Get latest block
      description: Returns the most recently created block
      responses:
        '200':
          description: Latest block retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockDetails'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /blocks/validate:
    post:
      tags: [Blocks]
      summary: Validate block structure
      description: Validates the structure and integrity of a block
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BlockValidationRequest'
      responses:
        '200':
          description: Block validation completed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockValidationResponse'
        '400':
          description: Invalid block structure
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Transaction Endpoints
  /transactions:
    post:
      tags: [Transactions]
      summary: Submit transaction
      description: Submits a transaction to the lucid_blocks blockchain for processing
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TransactionSubmitRequest'
      responses:
        '202':
          description: Transaction submitted successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TransactionResponse'
        '400':
          description: Invalid transaction data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '429':
          description: Transaction rate limit exceeded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /transactions/{tx_id}:
    get:
      tags: [Transactions]
      summary: Get transaction details
      description: Returns detailed information about a specific transaction
      parameters:
        - name: tx_id
          in: path
          required: true
          schema:
            type: string
            description: Transaction ID or hash
      responses:
        '200':
          description: Transaction details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TransactionDetails'
        '404':
          description: Transaction not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /transactions/pending:
    get:
      tags: [Transactions]
      summary: List pending transactions
      description: Returns a list of transactions pending confirmation
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
      responses:
        '200':
          description: Pending transactions retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TransactionListResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /transactions/batch:
    post:
      tags: [Transactions]
      summary: Submit batch of transactions
      description: Submits multiple transactions in a single batch
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TransactionBatchRequest'
      responses:
        '202':
          description: Batch submitted successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TransactionBatchResponse'
        '400':
          description: Invalid batch data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '429':
          description: Batch rate limit exceeded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Session Anchoring Endpoints
  /anchoring/session:
    post:
      tags: [Anchoring]
      summary: Anchor session manifest
      description: Anchors a session manifest to the lucid_blocks blockchain
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SessionAnchoringRequest'
      responses:
        '202':
          description: Session anchoring initiated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionAnchoringResponse'
        '400':
          description: Invalid anchoring request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '429':
          description: Anchoring rate limit exceeded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /anchoring/session/{session_id}:
    get:
      tags: [Anchoring]
      summary: Get session anchoring status
      description: Returns the anchoring status for a specific session
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Session anchoring status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionAnchoringStatus'
        '404':
          description: Session anchoring not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /anchoring/verify:
    post:
      tags: [Anchoring]
      summary: Verify session anchoring
      description: Verifies the anchoring of a session manifest on the blockchain
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AnchoringVerificationRequest'
      responses:
        '200':
          description: Anchoring verification completed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnchoringVerificationResponse'
        '400':
          description: Invalid verification request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /anchoring/status:
    get:
      tags: [Anchoring]
      summary: Get anchoring service status
      description: Returns the current status of the anchoring service
      responses:
        '200':
          description: Anchoring service status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnchoringServiceStatus'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Consensus Endpoints
  /consensus/status:
    get:
      tags: [Consensus]
      summary: Get consensus status
      description: Returns the current status of the consensus mechanism
      responses:
        '200':
          description: Consensus status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ConsensusStatus'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /consensus/participants:
    get:
      tags: [Consensus]
      summary: List consensus participants
      description: Returns a list of nodes participating in consensus
      responses:
        '200':
          description: Consensus participants retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ConsensusParticipants'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /consensus/vote:
    post:
      tags: [Consensus]
      summary: Submit consensus vote
      description: Submits a vote for consensus on a block or proposal
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ConsensusVoteRequest'
      responses:
        '200':
          description: Vote submitted successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ConsensusVoteResponse'
        '400':
          description: Invalid vote data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /consensus/history:
    get:
      tags: [Consensus]
      summary: Get consensus history
      description: Returns the history of consensus decisions and votes
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
        - name: offset
          in: query
          schema:
            type: integer
            minimum: 0
            default: 0
      responses:
        '200':
          description: Consensus history retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ConsensusHistory'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Merkle Tree Endpoints
  /merkle/build:
    post:
      tags: [Merkle]
      summary: Build Merkle tree
      description: Builds a Merkle tree for session data validation
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MerkleTreeBuildRequest'
      responses:
        '200':
          description: Merkle tree built successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MerkleTreeResponse'
        '400':
          description: Invalid build request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /merkle/{root_hash}:
    get:
      tags: [Merkle]
      summary: Get Merkle tree details
      description: Returns detailed information about a Merkle tree
      parameters:
        - name: root_hash
          in: path
          required: true
          schema:
            type: string
            pattern: '^[a-fA-F0-9]{64}$'
      responses:
        '200':
          description: Merkle tree details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MerkleTreeDetails'
        '404':
          description: Merkle tree not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /merkle/verify:
    post:
      tags: [Merkle]
      summary: Verify Merkle tree proof
      description: Verifies a Merkle tree proof for data integrity
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MerkleProofVerificationRequest'
      responses:
        '200':
          description: Merkle proof verification completed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MerkleProofVerificationResponse'
        '400':
          description: Invalid verification request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /merkle/validation/{session_id}:
    get:
      tags: [Merkle]
      summary: Get Merkle tree validation status
      description: Returns the validation status of a Merkle tree for a session
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Validation status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MerkleValidationStatus'
        '404':
          description: Validation not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    # Blockchain Schemas
    BlockchainInfo:
      type: object
      properties:
        network_name:
          type: string
          example: "lucid_blocks"
        version:
          type: string
          example: "1.0.0"
        consensus_algorithm:
          type: string
          example: "PoOT"
        block_time_seconds:
          type: integer
          example: 10
        current_height:
          type: integer
          example: 12345
        genesis_block:
          type: string
          example: "0000000000000000000000000000000000000000000000000000000000000000"
        total_transactions:
          type: integer
          example: 98765
        network_hash_rate:
          type: number
          example: 1000.5
        difficulty:
          type: number
          example: 1.5

    BlockchainStatus:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, syncing, error]
        current_height:
          type: integer
        network_height:
          type: integer
        sync_percentage:
          type: number
          minimum: 0
          maximum: 100
        last_block_time:
          type: string
          format: date-time
        peer_count:
          type: integer
        consensus_participants:
          type: integer
        block_production_rate:
          type: number

    BlockHeight:
      type: object
      properties:
        height:
          type: integer
          example: 12345
        timestamp:
          type: string
          format: date-time

    NetworkInfo:
      type: object
      properties:
        peer_count:
          type: integer
        connected_peers:
          type: array
          items:
            $ref: '#/components/schemas/PeerInfo'
        network_latency_avg:
          type: number
        network_throughput:
          type: number
        consensus_participants:
          type: array
          items:
            $ref: '#/components/schemas/ConsensusParticipant'

    PeerInfo:
      type: object
      properties:
        peer_id:
          type: string
        address:
          type: string
        last_seen:
          type: string
          format: date-time
        latency_ms:
          type: number
        block_height:
          type: integer

    ConsensusParticipant:
      type: object
      properties:
        node_id:
          type: string
        address:
          type: string
        voting_power:
          type: number
        last_vote:
          type: string
          format: date-time
        participation_rate:
          type: number

    # Block Schemas
    BlockDetails:
      type: object
      properties:
        block_id:
          type: string
        height:
          type: integer
        hash:
          type: string
        previous_hash:
          type: string
        merkle_root:
          type: string
        timestamp:
          type: string
          format: date-time
        nonce:
          type: integer
        difficulty:
          type: number
        transaction_count:
          type: integer
        block_size_bytes:
          type: integer
        transactions:
          type: array
          items:
            $ref: '#/components/schemas/TransactionSummary'
        validator:
          type: string
        signature:
          type: string

    TransactionSummary:
      type: object
      properties:
        tx_id:
          type: string
        type:
          type: string
          enum: [session_anchor, data_storage, consensus_vote, system]
        size_bytes:
          type: integer
        fee:
          type: number
        timestamp:
          type: string
          format: date-time

    BlockListResponse:
      type: object
      properties:
        blocks:
          type: array
          items:
            $ref: '#/components/schemas/BlockSummary'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    BlockSummary:
      type: object
      properties:
        block_id:
          type: string
        height:
          type: integer
        hash:
          type: string
        timestamp:
          type: string
          format: date-time
        transaction_count:
          type: integer
        block_size_bytes:
          type: integer
        validator:
          type: string

    BlockValidationRequest:
      type: object
      required: [block_data]
      properties:
        block_data:
          type: object
          properties:
            height:
              type: integer
            hash:
              type: string
            previous_hash:
              type: string
            merkle_root:
              type: string
            timestamp:
              type: string
              format: date-time
            transactions:
              type: array
              items:
                type: object
            signature:
              type: string

    BlockValidationResponse:
      type: object
      properties:
        valid:
          type: boolean
        validation_results:
          type: object
          properties:
            structure_valid:
              type: boolean
            signature_valid:
              type: boolean
            merkle_root_valid:
              type: boolean
            timestamp_valid:
              type: boolean
            transactions_valid:
              type: boolean
        errors:
          type: array
          items:
            type: string

    # Transaction Schemas
    TransactionSubmitRequest:
      type: object
      required: [type, data, signature]
      properties:
        type:
          type: string
          enum: [session_anchor, data_storage, consensus_vote, system]
        data:
          type: object
        signature:
          type: string
        fee:
          type: number
          minimum: 0
        timestamp:
          type: string
          format: date-time

    TransactionResponse:
      type: object
      properties:
        tx_id:
          type: string
        status:
          type: string
          enum: [pending, confirmed, failed]
        submitted_at:
          type: string
          format: date-time
        confirmation_time:
          type: string
          format: date-time
        block_height:
          type: integer

    TransactionDetails:
      type: object
      properties:
        tx_id:
          type: string
        type:
          type: string
        data:
          type: object
        signature:
          type: string
        fee:
          type: number
        status:
          type: string
        submitted_at:
          type: string
          format: date-time
        confirmed_at:
          type: string
          format: date-time
        block_height:
          type: integer
        block_hash:
          type: string
        transaction_index:
          type: integer

    TransactionListResponse:
      type: object
      properties:
        transactions:
          type: array
          items:
            $ref: '#/components/schemas/TransactionSummary'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    TransactionBatchRequest:
      type: object
      required: [transactions]
      properties:
        transactions:
          type: array
          items:
            $ref: '#/components/schemas/TransactionSubmitRequest'
          minItems: 1
          maxItems: 100

    TransactionBatchResponse:
      type: object
      properties:
        batch_id:
          type: string
        submitted_count:
          type: integer
        failed_count:
          type: integer
        transaction_ids:
          type: array
          items:
            type: string
        errors:
          type: array
          items:
            type: string

    # Anchoring Schemas
    SessionAnchoringRequest:
      type: object
      required: [session_id, manifest_data, merkle_root]
      properties:
        session_id:
          type: string
          format: uuid
        manifest_data:
          type: object
          properties:
            chunk_count:
              type: integer
            total_size:
              type: integer
            created_at:
              type: string
              format: date-time
        merkle_root:
          type: string
          pattern: '^[a-fA-F0-9]{64}$'
        user_signature:
          type: string

    SessionAnchoringResponse:
      type: object
      properties:
        anchoring_id:
          type: string
        status:
          type: string
          enum: [pending, processing, confirmed, failed]
        submitted_at:
          type: string
          format: date-time
        estimated_confirmation_time:
          type: string
          format: date-time

    SessionAnchoringStatus:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        anchoring_id:
          type: string
        status:
          type: string
          enum: [pending, processing, confirmed, failed]
        submitted_at:
          type: string
          format: date-time
        confirmed_at:
          type: string
          format: date-time
        block_height:
          type: integer
        transaction_id:
          type: string
        merkle_root:
          type: string

    AnchoringVerificationRequest:
      type: object
      required: [session_id, merkle_root]
      properties:
        session_id:
          type: string
          format: uuid
        merkle_root:
          type: string
          pattern: '^[a-fA-F0-9]{64}$'

    AnchoringVerificationResponse:
      type: object
      properties:
        verified:
          type: boolean
        block_height:
          type: integer
        transaction_id:
          type: string
        confirmation_time:
          type: string
          format: date-time
        merkle_proof_valid:
          type: boolean

    AnchoringServiceStatus:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, busy, error]
        pending_anchorings:
          type: integer
        processing_anchorings:
          type: integer
        completed_today:
          type: integer
        average_confirmation_time:
          type: number

    # Consensus Schemas
    ConsensusStatus:
      type: object
      properties:
        status:
          type: string
          enum: [active, voting, error]
        current_round:
          type: integer
        participants_count:
          type: integer
        voting_threshold:
          type: number
        last_consensus_time:
          type: string
          format: date-time
        consensus_algorithm:
          type: string
          example: "PoOT"

    ConsensusParticipants:
      type: object
      properties:
        participants:
          type: array
          items:
            $ref: '#/components/schemas/ConsensusParticipant'
        total_participants:
          type: integer
        active_participants:
          type: integer

    ConsensusVoteRequest:
      type: object
      required: [vote_type, target_id, vote_decision, signature]
      properties:
        vote_type:
          type: string
          enum: [block_validation, proposal_vote, participant_selection]
        target_id:
          type: string
        vote_decision:
          type: string
          enum: [approve, reject, abstain]
        reasoning:
          type: string
        signature:
          type: string

    ConsensusVoteResponse:
      type: object
      properties:
        vote_id:
          type: string
        status:
          type: string
          enum: [accepted, rejected, pending]
        submitted_at:
          type: string
          format: date-time
        vote_weight:
          type: number

    ConsensusHistory:
      type: object
      properties:
        history:
          type: array
          items:
            $ref: '#/components/schemas/ConsensusEvent'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    ConsensusEvent:
      type: object
      properties:
        event_id:
          type: string
        event_type:
          type: string
        target_id:
          type: string
        result:
          type: string
        participants:
          type: array
          items:
            type: string
        timestamp:
          type: string
          format: date-time

    # Merkle Tree Schemas
    MerkleTreeBuildRequest:
      type: object
      required: [session_id, chunk_hashes]
      properties:
        session_id:
          type: string
          format: uuid
        chunk_hashes:
          type: array
          items:
            type: string
            pattern: '^[a-fA-F0-9]{64}$'
        metadata:
          type: object

    MerkleTreeResponse:
      type: object
      properties:
        tree_id:
          type: string
        root_hash:
          type: string
        tree_height:
          type: integer
        leaf_count:
          type: integer
        created_at:
          type: string
          format: date-time
        session_id:
          type: string
          format: uuid

    MerkleTreeDetails:
      type: object
      properties:
        tree_id:
          type: string
        root_hash:
          type: string
        tree_height:
          type: integer
        leaf_count:
          type: integer
        created_at:
          type: string
          format: date-time
        session_id:
          type: string
          format: uuid
        nodes:
          type: array
          items:
            $ref: '#/components/schemas/MerkleNode'

    MerkleNode:
      type: object
      properties:
        node_id:
          type: string
        hash:
          type: string
        level:
          type: integer
        position:
          type: integer
        is_leaf:
          type: boolean
        parent_hash:
          type: string
        left_child_hash:
          type: string
        right_child_hash:
          type: string

    MerkleProofVerificationRequest:
      type: object
      required: [root_hash, leaf_hash, proof_path]
      properties:
        root_hash:
          type: string
          pattern: '^[a-fA-F0-9]{64}$'
        leaf_hash:
          type: string
          pattern: '^[a-fA-F0-9]{64}$'
        proof_path:
          type: array
          items:
            type: string
            pattern: '^[a-fA-F0-9]{64}$'

    MerkleProofVerificationResponse:
      type: object
      properties:
        verified:
          type: boolean
        proof_valid:
          type: boolean
        leaf_exists:
          type: boolean
        verification_time_ms:
          type: number

    MerkleValidationStatus:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        tree_id:
          type: string
        status:
          type: string
          enum: [building, built, validated, failed]
        validation_results:
          type: object
          properties:
            structure_valid:
              type: boolean
            hash_consistency:
              type: boolean
            proof_verification:
              type: boolean
        errors:
          type: array
          items:
            type: string

    # Common Schemas
    PaginationInfo:
      type: object
      properties:
        page:
          type: integer
        limit:
          type: integer
        total:
          type: integer
        pages:
          type: integer

    ErrorResponse:
      type: object
      properties:
        error:
          type: object
          properties:
            code:
              type: string
              example: "LUCID_ERR_4001"
            message:
              type: string
              example: "Block not found"
            details:
              type: object
              additionalProperties: true
            request_id:
              type: string
              format: uuid
            timestamp:
              type: string
              format: date-time
            service:
              type: string
              example: "lucid-blocks"
            version:
              type: string
              example: "v1"

tags:
  - name: Blockchain
    description: Core blockchain information and status
  - name: Blocks
    description: Block management and validation
  - name: Transactions
    description: Transaction processing and management
  - name: Anchoring
    description: Session manifest anchoring to blockchain
  - name: Consensus
    description: Consensus mechanism operations (PoOT)
  - name: Merkle
    description: Merkle tree operations and validation
```

## Rate Limiting Specifications

### Blockchain-Specific Rate Limiting

```yaml
rate_limits:
  blockchain_queries:
    requests_per_minute: 500
    burst_size: 1000
    endpoints:
      - "/api/v1/chain/*"
      - "/api/v1/blocks"
      - "/api/v1/blocks/*"
  
  transaction_submission:
    requests_per_minute: 100
    burst_size: 200
    endpoints:
      - "/api/v1/transactions"
      - "/api/v1/transactions/batch"
  
  session_anchoring:
    requests_per_minute: 50
    burst_size: 100
    endpoints:
      - "/api/v1/anchoring/*"
  
  consensus_operations:
    requests_per_minute: 200
    burst_size: 400
    endpoints:
      - "/api/v1/consensus/*"
  
  merkle_operations:
    requests_per_minute: 300
    burst_size: 600
    endpoints:
      - "/api/v1/merkle/*"
```

## Error Code Registry

### Blockchain-Specific Error Codes

```yaml
error_codes:
  # Block Errors (LUCID_ERR_4XXX)
  "LUCID_ERR_4001": "Block not found"
  "LUCID_ERR_4002": "Invalid block structure"
  "LUCID_ERR_4003": "Block validation failed"
  "LUCID_ERR_4004": "Block signature invalid"
  "LUCID_ERR_4005": "Merkle root mismatch"
  "LUCID_ERR_4006": "Block timestamp invalid"
  "LUCID_ERR_4007": "Block height mismatch"
  "LUCID_ERR_4008": "Block size limit exceeded"
  
  # Transaction Errors (LUCID_ERR_5XXX)
  "LUCID_ERR_5001": "Transaction not found"
  "LUCID_ERR_5002": "Invalid transaction format"
  "LUCID_ERR_5003": "Transaction signature invalid"
  "LUCID_ERR_5004": "Transaction fee insufficient"
  "LUCID_ERR_5005": "Transaction rate limit exceeded"
  "LUCID_ERR_5006": "Batch transaction failed"
  "LUCID_ERR_5007": "Transaction confirmation timeout"
  
  # Anchoring Errors (LUCID_ERR_6XXX)
  "LUCID_ERR_6001": "Session anchoring not found"
  "LUCID_ERR_6002": "Invalid anchoring request"
  "LUCID_ERR_6003": "Anchoring verification failed"
  "LUCID_ERR_6004": "Manifest data invalid"
  "LUCID_ERR_6005": "Anchoring rate limit exceeded"
  "LUCID_ERR_6006": "Session already anchored"
  
  # Consensus Errors (LUCID_ERR_7XXX)
  "LUCID_ERR_7001": "Consensus participant not authorized"
  "LUCID_ERR_7002": "Invalid consensus vote"
  "LUCID_ERR_7003": "Consensus timeout"
  "LUCID_ERR_7004": "Insufficient consensus participants"
  "LUCID_ERR_7005": "Consensus vote signature invalid"
  "LUCID_ERR_7006": "Consensus round not active"
  
  # Merkle Tree Errors (LUCID_ERR_8XXX)
  "LUCID_ERR_8001": "Merkle tree not found"
  "LUCID_ERR_8002": "Invalid Merkle tree structure"
  "LUCID_ERR_8003": "Merkle proof verification failed"
  "LUCID_ERR_8004": "Merkle tree build failed"
  "LUCID_ERR_8005": "Invalid chunk hash"
  "LUCID_ERR_8006": "Merkle tree height limit exceeded"
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
