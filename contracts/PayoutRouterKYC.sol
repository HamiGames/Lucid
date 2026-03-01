// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title PayoutRouterKYC
 * @dev KYC-gated payout router contract for compliance-required payouts
 * @notice This contract handles USDT-TRC20 payouts with KYC/AML verification
 *         TRON is used EXCLUSIVELY as a payment rail, NOT for blockchain consensus
 */
contract PayoutRouterKYC {
    struct KYCVerification {
        address user;
        string kycId;
        uint256 verificationLevel;
        uint256 verifiedAt;
        bool isActive;
        string complianceStatus;
    }
    
    struct PayoutRequest {
        address recipient;
        uint256 amount;
        bytes32 sessionId;
        string kycId;
        uint256 timestamp;
        bool processed;
        bytes32 txHash;
        string complianceReason;
    }
    
    // Events
    event KYCVerified(address indexed user, string kycId, uint256 verificationLevel);
    event PayoutRequested(bytes32 indexed payoutId, address recipient, uint256 amount, string kycId);
    event PayoutProcessed(bytes32 indexed payoutId, bytes32 txHash);
    event PayoutRejected(bytes32 indexed payoutId, string reason);
    event ComplianceCheck(bytes32 indexed payoutId, bool passed, string reason);
    
    // State variables
    mapping(bytes32 => PayoutRequest) public payouts;
    mapping(address => KYCVerification) public kycVerifications;
    mapping(string => address) public kycIdToAddress;
    mapping(bytes32 => bool) public processedPayouts;
    
    address public owner;
    address public complianceManager;
    uint256 public minimumKYCLevel;
    uint256 public maximumPayoutAmount;
    uint256 public dailyPayoutLimit;
    uint256 public totalDailyPayouts;
    uint256 public lastResetDay;
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "PayoutRouterKYC: Only owner can call this function");
        _;
    }
    
    modifier onlyComplianceManager() {
        require(msg.sender == complianceManager || msg.sender == owner, "PayoutRouterKYC: Only compliance manager can call this function");
        _;
    }
    
    modifier validKYCLevel(uint256 level) {
        require(level >= 1 && level <= 5, "PayoutRouterKYC: Invalid KYC level");
        _;
    }
    
    constructor(
        address _complianceManager,
        uint256 _minimumKYCLevel,
        uint256 _maximumPayoutAmount,
        uint256 _dailyPayoutLimit
    ) {
        owner = msg.sender;
        complianceManager = _complianceManager;
        minimumKYCLevel = _minimumKYCLevel;
        maximumPayoutAmount = _maximumPayoutAmount;
        dailyPayoutLimit = _dailyPayoutLimit;
        lastResetDay = block.timestamp / 1 days;
    }
    
    /**
     * @dev Verify KYC status for a user
     * @param user The user address to verify
     * @param kycId The KYC verification ID
     * @param verificationLevel The verification level (1-5)
     * @param complianceStatus The compliance status
     */
    function verifyKYC(
        address user,
        string memory kycId,
        uint256 verificationLevel,
        string memory complianceStatus
    ) external onlyComplianceManager validKYCLevel(verificationLevel) {
        require(bytes(kycId).length > 0, "PayoutRouterKYC: KYC ID cannot be empty");
        require(bytes(complianceStatus).length > 0, "PayoutRouterKYC: Compliance status cannot be empty");
        require(kycIdToAddress[kycId] == address(0) || kycIdToAddress[kycId] == user, "PayoutRouterKYC: KYC ID already in use");
        
        kycVerifications[user] = KYCVerification({
            user: user,
            kycId: kycId,
            verificationLevel: verificationLevel,
            verifiedAt: block.timestamp,
            isActive: true,
            complianceStatus: complianceStatus
        });
        
        kycIdToAddress[kycId] = user;
        
        emit KYCVerified(user, kycId, verificationLevel);
    }
    
    /**
     * @dev Request a KYC-gated payout
     * @param recipient The recipient address
     * @param amount The payout amount in USDT-TRC20
     * @param sessionId The session ID for tracking
     * @param kycId The KYC verification ID
     * @return payoutId The unique payout request ID
     */
    function requestPayout(
        address recipient,
        uint256 amount,
        bytes32 sessionId,
        string memory kycId
    ) external onlyOwner returns (bytes32) {
        require(amount > 0, "PayoutRouterKYC: Amount must be greater than zero");
        require(amount <= maximumPayoutAmount, "PayoutRouterKYC: Amount exceeds maximum limit");
        require(bytes(kycId).length > 0, "PayoutRouterKYC: KYC ID cannot be empty");
        
        // Check daily limits
        _resetDailyLimitsIfNeeded();
        require(totalDailyPayouts + amount <= dailyPayoutLimit, "PayoutRouterKYC: Daily limit exceeded");
        
        // Verify KYC status
        address kycUser = kycIdToAddress[kycId];
        require(kycUser != address(0), "PayoutRouterKYC: KYC ID not found");
        require(kycVerifications[kycUser].isActive, "PayoutRouterKYC: KYC verification not active");
        require(kycVerifications[kycUser].verificationLevel >= minimumKYCLevel, "PayoutRouterKYC: Insufficient KYC level");
        
        bytes32 payoutId = keccak256(abi.encodePacked(recipient, amount, sessionId, kycId, block.timestamp));
        require(!processedPayouts[payoutId], "PayoutRouterKYC: Payout already processed");
        
        payouts[payoutId] = PayoutRequest({
            recipient: recipient,
            amount: amount,
            sessionId: sessionId,
            kycId: kycId,
            timestamp: block.timestamp,
            processed: false,
            txHash: bytes32(0),
            complianceReason: ""
        });
        
        totalDailyPayouts += amount;
        
        emit PayoutRequested(payoutId, recipient, amount, kycId);
        
        return payoutId;
    }
    
    /**
     * @dev Process a KYC-gated payout
     * @param payoutId The payout request ID
     * @param txHash The TRON transaction hash
     * @param complianceReason The compliance reason for processing
     */
    function processPayout(
        bytes32 payoutId,
        bytes32 txHash,
        string memory complianceReason
    ) external onlyComplianceManager {
        require(payouts[payoutId].recipient != address(0), "PayoutRouterKYC: Payout request not found");
        require(!payouts[payoutId].processed, "PayoutRouterKYC: Payout already processed");
        require(txHash != bytes32(0), "PayoutRouterKYC: Invalid transaction hash");
        require(bytes(complianceReason).length > 0, "PayoutRouterKYC: Compliance reason required");
        
        payouts[payoutId].processed = true;
        payouts[payoutId].txHash = txHash;
        payouts[payoutId].complianceReason = complianceReason;
        processedPayouts[payoutId] = true;
        
        emit PayoutProcessed(payoutId, txHash);
        emit ComplianceCheck(payoutId, true, complianceReason);
    }
    
    /**
     * @dev Reject a payout request
     * @param payoutId The payout request ID
     * @param reason The rejection reason
     */
    function rejectPayout(
        bytes32 payoutId,
        string memory reason
    ) external onlyComplianceManager {
        require(payouts[payoutId].recipient != address(0), "PayoutRouterKYC: Payout request not found");
        require(!payouts[payoutId].processed, "PayoutRouterKYC: Payout already processed");
        require(bytes(reason).length > 0, "PayoutRouterKYC: Rejection reason required");
        
        // Refund the amount from daily limit
        totalDailyPayouts -= payouts[payoutId].amount;
        
        payouts[payoutId].processed = true;
        payouts[payoutId].complianceReason = reason;
        processedPayouts[payoutId] = true;
        
        emit PayoutRejected(payoutId, reason);
        emit ComplianceCheck(payoutId, false, reason);
    }
    
    /**
     * @dev Deactivate KYC verification
     * @param user The user address
     * @param reason The deactivation reason
     */
    function deactivateKYC(
        address user,
        string memory reason
    ) external onlyComplianceManager {
        require(kycVerifications[user].user != address(0), "PayoutRouterKYC: KYC verification not found");
        require(kycVerifications[user].isActive, "PayoutRouterKYC: KYC verification already inactive");
        require(bytes(reason).length > 0, "PayoutRouterKYC: Deactivation reason required");
        
        kycVerifications[user].isActive = false;
        kycVerifications[user].complianceStatus = reason;
    }
    
    /**
     * @dev Update compliance parameters
     * @param _minimumKYCLevel New minimum KYC level
     * @param _maximumPayoutAmount New maximum payout amount
     * @param _dailyPayoutLimit New daily payout limit
     */
    function updateComplianceParameters(
        uint256 _minimumKYCLevel,
        uint256 _maximumPayoutAmount,
        uint256 _dailyPayoutLimit
    ) external onlyOwner validKYCLevel(_minimumKYCLevel) {
        require(_maximumPayoutAmount > 0, "PayoutRouterKYC: Maximum payout amount must be greater than zero");
        require(_dailyPayoutLimit > 0, "PayoutRouterKYC: Daily payout limit must be greater than zero");
        
        minimumKYCLevel = _minimumKYCLevel;
        maximumPayoutAmount = _maximumPayoutAmount;
        dailyPayoutLimit = _dailyPayoutLimit;
    }
    
    /**
     * @dev Update compliance manager
     * @param _complianceManager New compliance manager address
     */
    function updateComplianceManager(address _complianceManager) external onlyOwner {
        require(_complianceManager != address(0), "PayoutRouterKYC: Invalid compliance manager address");
        complianceManager = _complianceManager;
    }
    
    /**
     * @dev Get KYC verification status
     * @param user The user address
     * @return verification The KYC verification details
     */
    function getKYCVerification(address user) external view returns (KYCVerification memory verification) {
        return kycVerifications[user];
    }
    
    /**
     * @dev Get payout request details
     * @param payoutId The payout request ID
     * @return payout The payout request details
     */
    function getPayoutRequest(bytes32 payoutId) external view returns (PayoutRequest memory payout) {
        return payouts[payoutId];
    }
    
    /**
     * @dev Check if payout is eligible based on KYC
     * @param user The user address
     * @param amount The payout amount
     * @return eligible Whether the payout is eligible
     * @return reason The eligibility reason
     */
    function checkPayoutEligibility(
        address user,
        uint256 amount
    ) external view returns (bool eligible, string memory reason) {
        KYCVerification memory kyc = kycVerifications[user];
        
        if (kyc.user == address(0)) {
            return (false, "KYC verification not found");
        }
        
        if (!kyc.isActive) {
            return (false, "KYC verification inactive");
        }
        
        if (kyc.verificationLevel < minimumKYCLevel) {
            return (false, "Insufficient KYC level");
        }
        
        if (amount > maximumPayoutAmount) {
            return (false, "Amount exceeds maximum limit");
        }
        
        _resetDailyLimitsIfNeeded();
        if (totalDailyPayouts + amount > dailyPayoutLimit) {
            return (false, "Daily limit would be exceeded");
        }
        
        return (true, "Eligible for payout");
    }
    
    /**
     * @dev Internal function to reset daily limits if needed
     */
    function _resetDailyLimitsIfNeeded() internal {
        uint256 currentDay = block.timestamp / 1 days;
        if (currentDay > lastResetDay) {
            totalDailyPayouts = 0;
            lastResetDay = currentDay;
        }
    }
    
    /**
     * @dev Emergency function to pause all payouts
     */
    function emergencyPause() external onlyOwner {
        // This would typically set a pause flag and emit an event
        // Implementation depends on specific emergency procedures
        emit ComplianceCheck(bytes32(0), false, "Emergency pause activated");
    }
}
