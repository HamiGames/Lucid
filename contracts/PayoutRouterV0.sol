// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title PayoutRouterV0
 * @dev Primary payout router contract for non-KYC payouts
 * @notice This contract handles USDT-TRC20 payouts as specified in SPEC-1B-v2-DISTROLESS.md
 *         TRON is used EXCLUSIVELY as a payment rail, NOT for blockchain consensus
 */
contract PayoutRouterV0 {
    struct PayoutRequest {
        address recipient;
        uint256 amount;
        bytes32 sessionId;
        uint256 timestamp;
        bool processed;
        bytes32 txHash;
    }
    
    // Events
    event PayoutRequested(bytes32 indexed payoutId, address recipient, uint256 amount, bytes32 sessionId);
    event PayoutProcessed(bytes32 indexed payoutId, bytes32 txHash);
    event PayoutFailed(bytes32 indexed payoutId, string reason);
    
    // State variables
    mapping(bytes32 => PayoutRequest) public payouts;
    mapping(bytes32 => bool) public processedPayouts;
    
    address public admin;
    address public tronService;
    uint256 public minPayoutAmount = 10 * 10**6; // $10 USDT (6 decimals)
    uint256 public maxPayoutAmount = 10000 * 10**6; // $10,000 USDT (6 decimals)
    
    modifier onlyAuthorized() {
        require(msg.sender == admin || msg.sender == tronService, "Unauthorized");
        _;
    }
    
    constructor(address _tronService) {
        admin = msg.sender;
        tronService = _tronService;
    }
    
    /**
     * @dev Request a payout to be processed via TRON network
     * @param recipient TRON address to receive USDT
     * @param amount Amount in USDT (6 decimals)
     * @param sessionId Associated session ID for audit trail
     * @return payoutId Unique payout identifier
     */
    function requestPayout(
        address recipient,
        uint256 amount,
        bytes32 sessionId
    ) external onlyAuthorized returns (bytes32 payoutId) {
        require(recipient != address(0), "Invalid recipient");
        require(amount >= minPayoutAmount, "Amount below minimum");
        require(amount <= maxPayoutAmount, "Amount above maximum");
        
        payoutId = keccak256(abi.encodePacked(recipient, amount, sessionId, block.timestamp));
        require(!processedPayouts[payoutId], "Payout already requested");
        
        payouts[payoutId] = PayoutRequest({
            recipient: recipient,
            amount: amount,
            sessionId: sessionId,
            timestamp: block.timestamp,
            processed: false,
            txHash: bytes32(0)
        });
        
        processedPayouts[payoutId] = true;
        
        emit PayoutRequested(payoutId, recipient, amount, sessionId);
        
        return payoutId;
    }
    
    /**
     * @dev Mark payout as processed with TRON transaction hash
     * @param payoutId Payout identifier
     * @param txHash TRON transaction hash
     */
    function markPayoutProcessed(bytes32 payoutId, bytes32 txHash) external onlyAuthorized {
        require(processedPayouts[payoutId], "Payout not found");
        require(!payouts[payoutId].processed, "Payout already processed");
        require(txHash != bytes32(0), "Invalid transaction hash");
        
        payouts[payoutId].processed = true;
        payouts[payoutId].txHash = txHash;
        
        emit PayoutProcessed(payoutId, txHash);
    }
    
    /**
     * @dev Mark payout as failed
     * @param payoutId Payout identifier
     * @param reason Failure reason
     */
    function markPayoutFailed(bytes32 payoutId, string calldata reason) external onlyAuthorized {
        require(processedPayouts[payoutId], "Payout not found");
        require(!payouts[payoutId].processed, "Payout already processed");
        
        // Mark as processed but with zero tx hash to indicate failure
        payouts[payoutId].processed = true;
        
        emit PayoutFailed(payoutId, reason);
    }
    
    /**
     * @dev Get payout details
     * @param payoutId Payout identifier
     * @return payout Payout request details
     */
    function getPayout(bytes32 payoutId) external view returns (PayoutRequest memory payout) {
        require(processedPayouts[payoutId], "Payout not found");
        return payouts[payoutId];
    }
    
    /**
     * @dev Update minimum payout amount
     * @param newMinAmount New minimum amount in USDT (6 decimals)
     */
    function updateMinPayoutAmount(uint256 newMinAmount) external {
        require(msg.sender == admin, "Only admin");
        require(newMinAmount > 0, "Invalid amount");
        minPayoutAmount = newMinAmount;
    }
    
    /**
     * @dev Update maximum payout amount
     * @param newMaxAmount New maximum amount in USDT (6 decimals)
     */
    function updateMaxPayoutAmount(uint256 newMaxAmount) external {
        require(msg.sender == admin, "Only admin");
        require(newMaxAmount > minPayoutAmount, "Invalid amount");
        maxPayoutAmount = newMaxAmount;
    }
    
    /**
     * @dev Update TRON service address
     * @param newTronService New TRON service address
     */
    function updateTronService(address newTronService) external {
        require(msg.sender == admin, "Only admin");
        require(newTronService != address(0), "Invalid address");
        tronService = newTronService;
    }
    
    /**
     * @dev Emergency pause function
     * @param paused Pause state
     */
    function setPaused(bool paused) external {
        require(msg.sender == admin, "Only admin");
        // Implementation depends on Pausable contract if needed
    }
}
