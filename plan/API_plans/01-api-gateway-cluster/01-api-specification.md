# API Gateway Cluster - API Specification

## OpenAPI 3.0 Specification

```yaml
openapi: 3.0.3
info:
  title: Lucid API Gateway
  description: Primary entry point for all Lucid blockchain system APIs
  version: 1.0.0
  contact:
    name: Lucid Development Team
    email: dev@lucid-blockchain.org
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://api.lucid-blockchain.org/api/v1
    description: Production server
  - url: https://api-dev.lucid-blockchain.org/api/v1
    description: Development server
  - url: http://localhost:8080/api/v1
    description: Local development server

security:
  - BearerAuth: []
  - ApiKeyAuth: []

paths:
  # Meta Endpoints
  /meta/info:
    get:
      tags: [Meta]
      summary: Get service information
      description: Returns comprehensive information about the API Gateway service
      security: []
      responses:
        '200':
          description: Service information retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ServiceInfo'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /meta/health:
    get:
      tags: [Meta]
      summary: Health check endpoint
      description: Returns the health status of the API Gateway and its dependencies
      security: []
      responses:
        '200':
          description: Service is healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthStatus'
        '503':
          description: Service is unhealthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthStatus'

  /meta/version:
    get:
      tags: [Meta]
      summary: Get API version information
      description: Returns version information for the API Gateway and supported API versions
      security: []
      responses:
        '200':
          description: Version information retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VersionInfo'

  /meta/metrics:
    get:
      tags: [Meta]
      summary: Get service metrics
      description: Returns performance and operational metrics for the API Gateway
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Metrics retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MetricsResponse'

  # Authentication Endpoints
  /auth/login:
    post:
      tags: [Authentication]
      summary: Initiate magic link login
      description: Initiates a magic link authentication flow
      security: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LoginRequest'
      responses:
        '200':
          description: Magic link sent successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LoginResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '429':
          description: Rate limit exceeded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /auth/verify:
    post:
      tags: [Authentication]
      summary: Verify TOTP code
      description: Verifies the TOTP code and completes authentication
      security: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/VerifyRequest'
      responses:
        '200':
          description: Authentication successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'
        '400':
          description: Invalid verification code
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Authentication failed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /auth/refresh:
    post:
      tags: [Authentication]
      summary: Refresh access token
      description: Refreshes an expired access token using a valid refresh token
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RefreshRequest'
      responses:
        '200':
          description: Token refreshed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'
        '401':
          description: Invalid or expired refresh token
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /auth/logout:
    post:
      tags: [Authentication]
      summary: Logout user
      description: Invalidates the current access token and logs out the user
      responses:
        '200':
          description: Logout successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LogoutResponse'
        '401':
          description: Invalid or expired token
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /auth/status:
    get:
      tags: [Authentication]
      summary: Get authentication status
      description: Returns the current authentication status and user information
      responses:
        '200':
          description: Authentication status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthStatusResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # User Management Endpoints
  /users/me:
    get:
      tags: [Users]
      summary: Get current user information
      description: Returns detailed information about the currently authenticated user
      responses:
        '200':
          description: User information retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    put:
      tags: [Users]
      summary: Update user profile
      description: Updates the profile information for the currently authenticated user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserUpdateRequest'
      responses:
        '200':
          description: User profile updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /users/{user_id}:
    get:
      tags: [Users]
      summary: Get user by ID
      description: Returns information about a specific user by their ID
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: User information retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '403':
          description: Access denied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: User not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /users:
    post:
      tags: [Users]
      summary: Create new user account
      description: Creates a new user account with the provided information
      security: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserCreateRequest'
      responses:
        '201':
          description: User account created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '409':
          description: User already exists
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Session Management Endpoints
  /sessions:
    get:
      tags: [Sessions]
      summary: List user sessions
      description: Returns a paginated list of sessions for the authenticated user
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
        - name: status
          in: query
          schema:
            type: string
            enum: [active, completed, failed, cancelled]
        - name: sort
          in: query
          schema:
            type: string
            enum: [created_at, updated_at, name]
            default: created_at
      responses:
        '200':
          description: Sessions retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionListResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    post:
      tags: [Sessions]
      summary: Create new session
      description: Creates a new recording session with the specified configuration
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SessionCreateRequest'
      responses:
        '201':
          description: Session created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '429':
          description: Rate limit exceeded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /sessions/{session_id}:
    get:
      tags: [Sessions]
      summary: Get session details
      description: Returns detailed information about a specific session
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Session details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '403':
          description: Access denied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Session not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    put:
      tags: [Sessions]
      summary: Update session
      description: Updates the configuration or status of an existing session
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SessionUpdateRequest'
      responses:
        '200':
          description: Session updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '403':
          description: Access denied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Session not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    delete:
      tags: [Sessions]
      summary: Delete session
      description: Deletes an existing session and all associated data
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '204':
          description: Session deleted successfully
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '403':
          description: Access denied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Session not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Manifest Endpoints
  /manifests/{manifest_id}:
    get:
      tags: [Manifests]
      summary: Get manifest details
      description: Returns detailed information about a specific manifest
      parameters:
        - name: manifest_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Manifest details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ManifestResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '403':
          description: Access denied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Manifest not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /manifests:
    post:
      tags: [Manifests]
      summary: Create new manifest
      description: Creates a new manifest for session data
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ManifestCreateRequest'
      responses:
        '201':
          description: Manifest created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ManifestResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Trust Policy Endpoints
  /trust/policies:
    get:
      tags: [Trust]
      summary: List trust policies
      description: Returns a list of trust policies for the authenticated user
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
      responses:
        '200':
          description: Trust policies retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TrustPolicyListResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    post:
      tags: [Trust]
      summary: Create trust policy
      description: Creates a new trust policy with the specified configuration
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TrustPolicyCreateRequest'
      responses:
        '201':
          description: Trust policy created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TrustPolicyResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /trust/policies/{policy_id}:
    put:
      tags: [Trust]
      summary: Update trust policy
      description: Updates an existing trust policy
      parameters:
        - name: policy_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TrustPolicyUpdateRequest'
      responses:
        '200':
          description: Trust policy updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TrustPolicyResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '403':
          description: Access denied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Trust policy not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Chain Proxy Endpoints
  /chain/info:
    get:
      tags: [Chain]
      summary: Get blockchain information
      description: Returns information about the lucid_blocks blockchain
      responses:
        '200':
          description: Blockchain information retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockchainInfoResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '503':
          description: Blockchain service unavailable
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /chain/blocks:
    get:
      tags: [Chain]
      summary: List blockchain blocks
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
        - name: height
          in: query
          schema:
            type: integer
            minimum: 0
        - name: hash
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Blocks retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockListResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /chain/blocks/{block_id}:
    get:
      tags: [Chain]
      summary: Get block details
      description: Returns detailed information about a specific block
      parameters:
        - name: block_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Block details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BlockResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Block not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /chain/transactions:
    post:
      tags: [Chain]
      summary: Submit transaction
      description: Submits a transaction to the lucid_blocks blockchain
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
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Wallets Proxy Endpoints
  /wallets:
    get:
      tags: [Wallets]
      summary: List user wallets
      description: Returns a list of wallets for the authenticated user
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
      responses:
        '200':
          description: Wallets retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WalletListResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    post:
      tags: [Wallets]
      summary: Create new wallet
      description: Creates a new wallet for the authenticated user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/WalletCreateRequest'
      responses:
        '201':
          description: Wallet created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WalletResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /wallets/{wallet_id}:
    get:
      tags: [Wallets]
      summary: Get wallet details
      description: Returns detailed information about a specific wallet
      parameters:
        - name: wallet_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Wallet details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WalletResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '403':
          description: Access denied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Wallet not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /wallets/{wallet_id}/transactions:
    post:
      tags: [Wallets]
      summary: Create wallet transaction
      description: Creates a new transaction for the specified wallet
      parameters:
        - name: wallet_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/WalletTransactionRequest'
      responses:
        '201':
          description: Transaction created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WalletTransactionResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '403':
          description: Access denied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Wallet not found
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
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

  schemas:
    # Meta Schemas
    ServiceInfo:
      type: object
      properties:
        service_name:
          type: string
          example: "api-gateway"
        version:
          type: string
          example: "1.0.0"
        build_date:
          type: string
          format: date-time
        environment:
          type: string
          example: "production"
        features:
          type: array
          items:
            type: string
          example: ["authentication", "rate_limiting", "ssl_termination"]

    HealthStatus:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, unhealthy, degraded]
        timestamp:
          type: string
          format: date-time
        service:
          type: string
          example: "api-gateway"
        version:
          type: string
          example: "1.0.0"
        dependencies:
          type: object
          additionalProperties:
            type: string
            enum: [healthy, unhealthy, unknown]
        uptime:
          type: integer
          description: "Uptime in seconds"
        response_time:
          type: number
          description: "Average response time in milliseconds"

    VersionInfo:
      type: object
      properties:
        api_version:
          type: string
          example: "v1"
        gateway_version:
          type: string
          example: "1.0.0"
        supported_versions:
          type: array
          items:
            type: string
          example: ["v1"]
        deprecation_notice:
          type: string
          nullable: true

    MetricsResponse:
      type: object
      properties:
        timestamp:
          type: string
          format: date-time
        metrics:
          type: object
          properties:
            requests_per_second:
              type: number
            response_time_p50:
              type: number
            response_time_p95:
              type: number
            response_time_p99:
              type: number
            error_rate:
              type: number
            active_connections:
              type: integer

    # Authentication Schemas
    LoginRequest:
      type: object
      required: [email]
      properties:
        email:
          type: string
          format: email
        hardware_wallet:
          type: boolean
          default: false

    LoginResponse:
      type: object
      properties:
        message:
          type: string
          example: "Magic link sent to your email"
        expires_in:
          type: integer
          description: "Expiration time in seconds"
          example: 300

    VerifyRequest:
      type: object
      required: [email, code]
      properties:
        email:
          type: string
          format: email
        code:
          type: string
          minLength: 6
          maxLength: 6

    AuthResponse:
      type: object
      properties:
        access_token:
          type: string
        refresh_token:
          type: string
        token_type:
          type: string
          example: "Bearer"
        expires_in:
          type: integer
          description: "Access token expiration in seconds"
        user:
          $ref: '#/components/schemas/UserResponse'

    RefreshRequest:
      type: object
      required: [refresh_token]
      properties:
        refresh_token:
          type: string

    LogoutResponse:
      type: object
      properties:
        message:
          type: string
          example: "Successfully logged out"

    AuthStatusResponse:
      type: object
      properties:
        authenticated:
          type: boolean
        user:
          $ref: '#/components/schemas/UserResponse'
        token_expires_at:
          type: string
          format: date-time

    # User Schemas
    UserResponse:
      type: object
      properties:
        user_id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        username:
          type: string
        first_name:
          type: string
        last_name:
          type: string
        role:
          type: string
          enum: [user, node_operator, admin, super_admin]
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        last_login:
          type: string
          format: date-time
        hardware_wallet_enabled:
          type: boolean

    UserCreateRequest:
      type: object
      required: [email, username, password]
      properties:
        email:
          type: string
          format: email
        username:
          type: string
          minLength: 3
          maxLength: 50
        password:
          type: string
          minLength: 8
        first_name:
          type: string
        last_name:
          type: string

    UserUpdateRequest:
      type: object
      properties:
        username:
          type: string
          minLength: 3
          maxLength: 50
        first_name:
          type: string
        last_name:
          type: string
        hardware_wallet_enabled:
          type: boolean

    # Session Schemas
    SessionResponse:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        status:
          type: string
          enum: [active, completed, failed, cancelled]
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        started_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
        duration:
          type: integer
          description: "Duration in seconds"
        size_bytes:
          type: integer
        chunk_count:
          type: integer

    SessionCreateRequest:
      type: object
      required: [name]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        description:
          type: string
          maxLength: 1000

    SessionUpdateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        description:
          type: string
          maxLength: 1000
        status:
          type: string
          enum: [active, completed, failed, cancelled]

    SessionListResponse:
      type: object
      properties:
        sessions:
          type: array
          items:
            $ref: '#/components/schemas/SessionResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    # Manifest Schemas
    ManifestResponse:
      type: object
      properties:
        manifest_id:
          type: string
          format: uuid
        session_id:
          type: string
          format: uuid
        merkle_root:
          type: string
        chunk_count:
          type: integer
        total_size:
          type: integer
        created_at:
          type: string
          format: date-time
        chunks:
          type: array
          items:
            $ref: '#/components/schemas/ChunkInfo'

    ManifestCreateRequest:
      type: object
      required: [session_id]
      properties:
        session_id:
          type: string
          format: uuid

    ChunkInfo:
      type: object
      properties:
        chunk_id:
          type: string
          format: uuid
        index:
          type: integer
        size:
          type: integer
        hash:
          type: string
        created_at:
          type: string
          format: date-time

    # Trust Policy Schemas
    TrustPolicyResponse:
      type: object
      properties:
        policy_id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        rules:
          type: array
          items:
            $ref: '#/components/schemas/TrustRule'
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    TrustPolicyCreateRequest:
      type: object
      required: [name, rules]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        description:
          type: string
          maxLength: 1000
        rules:
          type: array
          items:
            $ref: '#/components/schemas/TrustRule'

    TrustPolicyUpdateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        description:
          type: string
          maxLength: 1000
        rules:
          type: array
          items:
            $ref: '#/components/schemas/TrustRule'

    TrustPolicyListResponse:
      type: object
      properties:
        policies:
          type: array
          items:
            $ref: '#/components/schemas/TrustPolicyResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    TrustRule:
      type: object
      properties:
        rule_id:
          type: string
        type:
          type: string
          enum: [allow, deny]
        condition:
          type: string
        action:
          type: string

    # Chain Schemas
    BlockchainInfoResponse:
      type: object
      properties:
        network_name:
          type: string
          example: "lucid_blocks"
        version:
          type: string
        current_height:
          type: integer
        genesis_block:
          type: string
        consensus_algorithm:
          type: string
          example: "PoOT"
        block_time:
          type: integer
          description: "Average block time in seconds"

    BlockResponse:
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
        timestamp:
          type: string
          format: date-time
        transactions:
          type: array
          items:
            $ref: '#/components/schemas/TransactionInfo'
        merkle_root:
          type: string

    BlockListResponse:
      type: object
      properties:
        blocks:
          type: array
          items:
            $ref: '#/components/schemas/BlockResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    TransactionSubmitRequest:
      type: object
      required: [type, data]
      properties:
        type:
          type: string
          enum: [session_anchor, payout, governance]
        data:
          type: object
        signature:
          type: string

    TransactionResponse:
      type: object
      properties:
        transaction_id:
          type: string
        status:
          type: string
          enum: [pending, confirmed, failed]
        submitted_at:
          type: string
          format: date-time
        confirmed_at:
          type: string
          format: date-time

    TransactionInfo:
      type: object
      properties:
        transaction_id:
          type: string
        type:
          type: string
        status:
          type: string
        timestamp:
          type: string
          format: date-time

    # Wallet Schemas
    WalletResponse:
      type: object
      properties:
        wallet_id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        name:
          type: string
        address:
          type: string
        balance:
          type: number
        currency:
          type: string
          example: "USDT"
        network:
          type: string
          example: "TRON"
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    WalletCreateRequest:
      type: object
      required: [name, currency]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        currency:
          type: string
          enum: [USDT, TRX]
        network:
          type: string
          enum: [TRON]
          default: "TRON"

    WalletListResponse:
      type: object
      properties:
        wallets:
          type: array
          items:
            $ref: '#/components/schemas/WalletResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    WalletTransactionRequest:
      type: object
      required: [type, amount, recipient]
      properties:
        type:
          type: string
          enum: [transfer, payment]
        amount:
          type: number
          minimum: 0
        recipient:
          type: string
        currency:
          type: string
          enum: [USDT, TRX]
        memo:
          type: string

    WalletTransactionResponse:
      type: object
      properties:
        transaction_id:
          type: string
        status:
          type: string
          enum: [pending, confirmed, failed]
        amount:
          type: number
        currency:
          type: string
        recipient:
          type: string
        created_at:
          type: string
          format: date-time

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
              example: "LUCID_ERR_1001"
            message:
              type: string
              example: "Invalid request data"
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
              example: "api-gateway"
            version:
              type: string
              example: "v1"

tags:
  - name: Meta
    description: Service metadata and health information
  - name: Authentication
    description: User authentication and authorization
  - name: Users
    description: User management operations
  - name: Sessions
    description: Session lifecycle management
  - name: Manifests
    description: Session manifest operations
  - name: Trust
    description: Trust policy management
  - name: Chain
    description: Blockchain operations (lucid_blocks)
  - name: Wallets
    description: Wallet and payment operations
```

## Rate Limiting Specifications

### Tiered Rate Limiting Implementation

```yaml
rate_limits:
  public_endpoints:
    requests_per_minute: 100
    burst_size: 200
    endpoints:
      - "/api/v1/meta/*"
      - "/api/v1/auth/login"
      - "/api/v1/auth/verify"
      - "/api/v1/users"
  
  authenticated_endpoints:
    requests_per_minute: 1000
    burst_size: 2000
    endpoints:
      - "/api/v1/users/*"
      - "/api/v1/sessions/*"
      - "/api/v1/manifests/*"
      - "/api/v1/trust/*"
      - "/api/v1/chain/*"
      - "/api/v1/wallets/*"
  
  admin_endpoints:
    requests_per_minute: 10000
    burst_size: 20000
    endpoints:
      - "/api/v1/admin/*"
      - "/api/v1/meta/metrics"
  
  chunk_uploads:
    bytes_per_second: 10485760  # 10 MB/sec
    endpoints:
      - "/api/v1/sessions/*/chunks"
  
  blockchain_queries:
    requests_per_minute: 500
    burst_size: 1000
    endpoints:
      - "/api/v1/chain/blocks"
      - "/api/v1/chain/blocks/*"
```

## Error Code Registry

### Validation Errors (LUCID_ERR_1XXX)
- `LUCID_ERR_1001`: Invalid request data
- `LUCID_ERR_1002`: Missing required field
- `LUCID_ERR_1003`: Invalid field format
- `LUCID_ERR_1004`: Field value out of range
- `LUCID_ERR_1005`: Invalid UUID format
- `LUCID_ERR_1006`: Invalid email format
- `LUCID_ERR_1007`: Password too weak
- `LUCID_ERR_1008`: Invalid date format
- `LUCID_ERR_1009`: Invalid JSON format
- `LUCID_ERR_1010`: Request too large

### Authentication Errors (LUCID_ERR_2XXX)
- `LUCID_ERR_2001`: Invalid credentials
- `LUCID_ERR_2002`: Token expired
- `LUCID_ERR_2003`: Token invalid
- `LUCID_ERR_2004`: Insufficient permissions
- `LUCID_ERR_2005`: Account locked
- `LUCID_ERR_2006`: Magic link expired
- `LUCID_ERR_2007`: TOTP code invalid
- `LUCID_ERR_2008`: Hardware wallet error
- `LUCID_ERR_2009`: Session expired
- `LUCID_ERR_2010`: Refresh token invalid

### Rate Limiting Errors (LUCID_ERR_3XXX)
- `LUCID_ERR_3001`: Rate limit exceeded
- `LUCID_ERR_3002`: Quota exceeded
- `LUCID_ERR_3003`: Too many requests
- `LUCID_ERR_3004`: Bandwidth limit exceeded
- `LUCID_ERR_3005`: Concurrent request limit

### Business Logic Errors (LUCID_ERR_4XXX)
- `LUCID_ERR_4001`: Resource not found
- `LUCID_ERR_4002`: Resource already exists
- `LUCID_ERR_4003`: Operation not allowed
- `LUCID_ERR_4004`: Insufficient balance
- `LUCID_ERR_4005`: Session size limit exceeded
- `LUCID_ERR_4006`: Chunk size limit exceeded
- `LUCID_ERR_4007`: Invalid session state
- `LUCID_ERR_4008`: Transaction failed
- `LUCID_ERR_4009`: Blockchain service unavailable
- `LUCID_ERR_4010`: Payment service unavailable

### System Errors (LUCID_ERR_5XXX)
- `LUCID_ERR_5001`: Internal server error
- `LUCID_ERR_5002`: Database connection error
- `LUCID_ERR_5003`: External service error
- `LUCID_ERR_5004`: Configuration error
- `LUCID_ERR_5005`: Network error
- `LUCID_ERR_5006`: Timeout error
- `LUCID_ERR_5007`: Circuit breaker open
- `LUCID_ERR_5008`: Service unavailable
- `LUCID_ERR_5009`: Maintenance mode
- `LUCID_ERR_5010`: Unknown error

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
