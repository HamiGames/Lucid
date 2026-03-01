// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ParamRegistry
 * @dev Bounded parameter registry for governance and system configuration
 * @notice This contract manages system parameters with bounds checking and governance integration
 */
contract ParamRegistry {
    struct Parameter {
        string name;
        uint256 value;
        uint256 minValue;
        uint256 maxValue;
        uint256 lastUpdated;
        address updatedBy;
        bool isActive;
        string description;
    }
    
    struct ParameterUpdate {
        string name;
        uint256 oldValue;
        uint256 newValue;
        uint256 timestamp;
        address updatedBy;
        string reason;
    }
    
    // Events
    event ParameterUpdated(
        string indexed name,
        uint256 oldValue,
        uint256 newValue,
        address indexed updatedBy,
        string reason
    );
    event ParameterBoundsUpdated(
        string indexed name,
        uint256 oldMinValue,
        uint256 newMinValue,
        uint256 oldMaxValue,
        uint256 newMaxValue,
        address indexed updatedBy
    );
    event ParameterDeactivated(string indexed name, address indexed updatedBy, string reason);
    event ParameterActivated(string indexed name, address indexed updatedBy);
    
    // State variables
    mapping(string => Parameter) public parameters;
    mapping(string => ParameterUpdate[]) public parameterHistory;
    mapping(address => bool) public authorizedUpdaters;
    mapping(string => bool) public parameterExists;
    
    address public owner;
    address public governor;
    uint256 public constant MAX_PARAMETER_NAME_LENGTH = 64;
    uint256 public constant MAX_DESCRIPTION_LENGTH = 256;
    uint256 public constant MAX_HISTORY_ENTRIES = 100;
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "ParamRegistry: Only owner can call this function");
        _;
    }
    
    modifier onlyGovernor() {
        require(msg.sender == governor || msg.sender == owner, "ParamRegistry: Only governor can call this function");
        _;
    }
    
    modifier onlyAuthorized() {
        require(
            msg.sender == owner || 
            msg.sender == governor || 
            authorizedUpdaters[msg.sender],
            "ParamRegistry: Only authorized addresses can call this function"
        );
        _;
    }
    
    modifier validParameterName(string memory name) {
        require(bytes(name).length > 0, "ParamRegistry: Parameter name cannot be empty");
        require(bytes(name).length <= MAX_PARAMETER_NAME_LENGTH, "ParamRegistry: Parameter name too long");
        _;
    }
    
    modifier validBounds(uint256 minValue, uint256 maxValue) {
        require(minValue <= maxValue, "ParamRegistry: Min value must be less than or equal to max value");
        _;
    }
    
    constructor(address _governor) {
        owner = msg.sender;
        governor = _governor;
        
        // Initialize default system parameters
        _initializeDefaultParameters();
    }
    
    /**
     * @dev Initialize default system parameters
     */
    function _initializeDefaultParameters() internal {
        // Consensus parameters
        _setParameter(
            "SLOT_DURATION_SEC",
            120,
            60,
            300,
            "Slot duration in seconds for PoOT consensus",
            "System initialization"
        );
        
        _setParameter(
            "SLOT_TIMEOUT_MS",
            5000,
            1000,
            10000,
            "Leader timeout in milliseconds",
            "System initialization"
        );
        
        _setParameter(
            "COOLDOWN_SLOTS",
            16,
            8,
            32,
            "Cooldown period in slots for leader selection",
            "System initialization"
        );
        
        _setParameter(
            "LEADER_WINDOW_DAYS",
            7,
            1,
            30,
            "PoOT window duration in days",
            "System initialization"
        );
        
        _setParameter(
            "D_MIN",
            20,
            10,
            50,
            "Minimum density threshold (percentage)",
            "System initialization"
        );
        
        _setParameter(
            "BASE_MB_PER_SESSION",
            5,
            1,
            20,
            "Base MB per session for work credits calculation",
            "System initialization"
        );
        
        // Payment parameters
        _setParameter(
            "MAX_PAYOUT_AMOUNT",
            1000000000000000000000, // 1000 USDT (18 decimals)
            1000000000000000000,    // 1 USDT
            10000000000000000000000, // 10000 USDT
            "Maximum payout amount in USDT",
            "System initialization"
        );
        
        _setParameter(
            "DAILY_PAYOUT_LIMIT",
            10000000000000000000000, // 10000 USDT
            1000000000000000000000,  // 1000 USDT
            100000000000000000000000, // 100000 USDT
            "Daily payout limit in USDT",
            "System initialization"
        );
        
        _setParameter(
            "MIN_KYC_LEVEL",
            2,
            1,
            5,
            "Minimum KYC level for payouts",
            "System initialization"
        );
        
        // Session parameters
        _setParameter(
            "MAX_SESSION_DURATION",
            3600, // 1 hour
            300,  // 5 minutes
            86400, // 24 hours
            "Maximum session duration in seconds",
            "System initialization"
        );
        
        _setParameter(
            "MAX_CHUNK_SIZE",
            1048576, // 1MB
            65536,   // 64KB
            10485760, // 10MB
            "Maximum chunk size in bytes",
            "System initialization"
        );
        
        // Network parameters
        _setParameter(
            "MAX_PEERS",
            50,
            10,
            200,
            "Maximum number of peers",
            "System initialization"
        );
        
        _setParameter(
            "HEARTBEAT_INTERVAL",
            30,
            10,
            120,
            "Heartbeat interval in seconds",
            "System initialization"
        );
    }
    
    /**
     * @dev Set a parameter with bounds checking
     * @param name The parameter name
     * @param value The parameter value
     * @param minValue The minimum allowed value
     * @param maxValue The maximum allowed value
     * @param description The parameter description
     * @param reason The reason for the update
     */
    function setParameter(
        string memory name,
        uint256 value,
        uint256 minValue,
        uint256 maxValue,
        string memory description,
        string memory reason
    ) external onlyAuthorized validParameterName(name) validBounds(minValue, maxValue) {
        require(value >= minValue && value <= maxValue, "ParamRegistry: Value out of bounds");
        require(bytes(description).length <= MAX_DESCRIPTION_LENGTH, "ParamRegistry: Description too long");
        require(bytes(reason).length > 0, "ParamRegistry: Reason required");
        
        _setParameter(name, value, minValue, maxValue, description, reason);
    }
    
    /**
     * @dev Internal function to set parameter
     */
    function _setParameter(
        string memory name,
        uint256 value,
        uint256 minValue,
        uint256 maxValue,
        string memory description,
        string memory reason
    ) internal {
        uint256 oldValue = 0;
        bool isUpdate = parameterExists[name];
        
        if (isUpdate) {
            oldValue = parameters[name].value;
        }
        
        parameters[name] = Parameter({
            name: name,
            value: value,
            minValue: minValue,
            maxValue: maxValue,
            lastUpdated: block.timestamp,
            updatedBy: msg.sender,
            isActive: true,
            description: description
        });
        
        parameterExists[name] = true;
        
        // Add to history
        _addToHistory(name, oldValue, value, reason);
        
        emit ParameterUpdated(name, oldValue, value, msg.sender, reason);
    }
    
    /**
     * @dev Update parameter bounds
     * @param name The parameter name
     * @param newMinValue The new minimum value
     * @param newMaxValue The new maximum value
     */
    function updateParameterBounds(
        string memory name,
        uint256 newMinValue,
        uint256 newMaxValue
    ) external onlyGovernor validParameterName(name) validBounds(newMinValue, newMaxValue) {
        require(parameterExists[name], "ParamRegistry: Parameter does not exist");
        
        Parameter storage param = parameters[name];
        uint256 oldMinValue = param.minValue;
        uint256 oldMaxValue = param.maxValue;
        
        // Ensure current value is still within new bounds
        require(param.value >= newMinValue && param.value <= newMaxValue, "ParamRegistry: Current value out of new bounds");
        
        param.minValue = newMinValue;
        param.maxValue = newMaxValue;
        param.lastUpdated = block.timestamp;
        param.updatedBy = msg.sender;
        
        emit ParameterBoundsUpdated(name, oldMinValue, newMinValue, oldMaxValue, newMaxValue, msg.sender);
    }
    
    /**
     * @dev Update parameter value
     * @param name The parameter name
     * @param newValue The new value
     * @param reason The reason for the update
     */
    function updateParameterValue(
        string memory name,
        uint256 newValue,
        string memory reason
    ) external onlyAuthorized validParameterName(name) {
        require(parameterExists[name], "ParamRegistry: Parameter does not exist");
        require(parameters[name].isActive, "ParamRegistry: Parameter is inactive");
        require(bytes(reason).length > 0, "ParamRegistry: Reason required");
        
        Parameter storage param = parameters[name];
        require(newValue >= param.minValue && newValue <= param.maxValue, "ParamRegistry: Value out of bounds");
        
        uint256 oldValue = param.value;
        param.value = newValue;
        param.lastUpdated = block.timestamp;
        param.updatedBy = msg.sender;
        
        _addToHistory(name, oldValue, newValue, reason);
        
        emit ParameterUpdated(name, oldValue, newValue, msg.sender, reason);
    }
    
    /**
     * @dev Deactivate a parameter
     * @param name The parameter name
     * @param reason The reason for deactivation
     */
    function deactivateParameter(
        string memory name,
        string memory reason
    ) external onlyGovernor validParameterName(name) {
        require(parameterExists[name], "ParamRegistry: Parameter does not exist");
        require(parameters[name].isActive, "ParamRegistry: Parameter already inactive");
        require(bytes(reason).length > 0, "ParamRegistry: Reason required");
        
        parameters[name].isActive = false;
        parameters[name].lastUpdated = block.timestamp;
        parameters[name].updatedBy = msg.sender;
        
        emit ParameterDeactivated(name, msg.sender, reason);
    }
    
    /**
     * @dev Activate a parameter
     * @param name The parameter name
     */
    function activateParameter(string memory name) external onlyGovernor validParameterName(name) {
        require(parameterExists[name], "ParamRegistry: Parameter does not exist");
        require(!parameters[name].isActive, "ParamRegistry: Parameter already active");
        
        parameters[name].isActive = true;
        parameters[name].lastUpdated = block.timestamp;
        parameters[name].updatedBy = msg.sender;
        
        emit ParameterActivated(name, msg.sender);
    }
    
    /**
     * @dev Add authorized updater
     * @param updater The address to authorize
     */
    function addAuthorizedUpdater(address updater) external onlyOwner {
        require(updater != address(0), "ParamRegistry: Invalid updater address");
        authorizedUpdaters[updater] = true;
    }
    
    /**
     * @dev Remove authorized updater
     * @param updater The address to remove authorization
     */
    function removeAuthorizedUpdater(address updater) external onlyOwner {
        authorizedUpdaters[updater] = false;
    }
    
    /**
     * @dev Update governor address
     * @param _governor The new governor address
     */
    function updateGovernor(address _governor) external onlyOwner {
        require(_governor != address(0), "ParamRegistry: Invalid governor address");
        governor = _governor;
    }
    
    /**
     * @dev Get parameter value
     * @param name The parameter name
     * @return value The parameter value
     */
    function getParameterValue(string memory name) external view returns (uint256 value) {
        require(parameterExists[name], "ParamRegistry: Parameter does not exist");
        require(parameters[name].isActive, "ParamRegistry: Parameter is inactive");
        return parameters[name].value;
    }
    
    /**
     * @dev Get parameter details
     * @param name The parameter name
     * @return parameter The parameter details
     */
    function getParameter(string memory name) external view returns (Parameter memory parameter) {
        require(parameterExists[name], "ParamRegistry: Parameter does not exist");
        return parameters[name];
    }
    
    /**
     * @dev Get parameter history
     * @param name The parameter name
     * @return history The parameter update history
     */
    function getParameterHistory(string memory name) external view returns (ParameterUpdate[] memory history) {
        require(parameterExists[name], "ParamRegistry: Parameter does not exist");
        return parameterHistory[name];
    }
    
    /**
     * @dev Check if parameter exists
     * @param name The parameter name
     * @return exists Whether the parameter exists
     */
    function parameterExistsCheck(string memory name) external view returns (bool exists) {
        return parameterExists[name];
    }
    
    /**
     * @dev Check if parameter is active
     * @param name The parameter name
     * @return active Whether the parameter is active
     */
    function isParameterActive(string memory name) external view returns (bool active) {
        return parameterExists[name] && parameters[name].isActive;
    }
    
    /**
     * @dev Validate parameter value against bounds
     * @param name The parameter name
     * @param value The value to validate
     * @return valid Whether the value is valid
     * @return reason The validation reason
     */
    function validateParameterValue(
        string memory name,
        uint256 value
    ) external view returns (bool valid, string memory reason) {
        if (!parameterExists[name]) {
            return (false, "Parameter does not exist");
        }
        
        Parameter memory param = parameters[name];
        
        if (!param.isActive) {
            return (false, "Parameter is inactive");
        }
        
        if (value < param.minValue) {
            return (false, "Value below minimum");
        }
        
        if (value > param.maxValue) {
            return (false, "Value above maximum");
        }
        
        return (true, "Valid");
    }
    
    /**
     * @dev Internal function to add parameter to history
     */
    function _addToHistory(
        string memory name,
        uint256 oldValue,
        uint256 newValue,
        string memory reason
    ) internal {
        ParameterUpdate[] storage history = parameterHistory[name];
        
        // Limit history size
        if (history.length >= MAX_HISTORY_ENTRIES) {
            // Remove oldest entry
            for (uint256 i = 0; i < history.length - 1; i++) {
                history[i] = history[i + 1];
            }
            history.pop();
        }
        
        history.push(ParameterUpdate({
            name: name,
            oldValue: oldValue,
            newValue: newValue,
            timestamp: block.timestamp,
            updatedBy: msg.sender,
            reason: reason
        }));
    }
    
    /**
     * @dev Get all parameter names
     * @return names Array of parameter names
     */
    function getAllParameterNames() external view returns (string[] memory names) {
        // This is a simplified implementation
        // In a real implementation, you might want to maintain a separate array
        // or use events to track parameter names
        string[] memory defaultNames = new string[](12);
        defaultNames[0] = "SLOT_DURATION_SEC";
        defaultNames[1] = "SLOT_TIMEOUT_MS";
        defaultNames[2] = "COOLDOWN_SLOTS";
        defaultNames[3] = "LEADER_WINDOW_DAYS";
        defaultNames[4] = "D_MIN";
        defaultNames[5] = "BASE_MB_PER_SESSION";
        defaultNames[6] = "MAX_PAYOUT_AMOUNT";
        defaultNames[7] = "DAILY_PAYOUT_LIMIT";
        defaultNames[8] = "MIN_KYC_LEVEL";
        defaultNames[9] = "MAX_SESSION_DURATION";
        defaultNames[10] = "MAX_CHUNK_SIZE";
        defaultNames[11] = "MAX_PEERS";
        
        return defaultNames;
    }
}
