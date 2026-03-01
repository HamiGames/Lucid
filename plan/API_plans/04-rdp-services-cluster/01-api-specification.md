# RDP Services Cluster - API Specification

## OpenAPI 3.0 Specification

```yaml
openapi: 3.0.3
info:
  title: Lucid RDP Services API
  description: Remote Desktop Protocol services for the Lucid system
  version: 1.0.0
  contact:
    name: Lucid Development Team
    email: dev@lucid-blockchain.org
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://rdp-services.lucid-blockchain.org/api/v1
    description: Production RDP services server
  - url: https://rdp-services-dev.lucid-blockchain.org/api/v1
    description: Development RDP services server
  - url: http://localhost:8090/api/v1
    description: Local development server

security:
  - BearerAuth: []

paths:
  # RDP Server Management Endpoints
  /rdp/servers:
    get:
      tags: [RDP Servers]
      summary: List RDP servers
      description: Returns a list of RDP server instances
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
            enum: [running, stopped, error, maintenance]
        - name: user_id
          in: query
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: RDP servers retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpServerListResponse'
        '401':
          description: Not authenticated
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

    post:
      tags: [RDP Servers]
      summary: Create RDP server
      description: Creates a new RDP server instance
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RdpServerCreateRequest'
      responses:
        '201':
          description: RDP server created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpServerResponse'
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
          description: Insufficient permissions
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /rdp/servers/{server_id}:
    get:
      tags: [RDP Servers]
      summary: Get RDP server details
      description: Returns detailed information about a specific RDP server
      parameters:
        - name: server_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: RDP server details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpServerResponse'
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
          description: RDP server not found
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

    put:
      tags: [RDP Servers]
      summary: Update RDP server
      description: Updates RDP server configuration
      parameters:
        - name: server_id
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
              $ref: '#/components/schemas/RdpServerUpdateRequest'
      responses:
        '200':
          description: RDP server updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpServerResponse'
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
          description: RDP server not found
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

    delete:
      tags: [RDP Servers]
      summary: Delete RDP server
      description: Deletes an RDP server instance
      parameters:
        - name: server_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '204':
          description: RDP server deleted successfully
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
          description: RDP server not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '409':
          description: Server has active sessions
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

  /rdp/servers/{server_id}/start:
    post:
      tags: [RDP Servers]
      summary: Start RDP server
      description: Starts an RDP server instance
      parameters:
        - name: server_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: RDP server started successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpServerActionResponse'
        '400':
          description: Invalid request
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
          description: RDP server not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '409':
          description: Server already running
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

  /rdp/servers/{server_id}/stop:
    post:
      tags: [RDP Servers]
      summary: Stop RDP server
      description: Stops an RDP server instance
      parameters:
        - name: server_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: force
          in: query
          schema:
            type: boolean
            default: false
            description: Force stop even with active sessions
      responses:
        '200':
          description: RDP server stopped successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpServerActionResponse'
        '400':
          description: Invalid request
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
          description: RDP server not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '409':
          description: Cannot stop server with active sessions
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

  /rdp/servers/{server_id}/restart:
    post:
      tags: [RDP Servers]
      summary: Restart RDP server
      description: Restarts an RDP server instance
      parameters:
        - name: server_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: force
          in: query
          schema:
            type: boolean
            default: false
            description: Force restart even with active sessions
      responses:
        '200':
          description: RDP server restarted successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpServerActionResponse'
        '400':
          description: Invalid request
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
          description: RDP server not found
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

  /rdp/servers/{server_id}/status:
    get:
      tags: [RDP Servers]
      summary: Get RDP server status
      description: Returns the current status of an RDP server
      parameters:
        - name: server_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: RDP server status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpServerStatusResponse'
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
          description: RDP server not found
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

  # XRDP Integration Endpoints
  /xrdp/config:
    get:
      tags: [XRDP Integration]
      summary: Get XRDP configuration
      description: Returns the current XRDP configuration
      responses:
        '200':
          description: XRDP configuration retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/XrdpConfigResponse'
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    put:
      tags: [XRDP Integration]
      summary: Update XRDP configuration
      description: Updates the XRDP configuration
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/XrdpConfigUpdateRequest'
      responses:
        '200':
          description: XRDP configuration updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/XrdpConfigResponse'
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /xrdp/service/start:
    post:
      tags: [XRDP Integration]
      summary: Start XRDP service
      description: Starts the XRDP service
      responses:
        '200':
          description: XRDP service started successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/XrdpServiceActionResponse'
        '400':
          description: Invalid request
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
        '409':
          description: Service already running
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

  /xrdp/service/stop:
    post:
      tags: [XRDP Integration]
      summary: Stop XRDP service
      description: Stops the XRDP service
      responses:
        '200':
          description: XRDP service stopped successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/XrdpServiceActionResponse'
        '400':
          description: Invalid request
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /xrdp/service/restart:
    post:
      tags: [XRDP Integration]
      summary: Restart XRDP service
      description: Restarts the XRDP service
      responses:
        '200':
          description: XRDP service restarted successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/XrdpServiceActionResponse'
        '400':
          description: Invalid request
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /xrdp/service/status:
    get:
      tags: [XRDP Integration]
      summary: Get XRDP service status
      description: Returns the current status of the XRDP service
      responses:
        '200':
          description: XRDP service status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/XrdpServiceStatusResponse'
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Session Management Endpoints
  /sessions:
    get:
      tags: [Sessions]
      summary: List RDP sessions
      description: Returns a list of active RDP sessions
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
        - name: user_id
          in: query
          schema:
            type: string
            format: uuid
        - name: server_id
          in: query
          schema:
            type: string
            format: uuid
        - name: status
          in: query
          schema:
            type: string
            enum: [active, disconnected, terminated]
      responses:
        '200':
          description: RDP sessions retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpSessionListResponse'
        '401':
          description: Not authenticated
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

    post:
      tags: [Sessions]
      summary: Create RDP session
      description: Creates a new RDP session
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RdpSessionCreateRequest'
      responses:
        '201':
          description: RDP session created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpSessionResponse'
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
          description: Insufficient permissions
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /sessions/{session_id}:
    get:
      tags: [Sessions]
      summary: Get RDP session details
      description: Returns detailed information about a specific RDP session
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: RDP session details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpSessionResponse'
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
          description: RDP session not found
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

    delete:
      tags: [Sessions]
      summary: Terminate RDP session
      description: Terminates an RDP session
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: force
          in: query
          schema:
            type: boolean
            default: false
            description: Force termination
      responses:
        '204':
          description: RDP session terminated successfully
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
          description: RDP session not found
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

  /sessions/{session_id}/connect:
    post:
      tags: [Sessions]
      summary: Connect to RDP session
      description: Establishes connection to an RDP session
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
              $ref: '#/components/schemas/RdpSessionConnectRequest'
      responses:
        '200':
          description: Connection established successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpSessionConnectResponse'
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
          description: RDP session not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '409':
          description: Session already connected
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

  /sessions/{session_id}/disconnect:
    post:
      tags: [Sessions]
      summary: Disconnect from RDP session
      description: Disconnects from an RDP session
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Disconnected successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RdpSessionActionResponse'
        '400':
          description: Invalid request
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
          description: RDP session not found
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

  # Resource Monitoring Endpoints
  /resources/usage:
    get:
      tags: [Resources]
      summary: Get resource usage
      description: Returns current resource usage statistics
      parameters:
        - name: server_id
          in: query
          schema:
            type: string
            format: uuid
        - name: session_id
          in: query
          schema:
            type: string
            format: uuid
        - name: time_range
          in: query
          schema:
            type: string
            enum: [1h, 6h, 24h, 7d]
            default: 1h
      responses:
        '200':
          description: Resource usage retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceUsageResponse'
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /resources/limits:
    get:
      tags: [Resources]
      summary: Get resource limits
      description: Returns current resource limits configuration
      responses:
        '200':
          description: Resource limits retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceLimitsResponse'
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    put:
      tags: [Resources]
      summary: Update resource limits
      description: Updates resource limits configuration
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ResourceLimitsUpdateRequest'
      responses:
        '200':
          description: Resource limits updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceLimitsResponse'
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /resources/alerts:
    get:
      tags: [Resources]
      summary: Get resource alerts
      description: Returns current resource alerts
      parameters:
        - name: severity
          in: query
          schema:
            type: string
            enum: [low, medium, high, critical]
        - name: resolved
          in: query
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: Resource alerts retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceAlertsResponse'
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
    # RDP Server Schemas
    RdpServerResponse:
      type: object
      properties:
        server_id:
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
          enum: [running, stopped, error, maintenance]
        port:
          type: integer
          minimum: 1024
          maximum: 65535
        host:
          type: string
        configuration:
          $ref: '#/components/schemas/RdpServerConfiguration'
        resources:
          $ref: '#/components/schemas/RdpServerResources'
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        last_started_at:
          type: string
          format: date-time
        last_stopped_at:
          type: string
          format: date-time

    RdpServerConfiguration:
      type: object
      properties:
        desktop_environment:
          type: string
          enum: [xfce, gnome, kde, lxde]
          default: xfce
        resolution:
          type: string
          default: "1920x1080"
        color_depth:
          type: integer
          enum: [16, 24, 32]
          default: 24
        audio_enabled:
          type: boolean
          default: true
        clipboard_enabled:
          type: boolean
          default: true
        drive_redirection:
          type: boolean
          default: false
        printer_redirection:
          type: boolean
          default: false

    RdpServerResources:
      type: object
      properties:
        cpu_limit:
          type: number
          minimum: 0.1
          maximum: 8.0
        memory_limit:
          type: integer
          minimum: 512
          maximum: 16384
        disk_limit:
          type: integer
          minimum: 1024
          maximum: 102400
        network_bandwidth:
          type: integer
          minimum: 100
          maximum: 10000

    RdpServerCreateRequest:
      type: object
      required: [name, user_id]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        description:
          type: string
          maxLength: 1000
        user_id:
          type: string
          format: uuid
        configuration:
          $ref: '#/components/schemas/RdpServerConfiguration'
        resources:
          $ref: '#/components/schemas/RdpServerResources'

    RdpServerUpdateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        description:
          type: string
          maxLength: 1000
        configuration:
          $ref: '#/components/schemas/RdpServerConfiguration'
        resources:
          $ref: '#/components/schemas/RdpServerResources'

    RdpServerListResponse:
      type: object
      properties:
        servers:
          type: array
          items:
            $ref: '#/components/schemas/RdpServerResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    RdpServerActionResponse:
      type: object
      properties:
        server_id:
          type: string
          format: uuid
        action:
          type: string
        status:
          type: string
        message:
          type: string
        timestamp:
          type: string
          format: date-time

    RdpServerStatusResponse:
      type: object
      properties:
        server_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [running, stopped, error, maintenance]
        uptime:
          type: integer
          description: Uptime in seconds
        active_sessions:
          type: integer
        resource_usage:
          $ref: '#/components/schemas/ResourceUsage'
        last_health_check:
          type: string
          format: date-time

    # XRDP Schemas
    XrdpConfigResponse:
      type: object
      properties:
        config_version:
          type: string
        global_settings:
          $ref: '#/components/schemas/XrdpGlobalSettings'
        security_settings:
          $ref: '#/components/schemas/XrdpSecuritySettings'
        performance_settings:
          $ref: '#/components/schemas/XrdpPerformanceSettings'
        last_updated:
          type: string
          format: date-time

    XrdpGlobalSettings:
      type: object
      properties:
        port:
          type: integer
          default: 3389
        use_ssl:
          type: boolean
          default: true
        ssl_cert_path:
          type: string
        ssl_key_path:
          type: string
        log_level:
          type: string
          enum: [DEBUG, INFO, WARN, ERROR]
          default: INFO
        max_connections:
          type: integer
          default: 100

    XrdpSecuritySettings:
      type: object
      properties:
        authentication_method:
          type: string
          enum: [password, certificate, both]
          default: password
        session_timeout:
          type: integer
          default: 3600
        idle_timeout:
          type: integer
          default: 1800
        encryption_level:
          type: string
          enum: [low, medium, high]
          default: high

    XrdpPerformanceSettings:
      type: object
      properties:
        compression:
          type: boolean
          default: true
        bitmap_cache:
          type: boolean
          default: true
        glyph_cache:
          type: boolean
          default: true
        max_bitmap_cache_size:
          type: integer
          default: 32000000

    XrdpConfigUpdateRequest:
      type: object
      properties:
        global_settings:
          $ref: '#/components/schemas/XrdpGlobalSettings'
        security_settings:
          $ref: '#/components/schemas/XrdpSecuritySettings'
        performance_settings:
          $ref: '#/components/schemas/XrdpPerformanceSettings'

    XrdpServiceActionResponse:
      type: object
      properties:
        action:
          type: string
        status:
          type: string
        message:
          type: string
        timestamp:
          type: string
          format: date-time

    XrdpServiceStatusResponse:
      type: object
      properties:
        status:
          type: string
          enum: [running, stopped, error, maintenance]
        uptime:
          type: integer
          description: Uptime in seconds
        active_connections:
          type: integer
        last_health_check:
          type: string
          format: date-time
        version:
          type: string

    # Session Schemas
    RdpSessionResponse:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        server_id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [active, disconnected, terminated]
        connection_info:
          $ref: '#/components/schemas/RdpSessionConnectionInfo'
        created_at:
          type: string
          format: date-time
        connected_at:
          type: string
          format: date-time
        last_activity:
          type: string
          format: date-time
        terminated_at:
          type: string
          format: date-time

    RdpSessionConnectionInfo:
      type: object
      properties:
        client_ip:
          type: string
        client_port:
          type: integer
        server_ip:
          type: string
        server_port:
          type: integer
        protocol_version:
          type: string
        encryption_level:
          type: string

    RdpSessionCreateRequest:
      type: object
      required: [server_id, user_id]
      properties:
        server_id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        client_info:
          $ref: '#/components/schemas/RdpClientInfo'

    RdpClientInfo:
      type: object
      properties:
        client_name:
          type: string
        client_version:
          type: string
        client_ip:
          type: string
        resolution:
          type: string
        color_depth:
          type: integer

    RdpSessionListResponse:
      type: object
      properties:
        sessions:
          type: array
          items:
            $ref: '#/components/schemas/RdpSessionResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    RdpSessionConnectRequest:
      type: object
      required: [client_info]
      properties:
        client_info:
          $ref: '#/components/schemas/RdpClientInfo'

    RdpSessionConnectResponse:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        connection_info:
          $ref: '#/components/schemas/RdpSessionConnectionInfo'
        access_token:
          type: string
          description: Token for RDP connection
        expires_at:
          type: string
          format: date-time

    RdpSessionActionResponse:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        action:
          type: string
        status:
          type: string
        message:
          type: string
        timestamp:
          type: string
          format: date-time

    # Resource Schemas
    ResourceUsageResponse:
      type: object
      properties:
        timestamp:
          type: string
          format: date-time
        server_usage:
          $ref: '#/components/schemas/ResourceUsage'
        session_usage:
          type: array
          items:
            $ref: '#/components/schemas/SessionResourceUsage'
        system_usage:
          $ref: '#/components/schemas/SystemResourceUsage'

    ResourceUsage:
      type: object
      properties:
        cpu_percent:
          type: number
          minimum: 0
          maximum: 100
        memory_percent:
          type: number
          minimum: 0
          maximum: 100
        memory_used:
          type: integer
          description: Memory used in MB
        memory_total:
          type: integer
          description: Total memory in MB
        disk_usage_percent:
          type: number
          minimum: 0
          maximum: 100
        disk_used:
          type: integer
          description: Disk used in MB
        disk_total:
          type: integer
          description: Total disk in MB
        network_in:
          type: integer
          description: Network input in KB/s
        network_out:
          type: integer
          description: Network output in KB/s

    SessionResourceUsage:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        cpu_percent:
          type: number
          minimum: 0
          maximum: 100
        memory_percent:
          type: number
          minimum: 0
          maximum: 100
        network_in:
          type: integer
          description: Network input in KB/s
        network_out:
          type: integer
          description: Network output in KB/s

    SystemResourceUsage:
      type: object
      properties:
        total_cpu_percent:
          type: number
          minimum: 0
          maximum: 100
        total_memory_percent:
          type: number
          minimum: 0
          maximum: 100
        total_disk_percent:
          type: number
          minimum: 0
          maximum: 100
        active_sessions:
          type: integer
        total_connections:
          type: integer

    ResourceLimitsResponse:
      type: object
      properties:
        global_limits:
          $ref: '#/components/schemas/GlobalResourceLimits'
        server_limits:
          $ref: '#/components/schemas/ServerResourceLimits'
        session_limits:
          $ref: '#/components/schemas/SessionResourceLimits'
        last_updated:
          type: string
          format: date-time

    GlobalResourceLimits:
      type: object
      properties:
        max_concurrent_servers:
          type: integer
          default: 50
        max_concurrent_sessions:
          type: integer
          default: 100
        max_total_cpu_percent:
          type: number
          default: 80
        max_total_memory_percent:
          type: number
          default: 80
        max_total_disk_percent:
          type: number
          default: 90

    ServerResourceLimits:
      type: object
      properties:
        max_cpu_percent:
          type: number
          default: 80
        max_memory_mb:
          type: integer
          default: 4096
        max_disk_mb:
          type: integer
          default: 20480
        max_network_bandwidth:
          type: integer
          default: 1000

    SessionResourceLimits:
      type: object
      properties:
        max_cpu_percent:
          type: number
          default: 50
        max_memory_mb:
          type: integer
          default: 2048
        max_network_bandwidth:
          type: integer
          default: 500
        max_session_duration:
          type: integer
          default: 3600

    ResourceLimitsUpdateRequest:
      type: object
      properties:
        global_limits:
          $ref: '#/components/schemas/GlobalResourceLimits'
        server_limits:
          $ref: '#/components/schemas/ServerResourceLimits'
        session_limits:
          $ref: '#/components/schemas/SessionResourceLimits'

    ResourceAlertsResponse:
      type: object
      properties:
        alerts:
          type: array
          items:
            $ref: '#/components/schemas/ResourceAlert'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    ResourceAlert:
      type: object
      properties:
        alert_id:
          type: string
          format: uuid
        severity:
          type: string
          enum: [low, medium, high, critical]
        resource_type:
          type: string
          enum: [cpu, memory, disk, network]
        resource_id:
          type: string
        threshold:
          type: number
        current_value:
          type: number
        message:
          type: string
        created_at:
          type: string
          format: date-time
        resolved_at:
          type: string
          format: date-time
        resolved:
          type: boolean

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
              example: "LUCID_ERR_2001"
            message:
              type: string
              example: "RDP server not found"
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
              example: "rdp-server-manager"
            version:
              type: string
              example: "v1"

tags:
  - name: RDP Servers
    description: RDP server instance management
  - name: XRDP Integration
    description: XRDP service control and configuration
  - name: Sessions
    description: RDP session management
  - name: Resources
    description: Resource monitoring and management
```

## Rate Limiting Specifications

### RDP Services-Specific Rate Limiting

```yaml
rate_limits:
  rdp_server_operations:
    requests_per_minute: 100
    burst_size: 200
    endpoints:
      - "/api/v1/rdp/servers/*"
  
  xrdp_operations:
    requests_per_minute: 50
    burst_size: 100
    endpoints:
      - "/api/v1/xrdp/*"
  
  session_operations:
    requests_per_minute: 200
    burst_size: 400
    endpoints:
      - "/api/v1/sessions/*"
  
  resource_monitoring:
    requests_per_minute: 300
    burst_size: 600
    endpoints:
      - "/api/v1/resources/*"
```

## Error Code Registry

### RDP Services-Specific Error Codes

```yaml
error_codes:
  # RDP Server Errors (LUCID_ERR_20XX)
  "LUCID_ERR_2001": "RDP server not found"
  "LUCID_ERR_2002": "RDP server creation failed"
  "LUCID_ERR_2003": "RDP server start failed"
  "LUCID_ERR_2004": "RDP server stop failed"
  "LUCID_ERR_2005": "RDP server restart failed"
  "LUCID_ERR_2006": "RDP server configuration invalid"
  "LUCID_ERR_2007": "RDP server port allocation failed"
  "LUCID_ERR_2008": "RDP server resource limit exceeded"
  
  # XRDP Errors (LUCID_ERR_21XX)
  "LUCID_ERR_2101": "XRDP service not available"
  "LUCID_ERR_2102": "XRDP configuration invalid"
  "LUCID_ERR_2103": "XRDP service start failed"
  "LUCID_ERR_2104": "XRDP service stop failed"
  "LUCID_ERR_2105": "XRDP service restart failed"
  "LUCID_ERR_2106": "XRDP SSL configuration error"
  
  # Session Errors (LUCID_ERR_22XX)
  "LUCID_ERR_2201": "RDP session not found"
  "LUCID_ERR_2202": "RDP session creation failed"
  "LUCID_ERR_2203": "RDP session connection failed"
  "LUCID_ERR_2204": "RDP session termination failed"
  "LUCID_ERR_2205": "RDP session already connected"
  "LUCID_ERR_2206": "RDP session timeout"
  "LUCID_ERR_2207": "RDP session authentication failed"
  
  # Resource Errors (LUCID_ERR_23XX)
  "LUCID_ERR_2301": "Resource limit exceeded"
  "LUCID_ERR_2302": "Resource monitoring failed"
  "LUCID_ERR_2303": "Resource allocation failed"
  "LUCID_ERR_2304": "Resource cleanup failed"
  "LUCID_ERR_2305": "Resource alert creation failed"
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
