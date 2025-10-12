# TRON Payment Cluster - API Specification

## OpenAPI 3.0 Specification

```yaml
openapi: 3.0.3
info:
  title: Lucid TRON Payment System
  description: TRON payment operations for the Lucid system - COMPLETELY ISOLATED from lucid_blocks blockchain
  version: 1.0.0
  contact:
    name: Lucid Development Team
    email: dev@lucid-blockchain.org
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://tron-payment.lucid-blockchain.org/api/v1
    description: Production TRON payment server
  - url: https://tron-payment-dev.lucid-blockchain.org/api/v1
    description: Development TRON payment server
  - url: http://localhost:8085/api/v1
    description: Local development server

security:
  - BearerAuth: []

paths:
  # TRON Network Endpoints
  /tron/network/info:
    get:
      tags: [TRON Network]
      summary: Get TRON network information
      description: Returns comprehensive information about the TRON network
      responses:
        '200':
          description: TRON network information retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TronNetworkInfo'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /tron/network/status:
    get:
      tags: [TRON Network]
      summary: Get TRON network status
      description: Returns the current status of the TRON network
      responses:
        '200':
          description: TRON network status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TronNetworkStatus'
        '503':
          description: TRON network unavailable
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /tron/network/height:
    get:
      tags: [TRON Network]
      summary: Get TRON network height
      description: Returns the current block height of the TRON network
      responses:
        '200':
          description: TRON network height retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TronNetworkHeight'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /tron/network/fees:
    get:
      tags: [TRON Network]
      summary: Get TRON network fees
      description: Returns current TRON network transaction fees
      responses:
        '200':
          description: TRON network fees retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TronNetworkFees'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Wallet Management Endpoints
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
        - name: currency
          in: query
          schema:
            type: string
            enum: [TRX, USDT]
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    post:
      tags: [Wallets]
      summary: Create new wallet
      description: Creates a new TRON wallet for the authenticated user
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
        '500':
          description: Internal server error
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    put:
      tags: [Wallets]
      summary: Update wallet
      description: Updates wallet information
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
              $ref: '#/components/schemas/WalletUpdateRequest'
      responses:
        '200':
          description: Wallet updated successfully
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    delete:
      tags: [Wallets]
      summary: Delete wallet
      description: Deletes a wallet (soft delete)
      parameters:
        - name: wallet_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '204':
          description: Wallet deleted successfully
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /wallets/{wallet_id}/balance:
    get:
      tags: [Wallets]
      summary: Get wallet balance
      description: Returns the balance of a specific wallet
      parameters:
        - name: wallet_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: currency
          in: query
          schema:
            type: string
            enum: [TRX, USDT]
            default: TRX
      responses:
        '200':
          description: Wallet balance retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WalletBalanceResponse'
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /wallets/{wallet_id}/transactions:
    get:
      tags: [Wallets]
      summary: Get wallet transactions
      description: Returns transaction history for a specific wallet
      parameters:
        - name: wallet_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
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
        - name: currency
          in: query
          schema:
            type: string
            enum: [TRX, USDT]
        - name: status
          in: query
          schema:
            type: string
            enum: [pending, confirmed, failed]
      responses:
        '200':
          description: Wallet transactions retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WalletTransactionListResponse'
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
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # USDT Operations Endpoints
  /usdt/transfer:
    post:
      tags: [USDT]
      summary: Transfer USDT
      description: Transfers USDT from one address to another
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UsdtTransferRequest'
      responses:
        '202':
          description: USDT transfer initiated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UsdtTransferResponse'
        '400':
          description: Invalid transfer request
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
          description: Insufficient balance or permissions
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

  /usdt/balance/{address}:
    get:
      tags: [USDT]
      summary: Get USDT balance
      description: Returns the USDT balance for a specific TRON address
      parameters:
        - name: address
          in: path
          required: true
          schema:
            type: string
            pattern: '^T[A-Za-z1-9]{33}$'
            description: TRON address
      responses:
        '200':
          description: USDT balance retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UsdtBalanceResponse'
        '400':
          description: Invalid TRON address
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

  /usdt/transactions/{address}:
    get:
      tags: [USDT]
      summary: Get USDT transactions
      description: Returns USDT transaction history for a specific address
      parameters:
        - name: address
          in: path
          required: true
          schema:
            type: string
            pattern: '^T[A-Za-z1-9]{33}$'
            description: TRON address
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
        - name: start_time
          in: query
          schema:
            type: string
            format: date-time
        - name: end_time
          in: query
          schema:
            type: string
            format: date-time
      responses:
        '200':
          description: USDT transactions retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UsdtTransactionListResponse'
        '400':
          description: Invalid TRON address or parameters
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

  /usdt/approve:
    post:
      tags: [USDT]
      summary: Approve USDT spending
      description: Approves USDT spending for a specific address
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UsdtApproveRequest'
      responses:
        '202':
          description: USDT approval initiated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UsdtApproveResponse'
        '400':
          description: Invalid approval request
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

  /usdt/allowance:
    get:
      tags: [USDT]
      summary: Check USDT allowance
      description: Checks USDT allowance for a specific address
      parameters:
        - name: owner
          in: query
          required: true
          schema:
            type: string
            pattern: '^T[A-Za-z1-9]{33}$'
            description: Owner TRON address
        - name: spender
          in: query
          required: true
          schema:
            type: string
            pattern: '^T[A-Za-z1-9]{33}$'
            description: Spender TRON address
      responses:
        '200':
          description: USDT allowance retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UsdtAllowanceResponse'
        '400':
          description: Invalid TRON addresses
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

  # Payout Operations Endpoints
  /payouts/initiate:
    post:
      tags: [Payouts]
      summary: Initiate payout
      description: Initiates a payout to a TRON address
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PayoutInitiateRequest'
      responses:
        '202':
          description: Payout initiated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PayoutInitiateResponse'
        '400':
          description: Invalid payout request
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

  /payouts/{payout_id}:
    get:
      tags: [Payouts]
      summary: Get payout status
      description: Returns the status of a specific payout
      parameters:
        - name: payout_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Payout status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PayoutStatusResponse'
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
          description: Payout not found
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

  /payouts/batch:
    post:
      tags: [Payouts]
      summary: Process batch payout
      description: Processes multiple payouts in a single batch
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PayoutBatchRequest'
      responses:
        '202':
          description: Batch payout initiated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PayoutBatchResponse'
        '400':
          description: Invalid batch payout request
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

  /payouts/history:
    get:
      tags: [Payouts]
      summary: Get payout history
      description: Returns payout history for the authenticated user
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
            enum: [pending, processing, completed, failed, cancelled]
        - name: currency
          in: query
          schema:
            type: string
            enum: [TRX, USDT]
        - name: start_date
          in: query
          schema:
            type: string
            format: date
        - name: end_date
          in: query
          schema:
            type: string
            format: date
      responses:
        '200':
          description: Payout history retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PayoutHistoryResponse'
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

  /payouts/cancel:
    post:
      tags: [Payouts]
      summary: Cancel payout
      description: Cancels a pending payout
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PayoutCancelRequest'
      responses:
        '200':
          description: Payout cancelled successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PayoutCancelResponse'
        '400':
          description: Invalid cancel request
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
          description: Payout not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '409':
          description: Payout cannot be cancelled
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

  # TRX Staking Endpoints
  /staking/stake:
    post:
      tags: [Staking]
      summary: Stake TRX
      description: Stakes TRX tokens for staking rewards
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/StakingStakeRequest'
      responses:
        '202':
          description: TRX staking initiated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StakingStakeResponse'
        '400':
          description: Invalid staking request
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
          description: Insufficient TRX balance
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

  /staking/unstake:
    post:
      tags: [Staking]
      summary: Unstake TRX
      description: Unstakes TRX tokens from staking
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/StakingUnstakeRequest'
      responses:
        '202':
          description: TRX unstaking initiated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StakingUnstakeResponse'
        '400':
          description: Invalid unstaking request
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
          description: Insufficient staked TRX
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

  /staking/status/{address}:
    get:
      tags: [Staking]
      summary: Get staking status
      description: Returns staking status for a specific TRON address
      parameters:
        - name: address
          in: path
          required: true
          schema:
            type: string
            pattern: '^T[A-Za-z1-9]{33}$'
            description: TRON address
      responses:
        '200':
          description: Staking status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StakingStatusResponse'
        '400':
          description: Invalid TRON address
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

  /staking/rewards/{address}:
    get:
      tags: [Staking]
      summary: Get staking rewards
      description: Returns staking rewards for a specific TRON address
      parameters:
        - name: address
          in: path
          required: true
          schema:
            type: string
            pattern: '^T[A-Za-z1-9]{33}$'
            description: TRON address
        - name: period
          in: query
          schema:
            type: string
            enum: [daily, weekly, monthly, yearly, all]
            default: all
      responses:
        '200':
          description: Staking rewards retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StakingRewardsResponse'
        '400':
          description: Invalid TRON address or period
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

  /staking/withdraw:
    post:
      tags: [Staking]
      summary: Withdraw staking rewards
      description: Withdraws accumulated staking rewards
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/StakingWithdrawRequest'
      responses:
        '202':
          description: Staking rewards withdrawal initiated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StakingWithdrawResponse'
        '400':
          description: Invalid withdrawal request
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
          description: No rewards to withdraw
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

  # Payment Gateway Endpoints
  /payments/process:
    post:
      tags: [Payments]
      summary: Process payment
      description: Processes a payment request
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PaymentProcessRequest'
      responses:
        '202':
          description: Payment processed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaymentProcessResponse'
        '400':
          description: Invalid payment request
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
          description: Payment not authorized
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

  /payments/{payment_id}:
    get:
      tags: [Payments]
      summary: Get payment status
      description: Returns the status of a specific payment
      parameters:
        - name: payment_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Payment status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaymentStatusResponse'
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
          description: Payment not found
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

  /payments/refund:
    post:
      tags: [Payments]
      summary: Process refund
      description: Processes a refund for a completed payment
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PaymentRefundRequest'
      responses:
        '202':
          description: Refund processed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaymentRefundResponse'
        '400':
          description: Invalid refund request
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
          description: Refund not authorized
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Payment not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '409':
          description: Refund not allowed
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

  /payments/reconciliation:
    get:
      tags: [Payments]
      summary: Get payment reconciliation
      description: Returns payment reconciliation data
      parameters:
        - name: date
          in: query
          required: true
          schema:
            type: string
            format: date
        - name: currency
          in: query
          schema:
            type: string
            enum: [TRX, USDT]
        - name: status
          in: query
          schema:
            type: string
            enum: [completed, pending, failed]
      responses:
        '200':
          description: Payment reconciliation retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaymentReconciliationResponse'
        '400':
          description: Invalid parameters
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

  /payments/webhook:
    post:
      tags: [Payments]
      summary: Payment webhook endpoint
      description: Webhook endpoint for payment notifications
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PaymentWebhookRequest'
      responses:
        '200':
          description: Webhook processed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaymentWebhookResponse'
        '400':
          description: Invalid webhook data
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
    # TRON Network Schemas
    TronNetworkInfo:
      type: object
      properties:
        network_name:
          type: string
          example: "TRON Mainnet"
        network_id:
          type: string
          example: "mainnet"
        chain_id:
          type: string
          example: "0x2b6653dc"
        current_height:
          type: integer
          example: 50000000
        block_time:
          type: integer
          example: 3
        total_supply:
          type: string
          example: "100000000000"
        circulating_supply:
          type: string
          example: "99000000000"
        energy_price:
          type: string
          example: "420"
        bandwidth_price:
          type: string
          example: "1000"

    TronNetworkStatus:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, degraded, down]
        current_height:
          type: integer
        sync_percentage:
          type: number
          minimum: 0
          maximum: 100
        last_block_time:
          type: string
          format: date-time
        node_count:
          type: integer
        network_hash_rate:
          type: string

    TronNetworkHeight:
      type: object
      properties:
        height:
          type: integer
          example: 50000000
        timestamp:
          type: string
          format: date-time

    TronNetworkFees:
      type: object
      properties:
        energy_price:
          type: string
          example: "420"
        bandwidth_price:
          type: string
          example: "1000"
        transaction_fee:
          type: string
          example: "1000000"
        smart_contract_fee:
          type: string
          example: "10000000"

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
          pattern: '^T[A-Za-z1-9]{33}$'
        currency:
          type: string
          enum: [TRX, USDT]
        network:
          type: string
          example: "TRON"
        balance:
          type: number
        is_active:
          type: boolean
        hardware_wallet:
          type: boolean
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
          enum: [TRX, USDT]
        hardware_wallet:
          type: boolean
          default: false
        hardware_wallet_path:
          type: string
          maxLength: 200

    WalletUpdateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        is_active:
          type: boolean

    WalletBalanceResponse:
      type: object
      properties:
        wallet_id:
          type: string
          format: uuid
        address:
          type: string
        currency:
          type: string
        balance:
          type: number
        balance_formatted:
          type: string
        last_updated:
          type: string
          format: date-time

    WalletTransactionListResponse:
      type: object
      properties:
        transactions:
          type: array
          items:
            $ref: '#/components/schemas/WalletTransaction'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    WalletTransaction:
      type: object
      properties:
        tx_id:
          type: string
        hash:
          type: string
        type:
          type: string
          enum: [transfer, receive, stake, unstake, reward]
        amount:
          type: number
        currency:
          type: string
        from_address:
          type: string
        to_address:
          type: string
        status:
          type: string
          enum: [pending, confirmed, failed]
        timestamp:
          type: string
          format: date-time
        block_height:
          type: integer
        fee:
          type: number

    WalletListResponse:
      type: object
      properties:
        wallets:
          type: array
          items:
            $ref: '#/components/schemas/WalletResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    # USDT Schemas
    UsdtTransferRequest:
      type: object
      required: [from_address, to_address, amount]
      properties:
        from_address:
          type: string
          pattern: '^T[A-Za-z1-9]{33}$'
        to_address:
          type: string
          pattern: '^T[A-Za-z1-9]{33}$'
        amount:
          type: number
          minimum: 0.000001
        memo:
          type: string
          maxLength: 255
        private_key_encrypted:
          type: string

    UsdtTransferResponse:
      type: object
      properties:
        transfer_id:
          type: string
          format: uuid
        tx_id:
          type: string
        status:
          type: string
          enum: [pending, confirmed, failed]
        amount:
          type: number
        from_address:
          type: string
        to_address:
          type: string
        submitted_at:
          type: string
          format: date-time
        confirmed_at:
          type: string
          format: date-time

    UsdtBalanceResponse:
      type: object
      properties:
        address:
          type: string
        balance:
          type: number
        balance_formatted:
          type: string
        last_updated:
          type: string
          format: date-time

    UsdtTransactionListResponse:
      type: object
      properties:
        transactions:
          type: array
          items:
            $ref: '#/components/schemas/UsdtTransaction'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    UsdtTransaction:
      type: object
      properties:
        tx_id:
          type: string
        hash:
          type: string
        type:
          type: string
          enum: [transfer, receive, approve]
        amount:
          type: number
        from_address:
          type: string
        to_address:
          type: string
        status:
          type: string
          enum: [pending, confirmed, failed]
        timestamp:
          type: string
          format: date-time
        block_height:
          type: integer
        fee:
          type: number

    UsdtApproveRequest:
      type: object
      required: [owner_address, spender_address, amount]
      properties:
        owner_address:
          type: string
          pattern: '^T[A-Za-z1-9]{33}$'
        spender_address:
          type: string
          pattern: '^T[A-Za-z1-9]{33}$'
        amount:
          type: number
          minimum: 0
        private_key_encrypted:
          type: string

    UsdtApproveResponse:
      type: object
      properties:
        approve_id:
          type: string
          format: uuid
        tx_id:
          type: string
        status:
          type: string
          enum: [pending, confirmed, failed]
        amount:
          type: number
        owner_address:
          type: string
        spender_address:
          type: string
        submitted_at:
          type: string
          format: date-time

    UsdtAllowanceResponse:
      type: object
      properties:
        owner_address:
          type: string
        spender_address:
          type: string
        allowance:
          type: number
        allowance_formatted:
          type: string
        last_updated:
          type: string
          format: date-time

    # Payout Schemas
    PayoutInitiateRequest:
      type: object
      required: [recipient_address, amount, currency]
      properties:
        recipient_address:
          type: string
          pattern: '^T[A-Za-z1-9]{33}$'
        amount:
          type: number
          minimum: 0.000001
        currency:
          type: string
          enum: [TRX, USDT]
        memo:
          type: string
          maxLength: 255
        priority:
          type: string
          enum: [low, normal, high]
          default: normal

    PayoutInitiateResponse:
      type: object
      properties:
        payout_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [pending, processing, completed, failed, cancelled]
        amount:
          type: number
        currency:
          type: string
        recipient_address:
          type: string
        estimated_completion:
          type: string
          format: date-time
        submitted_at:
          type: string
          format: date-time

    PayoutStatusResponse:
      type: object
      properties:
        payout_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [pending, processing, completed, failed, cancelled]
        amount:
          type: number
        currency:
          type: string
        recipient_address:
          type: string
        tx_id:
          type: string
        submitted_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
        failure_reason:
          type: string

    PayoutBatchRequest:
      type: object
      required: [payouts]
      properties:
        payouts:
          type: array
          items:
            $ref: '#/components/schemas/PayoutInitiateRequest'
          minItems: 1
          maxItems: 100
        batch_memo:
          type: string
          maxLength: 255

    PayoutBatchResponse:
      type: object
      properties:
        batch_id:
          type: string
          format: uuid
        payout_count:
          type: integer
        successful_count:
          type: integer
        failed_count:
          type: integer
        payout_ids:
          type: array
          items:
            type: string
            format: uuid
        submitted_at:
          type: string
          format: date-time

    PayoutHistoryResponse:
      type: object
      properties:
        payouts:
          type: array
          items:
            $ref: '#/components/schemas/PayoutStatusResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    PayoutCancelRequest:
      type: object
      required: [payout_id]
      properties:
        payout_id:
          type: string
          format: uuid
        reason:
          type: string
          maxLength: 255

    PayoutCancelResponse:
      type: object
      properties:
        payout_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [cancelled, cannot_cancel]
        cancelled_at:
          type: string
          format: date-time
        reason:
          type: string

    # Staking Schemas
    StakingStakeRequest:
      type: object
      required: [wallet_address, amount]
      properties:
        wallet_address:
          type: string
          pattern: '^T[A-Za-z1-9]{33}$'
        amount:
          type: number
          minimum: 1000
        private_key_encrypted:
          type: string

    StakingStakeResponse:
      type: object
      properties:
        stake_id:
          type: string
          format: uuid
        tx_id:
          type: string
        status:
          type: string
          enum: [pending, confirmed, failed]
        amount:
          type: number
        wallet_address:
          type: string
        submitted_at:
          type: string
          format: date-time
        confirmed_at:
          type: string
          format: date-time

    StakingUnstakeRequest:
      type: object
      required: [wallet_address, amount]
      properties:
        wallet_address:
          type: string
          pattern: '^T[A-Za-z1-9]{33}$'
        amount:
          type: number
          minimum: 1
        private_key_encrypted:
          type: string

    StakingUnstakeResponse:
      type: object
      properties:
        unstake_id:
          type: string
          format: uuid
        tx_id:
          type: string
        status:
          type: string
          enum: [pending, confirmed, failed]
        amount:
          type: number
        wallet_address:
          type: string
        submitted_at:
          type: string
          format: date-time
        confirmed_at:
          type: string
          format: date-time

    StakingStatusResponse:
      type: object
      properties:
        address:
          type: string
        total_staked:
          type: number
        total_staked_formatted:
          type: string
        available_for_unstaking:
          type: number
        available_for_unstaking_formatted:
          type: string
        total_rewards:
          type: number
        total_rewards_formatted:
          type: string
        staking_entries:
          type: array
          items:
            $ref: '#/components/schemas/StakingEntry'

    StakingEntry:
      type: object
      properties:
        entry_id:
          type: string
        amount:
          type: number
        staked_at:
          type: string
          format: date-time
        unlock_time:
          type: string
          format: date-time
        is_unlocked:
          type: boolean

    StakingRewardsResponse:
      type: object
      properties:
        address:
          type: string
        period:
          type: string
        total_rewards:
          type: number
        total_rewards_formatted:
          type: string
        reward_entries:
          type: array
          items:
            $ref: '#/components/schemas/RewardEntry'

    RewardEntry:
      type: object
      properties:
        date:
          type: string
          format: date
        amount:
          type: number
        amount_formatted:
          type: string
        type:
          type: string
          enum: [staking, voting, resource]

    StakingWithdrawRequest:
      type: object
      required: [wallet_address]
      properties:
        wallet_address:
          type: string
          pattern: '^T[A-Za-z1-9]{33}$'
        amount:
          type: number
        private_key_encrypted:
          type: string

    StakingWithdrawResponse:
      type: object
      properties:
        withdraw_id:
          type: string
          format: uuid
        tx_id:
          type: string
        status:
          type: string
          enum: [pending, confirmed, failed]
        amount:
          type: number
        wallet_address:
          type: string
        submitted_at:
          type: string
          format: date-time

    # Payment Schemas
    PaymentProcessRequest:
      type: object
      required: [amount, currency, recipient_address]
      properties:
        amount:
          type: number
          minimum: 0.000001
        currency:
          type: string
          enum: [TRX, USDT]
        recipient_address:
          type: string
          pattern: '^T[A-Za-z1-9]{33}$'
        description:
          type: string
          maxLength: 255
        callback_url:
          type: string
          format: uri

    PaymentProcessResponse:
      type: object
      properties:
        payment_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [pending, processing, completed, failed, cancelled]
        amount:
          type: number
        currency:
          type: string
        recipient_address:
          type: string
        tx_id:
          type: string
        submitted_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time

    PaymentStatusResponse:
      type: object
      properties:
        payment_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [pending, processing, completed, failed, cancelled]
        amount:
          type: number
        currency:
          type: string
        recipient_address:
          type: string
        tx_id:
          type: string
        submitted_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
        failure_reason:
          type: string

    PaymentRefundRequest:
      type: object
      required: [payment_id, reason]
      properties:
        payment_id:
          type: string
          format: uuid
        reason:
          type: string
          maxLength: 255
        amount:
          type: number

    PaymentRefundResponse:
      type: object
      properties:
        refund_id:
          type: string
          format: uuid
        payment_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [pending, processing, completed, failed]
        amount:
          type: number
        tx_id:
          type: string
        submitted_at:
          type: string
          format: date-time

    PaymentReconciliationResponse:
      type: object
      properties:
        date:
          type: string
          format: date
        currency:
          type: string
        total_amount:
          type: number
        total_transactions:
          type: integer
        completed_transactions:
          type: integer
        failed_transactions:
          type: integer
        pending_transactions:
          type: integer
        reconciliation_data:
          type: array
          items:
            $ref: '#/components/schemas/ReconciliationEntry'

    ReconciliationEntry:
      type: object
      properties:
        transaction_id:
          type: string
        amount:
          type: number
        status:
          type: string
        timestamp:
          type: string
          format: date-time
        tx_hash:
          type: string

    PaymentWebhookRequest:
      type: object
      properties:
        event_type:
          type: string
          enum: [payment.completed, payment.failed, payout.completed, payout.failed]
        payment_id:
          type: string
          format: uuid
        tx_id:
          type: string
        status:
          type: string
        amount:
          type: number
        currency:
          type: string
        timestamp:
          type: string
          format: date-time
        signature:
          type: string

    PaymentWebhookResponse:
      type: object
      properties:
        received:
          type: boolean
        processed:
          type: boolean
        timestamp:
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
              example: "LUCID_ERR_9001"
            message:
              type: string
              example: "TRON network error"
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
              example: "tron-payment-service"
            version:
              type: string
              example: "v1"

tags:
  - name: TRON Network
    description: TRON network information and status
  - name: Wallets
    description: TRON wallet management operations
  - name: USDT
    description: USDT-TRC20 token operations
  - name: Payouts
    description: Payout processing and management
  - name: Staking
    description: TRX staking operations and rewards
  - name: Payments
    description: Payment gateway operations
```

## Rate Limiting Specifications

### TRON Payment-Specific Rate Limiting

```yaml
rate_limits:
  tron_network_queries:
    requests_per_minute: 1000
    burst_size: 2000
    endpoints:
      - "/api/v1/tron/network/*"
  
  wallet_operations:
    requests_per_minute: 500
    burst_size: 1000
    endpoints:
      - "/api/v1/wallets/*"
  
  usdt_operations:
    requests_per_minute: 200
    burst_size: 400
    endpoints:
      - "/api/v1/usdt/*"
  
  payout_operations:
    requests_per_minute: 100
    burst_size: 200
    endpoints:
      - "/api/v1/payouts/*"
  
  staking_operations:
    requests_per_minute: 50
    burst_size: 100
    endpoints:
      - "/api/v1/staking/*"
  
  payment_operations:
    requests_per_minute: 300
    burst_size: 600
    endpoints:
      - "/api/v1/payments/*"
```

## Error Code Registry

### TRON Payment-Specific Error Codes

```yaml
error_codes:
  # TRON Network Errors (LUCID_ERR_9XXX)
  "LUCID_ERR_9001": "TRON network error"
  "LUCID_ERR_9002": "TRON node connection failed"
  "LUCID_ERR_9003": "TRON transaction broadcast failed"
  "LUCID_ERR_9004": "TRON block synchronization failed"
  "LUCID_ERR_9005": "TRON network fees unavailable"
  
  # Wallet Errors (LUCID_ERR_10XX)
  "LUCID_ERR_1001": "Wallet not found"
  "LUCID_ERR_1002": "Invalid wallet address"
  "LUCID_ERR_1003": "Wallet balance insufficient"
  "LUCID_ERR_1004": "Wallet creation failed"
  "LUCID_ERR_1005": "Hardware wallet connection failed"
  
  # USDT Errors (LUCID_ERR_11XX)
  "LUCID_ERR_1101": "USDT transfer failed"
  "LUCID_ERR_1102": "USDT balance insufficient"
  "LUCID_ERR_1103": "USDT approval failed"
  "LUCID_ERR_1104": "USDT allowance insufficient"
  "LUCID_ERR_1105": "USDT contract error"
  
  # Payout Errors (LUCID_ERR_12XX)
  "LUCID_ERR_1201": "Payout not found"
  "LUCID_ERR_1202": "Payout processing failed"
  "LUCID_ERR_1203": "Payout cannot be cancelled"
  "LUCID_ERR_1204": "Batch payout failed"
  "LUCID_ERR_1205": "Payout router error"
  
  # Staking Errors (LUCID_ERR_13XX)
  "LUCID_ERR_1301": "Staking failed"
  "LUCID_ERR_1302": "Insufficient TRX for staking"
  "LUCID_ERR_1303": "Unstaking failed"
  "LUCID_ERR_1304": "Staking rewards unavailable"
  "LUCID_ERR_1305": "Staking withdrawal failed"
  
  # Payment Errors (LUCID_ERR_14XX)
  "LUCID_ERR_1401": "Payment processing failed"
  "LUCID_ERR_1402": "Payment not found"
  "LUCID_ERR_1403": "Payment refund failed"
  "LUCID_ERR_1404": "Payment reconciliation failed"
  "LUCID_ERR_1405": "Payment webhook failed"
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
