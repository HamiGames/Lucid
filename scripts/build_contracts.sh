#!/bin/bash
# Path: scripts/build_contracts.sh
# Build and deploy Lucid RDP smart contracts to On-System Chain and TRON
# Based on LUCID-STRICT requirements per Spec-1b

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONTRACTS_DIR="${PROJECT_ROOT}/contracts"
BUILD_DIR="${PROJECT_ROOT}/build/contracts"
DEPLOY_DIR="${PROJECT_ROOT}/deploy/contracts"

# Network configurations
TRON_SHASTA_RPC="https://api.shasta.trongrid.io"
TRON_MAINNET_RPC="https://api.trongrid.io"
ON_SYSTEM_CHAIN_RPC="${ON_SYSTEM_CHAIN_RPC:-http://localhost:8545}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO) echo -e "${BLUE}[INFO]${NC} [$timestamp] $message" ;;
        WARN) echo -e "${YELLOW}[WARN]${NC} [$timestamp] $message" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} [$timestamp] $message" >&2 ;;
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} [$timestamp] $message" ;;
        DEPLOY) echo -e "${MAGENTA}[DEPLOY]${NC} [$timestamp] $message" ;;
    esac
}

check_dependencies() {
    log INFO "Checking contract build dependencies..."
    
    local missing_deps=()
    
    # Check for Solidity compiler
    if ! command -v solc &> /dev/null; then
        missing_deps+=("solc")
    fi
    
    # Check for Node.js and npm
    if ! command -v node &> /dev/null; then
        missing_deps+=("nodejs")
    fi
    
    if ! command -v npm &> /dev/null; then
        missing_deps+=("npm")
    fi
    
    # Check for TronBox for TRON deployment
    if ! command -v tronbox &> /dev/null && ! npx tronbox --version &> /dev/null; then
        log WARN "TronBox not found globally, will install locally"
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log ERROR "Missing dependencies: ${missing_deps[*]}"
        log INFO "Install Solidity: https://docs.soliditylang.org/en/latest/installing-solidity.html"
        log INFO "Install Node.js: https://nodejs.org/"
        return 1
    fi
    
    log SUCCESS "All dependencies available"
    return 0
}

setup_build_environment() {
    log INFO "Setting up contract build environment..."
    
    # Create build directories
    mkdir -p "$BUILD_DIR"
    mkdir -p "$DEPLOY_DIR"
    
    # Initialize npm project if needed
    if [[ ! -f "${PROJECT_ROOT}/package.json" ]]; then
        cd "$PROJECT_ROOT"
        npm init -y > /dev/null
        log INFO "Initialized npm project"
    fi
    
    # Install required packages
    cd "$PROJECT_ROOT"
    local packages=(
        "@openzeppelin/contracts@^4.9.0"
        "@tronbox/cli@^3.0.0"
        "tronweb@^5.3.0"
        "web3@^1.10.0"
        "hardhat@^2.17.0"
        "@nomiclabs/hardhat-waffle@^2.0.6"
        "@nomiclabs/hardhat-ethers@^2.2.3"
        "ethereum-waffle@^4.0.10"
        "chai@^4.3.7"
        "ethers@^5.7.2"
    )
    
    log INFO "Installing contract dependencies..."
    npm install --save-dev "${packages[@]}" > /dev/null
    
    log SUCCESS "Build environment ready"
}

create_contract_templates() {
    log INFO "Creating Solidity contract templates..."
    
    mkdir -p "$CONTRACTS_DIR"
    
    # LucidAnchors.sol - Session anchoring contract per Spec-1b
    cat > "${CONTRACTS_DIR}/LucidAnchors.sol" << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title LucidAnchors
 * @dev Session manifest anchoring for Lucid RDP
 * Per Spec-1b: immutable after deploy, ownership renounced, no upgrade proxy
 */
contract LucidAnchors is Ownable, Pausable, ReentrancyGuard {
    
    struct SessionAnchor {
        bytes32 sessionId;
        bytes32 manifestHash;
        bytes32 merkleRoot;
        uint64 startedAt;
        address owner;
        uint32 chunkCount;
        uint256 blockNumber;
        uint256 timestamp;
    }
    
    // Events per specification - prefer events over storage
    event SessionRegistered(
        bytes32 indexed sessionId,
        bytes32 indexed manifestHash,
        address indexed owner,
        bytes32 merkleRoot,
        uint32 chunkCount
    );
    
    event ChunkAnchored(
        bytes32 indexed sessionId,
        uint32 indexed chunkIndex,
        bytes32 chunkHash
    );
    
    // Minimal storage to prevent duplicate roots
    mapping(bytes32 => bool) private registeredSessions;
    mapping(bytes32 => bool) private usedMerkleRoots;
    
    // Circuit breaker parameters
    uint256 public maxSessionsPerBlock = 100;
    uint256 public sessionsInCurrentBlock = 0;
    uint256 public currentBlockNumber = 0;
    
    /**
     * @dev Register session manifest with Merkle root
     * Gas-efficient: uses events for data, minimal storage
     */
    function registerSession(
        bytes32 sessionId,
        bytes32 manifestHash,
        uint64 startedAt,
        address owner,
        bytes32 merkleRoot,
        uint32 chunkCount
    ) external whenNotPaused nonReentrant {
        require(sessionId != bytes32(0), "Invalid session ID");
        require(manifestHash != bytes32(0), "Invalid manifest hash");
        require(merkleRoot != bytes32(0), "Invalid Merkle root");
        require(owner != address(0), "Invalid owner address");
        require(!registeredSessions[sessionId], "Session already registered");
        require(!usedMerkleRoots[merkleRoot], "Merkle root already used");
        
        // Circuit breaker
        if (block.number != currentBlockNumber) {
            currentBlockNumber = block.number;
            sessionsInCurrentBlock = 0;
        }
        require(sessionsInCurrentBlock < maxSessionsPerBlock, "Block limit reached");
        sessionsInCurrentBlock++;
        
        // Mark as registered
        registeredSessions[sessionId] = true;
        usedMerkleRoots[merkleRoot] = true;
        
        // Emit event with all data (gas-efficient anchoring)
        emit SessionRegistered(
            sessionId,
            manifestHash,
            owner,
            merkleRoot,
            chunkCount
        );
    }
    
    /**
     * @dev Optional granular chunk anchoring
     */
    function anchorChunk(
        bytes32 sessionId,
        uint32 chunkIndex,
        bytes32 chunkHash
    ) external whenNotPaused {
        require(registeredSessions[sessionId], "Session not registered");
        require(chunkHash != bytes32(0), "Invalid chunk hash");
        
        emit ChunkAnchored(sessionId, chunkIndex, chunkHash);
    }
    
    /**
     * @dev Check if session is registered
     */
    function isSessionRegistered(bytes32 sessionId) external view returns (bool) {
        return registeredSessions[sessionId];
    }
    
    /**
     * @dev Emergency pause (only before ownership renouncement)
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
    
    /**
     * @dev Renounce ownership to make contract immutable
     * This should be called after initial setup and testing
     */
    function finalizeContract() external onlyOwner {
        renounceOwnership();
    }
}
EOF

    # PayoutRouterV0.sol - No-KYC USDT payouts per Spec-1b
    cat > "${CONTRACTS_DIR}/PayoutRouterV0.sol" << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title PayoutRouterV0
 * @dev No-KYC USDT payout router for Lucid RDP
 * Per Spec-1b: deployed now to avoid contract migrations later
 */
contract PayoutRouterV0 is AccessControl, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;
    
    bytes32 public constant DISBURSER_ROLE = keccak256("DISBURSER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    
    IERC20 public immutable usdt;
    
    // Circuit breaker parameters (set at deploy)
    uint256 public immutable maxPerTx;
    uint256 public immutable maxPerDay;
    
    // Daily limits tracking
    mapping(uint256 => uint256) public dailyDisbursed; // day => amount
    
    event Paid(
        bytes32 indexed sessionId,
        address indexed to,
        uint256 amount,
        string reason
    );
    
    event EmergencyWithdraw(address indexed to, uint256 amount);
    
    constructor(
        address _usdt,
        uint256 _maxPerTx,
        uint256 _maxPerDay,
        address _admin,
        address _disburser,
        address _pauser
    ) {
        require(_usdt != address(0), "Invalid USDT address");
        require(_maxPerTx > 0, "Invalid max per tx");
        require(_maxPerDay > 0, "Invalid max per day");
        
        usdt = IERC20(_usdt);
        maxPerTx = _maxPerTx;
        maxPerDay = _maxPerDay;
        
        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(DISBURSER_ROLE, _disburser);
        _grantRole(PAUSER_ROLE, _pauser);
    }
    
    /**
     * @dev Disburse USDT to recipient
     * Called by Pi or designated service account
     */
    function disburse(
        bytes32 sessionId,
        address to,
        uint256 amount,
        string calldata reason
    ) external onlyRole(DISBURSER_ROLE) whenNotPaused nonReentrant {
        require(to != address(0), "Invalid recipient");
        require(amount > 0, "Invalid amount");
        require(amount <= maxPerTx, "Exceeds per-tx limit");
        
        // Check daily limit
        uint256 today = block.timestamp / 1 days;
        require(dailyDisbursed[today] + amount <= maxPerDay, "Exceeds daily limit");
        
        // Update daily total
        dailyDisbursed[today] += amount;
        
        // Transfer USDT
        usdt.safeTransfer(to, amount);
        
        emit Paid(sessionId, to, amount, reason);
    }
    
    /**
     * @dev Get current day's disbursed amount
     */
    function getTodayDisbursed() external view returns (uint256) {
        uint256 today = block.timestamp / 1 days;
        return dailyDisbursed[today];
    }
    
    /**
     * @dev Emergency withdraw (admin only)
     */
    function emergencyWithdraw(address to, uint256 amount) 
        external 
        onlyRole(DEFAULT_ADMIN_ROLE) 
        whenPaused 
    {
        require(to != address(0), "Invalid recipient");
        usdt.safeTransfer(to, amount);
        emit EmergencyWithdraw(to, amount);
    }
    
    /**
     * @dev Pause contract
     */
    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }
    
    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }
    
    /**
     * @dev Get contract balance
     */
    function balance() external view returns (uint256) {
        return usdt.balanceOf(address(this));
    }
}
EOF

    # PayoutRouterKYC.sol - KYC-gated payouts per Spec-1b
    cat > "${CONTRACTS_DIR}/PayoutRouterKYC.sol" << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./PayoutRouterV0.sol";

/**
 * @title PayoutRouterKYC
 * @dev KYC-gated USDT payout router for Lucid RDP
 * Extends PayoutRouterV0 with compliance signature checks
 */
contract PayoutRouterKYC is PayoutRouterV0 {
    
    bytes32 public constant COMPLIANCE_SIGNER_ROLE = keccak256("COMPLIANCE_SIGNER_ROLE");
    
    // Daily limits per address
    mapping(address => mapping(uint256 => uint256)) public dailyLimits;
    
    event KYCPayout(
        bytes32 indexed sessionId,
        address indexed to,
        uint256 amount,
        bytes32 kycHash,
        uint256 expiry
    );
    
    constructor(
        address _usdt,
        uint256 _maxPerTx,
        uint256 _maxPerDay,
        address _admin,
        address _disburser,
        address _pauser,
        address _complianceSigner
    ) PayoutRouterV0(_usdt, _maxPerTx, _maxPerDay, _admin, _disburser, _pauser) {
        _grantRole(COMPLIANCE_SIGNER_ROLE, _complianceSigner);
    }
    
    /**
     * @dev KYC-gated disbursement with compliance signature
     * Requires ECDSA signature over (to, kycHash, expiry)
     */
    function disburseKYC(
        bytes32 sessionId,
        address to,
        uint256 amount,
        string calldata reason,
        bytes32 kycHash,
        uint256 expiry,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external onlyRole(DISBURSER_ROLE) whenNotPaused nonReentrant {
        require(block.timestamp <= expiry, "Signature expired");
        require(kycHash != bytes32(0), "Invalid KYC hash");
        
        // Verify compliance signature
        bytes32 messageHash = keccak256(
            abi.encodePacked(
                "\x19Ethereum Signed Message:\n32",
                keccak256(abi.encodePacked(to, kycHash, expiry))
            )
        );
        
        address signer = ecrecover(messageHash, v, r, s);
        require(hasRole(COMPLIANCE_SIGNER_ROLE, signer), "Invalid compliance signature");
        
        // Check per-address daily limit if set
        uint256 today = block.timestamp / 1 days;
        uint256 addressLimit = dailyLimits[to][today];
        if (addressLimit > 0) {
            require(amount <= addressLimit, "Exceeds address daily limit");
            dailyLimits[to][today] -= amount;
        }
        
        // Call parent disburse function
        this.disburse(sessionId, to, amount, reason);
        
        emit KYCPayout(sessionId, to, amount, kycHash, expiry);
    }
    
    /**
     * @dev Set daily limit for specific address
     */
    function setDailyLimit(address user, uint256 limit) 
        external 
        onlyRole(COMPLIANCE_SIGNER_ROLE) 
    {
        uint256 today = block.timestamp / 1 days;
        dailyLimits[user][today] = limit;
    }
}
EOF

    # ParamRegistry.sol - Bounded parameter management per Spec-1b
    cat > "${CONTRACTS_DIR}/ParamRegistry.sol" << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title ParamRegistry
 * @dev Bounded parameter registry for Lucid governance
 * Per Spec-1b: immutable interface, bounded typed keys only
 */
contract ParamRegistry is Ownable {
    
    struct ParamBounds {
        uint256 minValue;
        uint256 maxValue;
        bool exists;
    }
    
    mapping(string => uint256) public params;
    mapping(string => ParamBounds) public bounds;
    
    event ParamUpdated(string indexed key, uint256 oldValue, uint256 newValue);
    event BoundsSet(string indexed key, uint256 minValue, uint256 maxValue);
    
    constructor() {
        // Initialize consensus parameters per Spec-1b
        _setBounds("slotDurationSec", 120, 120);           // Fixed at 120s
        _setBounds("slotTimeoutMs", 1000, 10000);          // 1-10 seconds
        _setBounds("cooldownSlots", 8, 64);                // 8-64 slots
        _setBounds("leaderWindowDays", 3, 14);             // 3-14 days
        _setBounds("BASE_MB_PER_SESSION", 1, 50);          // 1-50 MB
        _setBounds("payoutEpochLength", 86400, 2678400);   // 1-31 days in seconds
        _setBounds("maxChunkSize", 1048576, 67108864);     // 1-64 MB
        _setBounds("policyTimeoutMs", 1000, 300000);       // 1-300 seconds
        
        // Set defaults
        params["slotDurationSec"] = 120;
        params["slotTimeoutMs"] = 5000;
        params["cooldownSlots"] = 16;
        params["leaderWindowDays"] = 7;
        params["BASE_MB_PER_SESSION"] = 5;
        params["payoutEpochLength"] = 2592000; // 30 days
        params["maxChunkSize"] = 16777216;     // 16 MB
        params["policyTimeoutMs"] = 30000;     // 30 seconds
    }
    
    function _setBounds(string memory key, uint256 min, uint256 max) private {
        bounds[key] = ParamBounds({
            minValue: min,
            maxValue: max,
            exists: true
        });
        emit BoundsSet(key, min, max);
    }
    
    /**
     * @dev Update parameter value within bounds
     * Only callable by governance (owner)
     */
    function setParam(string calldata key, uint256 value) external onlyOwner {
        ParamBounds memory bound = bounds[key];
        require(bound.exists, "Parameter not defined");
        require(value >= bound.minValue && value <= bound.maxValue, "Value out of bounds");
        
        uint256 oldValue = params[key];
        params[key] = value;
        
        emit ParamUpdated(key, oldValue, value);
    }
    
    /**
     * @dev Get parameter value
     */
    function getParam(string calldata key) external view returns (uint256) {
        require(bounds[key].exists, "Parameter not defined");
        return params[key];
    }
    
    /**
     * @dev Get parameter bounds
     */
    function getBounds(string calldata key) external view returns (uint256 min, uint256 max) {
        ParamBounds memory bound = bounds[key];
        require(bound.exists, "Parameter not defined");
        return (bound.minValue, bound.maxValue);
    }
}
EOF

    log SUCCESS "Contract templates created"
}

compile_contracts() {
    log INFO "Compiling Solidity contracts..."
    
    cd "$PROJECT_ROOT"
    
    # Create Hardhat config
    cat > "hardhat.config.js" << 'EOF'
require("@nomiclabs/hardhat-waffle");
require("@nomiclabs/hardhat-ethers");

module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    hardhat: {
      chainId: 1337
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 1337
    },
    onsystem: {
      url: process.env.ON_SYSTEM_CHAIN_RPC || "http://localhost:8545",
      chainId: 31337,
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : []
    }
  },
  paths: {
    sources: "./contracts",
    artifacts: "./build/contracts",
    cache: "./build/cache"
  }
};
EOF

    # Compile with Hardhat
    npx hardhat compile
    
    if [[ $? -eq 0 ]]; then
        log SUCCESS "Contract compilation completed"
    else
        log ERROR "Contract compilation failed"
        return 1
    fi
}

create_deployment_scripts() {
    log INFO "Creating deployment scripts..."
    
    mkdir -p "${DEPLOY_DIR}"
    
    # On-System Chain deployment script
    cat > "${DEPLOY_DIR}/deploy-onsystem.js" << 'EOF'
const { ethers } = require("hardhat");

async function main() {
    console.log("Deploying Lucid contracts to On-System Chain...");
    
    const [deployer] = await ethers.getSigners();
    console.log("Deployer address:", deployer.address);
    
    const balance = await deployer.getBalance();
    console.log("Deployer balance:", ethers.utils.formatEther(balance), "ETH");
    
    // Deploy ParamRegistry first
    const ParamRegistry = await ethers.getContractFactory("ParamRegistry");
    const paramRegistry = await ParamRegistry.deploy();
    await paramRegistry.deployed();
    console.log("ParamRegistry deployed to:", paramRegistry.address);
    
    // Deploy LucidAnchors
    const LucidAnchors = await ethers.getContractFactory("LucidAnchors");
    const lucidAnchors = await LucidAnchors.deploy();
    await lucidAnchors.deployed();
    console.log("LucidAnchors deployed to:", lucidAnchors.address);
    
    // Wait for confirmations
    console.log("Waiting for confirmations...");
    await paramRegistry.deployTransaction.wait(2);
    await lucidAnchors.deployTransaction.wait(2);
    
    // Save deployment info
    const deployment = {
        network: "onsystem",
        chainId: (await ethers.provider.getNetwork()).chainId,
        deployer: deployer.address,
        contracts: {
            ParamRegistry: paramRegistry.address,
            LucidAnchors: lucidAnchors.address
        },
        blockNumber: await ethers.provider.getBlockNumber(),
        timestamp: Date.now()
    };
    
    console.log("Deployment completed:", JSON.stringify(deployment, null, 2));
    return deployment;
}

if (require.main === module) {
    main()
        .then(() => process.exit(0))
        .catch((error) => {
            console.error(error);
            process.exit(1);
        });
}

module.exports = main;
EOF

    # TRON deployment script
    cat > "${DEPLOY_DIR}/deploy-tron.js" << 'EOF'
const TronWeb = require('tronweb');

async function deployToTron(network = 'shasta') {
    console.log(`Deploying Lucid payout contracts to TRON ${network}...`);
    
    const privateKey = process.env.TRON_PRIVATE_KEY;
    if (!privateKey) {
        throw new Error('TRON_PRIVATE_KEY environment variable required');
    }
    
    // Initialize TronWeb
    const tronWeb = new TronWeb({
        fullHost: network === 'mainnet' ? 
            'https://api.trongrid.io' : 
            'https://api.shasta.trongrid.io',
        privateKey: privateKey
    });
    
    console.log("Deployer address:", tronWeb.address.fromPrivateKey(privateKey));
    
    // USDT contract addresses
    const usdtAddress = network === 'mainnet' ? 
        'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t' :  // Mainnet USDT
        'TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs';   // Shasta USDT
    
    // Contract parameters
    const maxPerTx = tronWeb.toSun(10000);        // 10,000 USDT
    const maxPerDay = tronWeb.toSun(1000000);     // 1,000,000 USDT
    const adminAddress = tronWeb.address.fromPrivateKey(privateKey);
    const disburserAddress = adminAddress;        // Same for demo
    const pauserAddress = adminAddress;           // Same for demo
    const complianceSignerAddress = adminAddress; // Same for demo
    
    console.log("Contract parameters:");
    console.log("  USDT:", usdtAddress);
    console.log("  Max per tx:", tronWeb.fromSun(maxPerTx), "USDT");
    console.log("  Max per day:", tronWeb.fromSun(maxPerDay), "USDT");
    
    // Read contract bytecode (would need to be compiled for TVM)
    // This is a placeholder - actual deployment would use TronBox
    console.log("Note: Full TRON deployment requires TronBox compilation");
    console.log("Run: tronbox migrate --network", network);
    
    const deployment = {
        network: `tron-${network}`,
        deployer: adminAddress,
        parameters: {
            usdt: usdtAddress,
            maxPerTx: tronWeb.fromSun(maxPerTx),
            maxPerDay: tronWeb.fromSun(maxPerDay),
            admin: adminAddress,
            disburser: disburserAddress,
            pauser: pauserAddress,
            complianceSigner: complianceSignerAddress
        },
        timestamp: Date.now()
    };
    
    console.log("TRON deployment info:", JSON.stringify(deployment, null, 2));
    return deployment;
}

if (require.main === module) {
    const network = process.argv[2] || 'shasta';
    deployToTron(network)
        .then(() => process.exit(0))
        .catch((error) => {
            console.error(error);
            process.exit(1);
        });
}

module.exports = deployToTron;
EOF

    chmod +x "${DEPLOY_DIR}"/*.js
    log SUCCESS "Deployment scripts created"
}

run_tests() {
    log INFO "Running contract tests..."
    
    # Create basic test file
    mkdir -p "${PROJECT_ROOT}/test"
    
    cat > "${PROJECT_ROOT}/test/contracts.test.js" << 'EOF'
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Lucid Contracts", function() {
    let deployer, user1, user2;
    let lucidAnchors, paramRegistry;
    
    beforeEach(async function() {
        [deployer, user1, user2] = await ethers.getSigners();
        
        const ParamRegistry = await ethers.getContractFactory("ParamRegistry");
        paramRegistry = await ParamRegistry.deploy();
        
        const LucidAnchors = await ethers.getContractFactory("LucidAnchors");
        lucidAnchors = await LucidAnchors.deploy();
    });
    
    describe("LucidAnchors", function() {
        it("Should register session correctly", async function() {
            const sessionId = ethers.utils.keccak256(ethers.utils.toUtf8Bytes("test-session"));
            const manifestHash = ethers.utils.keccak256(ethers.utils.toUtf8Bytes("test-manifest"));
            const merkleRoot = ethers.utils.keccak256(ethers.utils.toUtf8Bytes("test-root"));
            
            await expect(lucidAnchors.registerSession(
                sessionId,
                manifestHash,
                Math.floor(Date.now() / 1000),
                user1.address,
                merkleRoot,
                5
            )).to.emit(lucidAnchors, "SessionRegistered");
            
            expect(await lucidAnchors.isSessionRegistered(sessionId)).to.be.true;
        });
        
        it("Should prevent duplicate sessions", async function() {
            const sessionId = ethers.utils.keccak256(ethers.utils.toUtf8Bytes("test-session"));
            const manifestHash = ethers.utils.keccak256(ethers.utils.toUtf8Bytes("test-manifest"));
            const merkleRoot = ethers.utils.keccak256(ethers.utils.toUtf8Bytes("test-root"));
            
            await lucidAnchors.registerSession(
                sessionId, manifestHash, Math.floor(Date.now() / 1000), 
                user1.address, merkleRoot, 5
            );
            
            await expect(lucidAnchors.registerSession(
                sessionId, manifestHash, Math.floor(Date.now() / 1000),
                user1.address, merkleRoot, 5
            )).to.be.revertedWith("Session already registered");
        });
    });
    
    describe("ParamRegistry", function() {
        it("Should have default parameters", async function() {
            expect(await paramRegistry.getParam("slotDurationSec")).to.equal(120);
            expect(await paramRegistry.getParam("slotTimeoutMs")).to.equal(5000);
        });
        
        it("Should enforce parameter bounds", async function() {
            await expect(
                paramRegistry.setParam("slotTimeoutMs", 500)
            ).to.be.revertedWith("Value out of bounds");
            
            await expect(
                paramRegistry.setParam("slotTimeoutMs", 20000)
            ).to.be.revertedWith("Value out of bounds");
        });
        
        it("Should update parameters within bounds", async function() {
            await paramRegistry.setParam("slotTimeoutMs", 3000);
            expect(await paramRegistry.getParam("slotTimeoutMs")).to.equal(3000);
        });
    });
});
EOF

    # Run tests
    cd "$PROJECT_ROOT"
    npx hardhat test
    
    if [[ $? -eq 0 ]]; then
        log SUCCESS "Contract tests passed"
    else
        log ERROR "Contract tests failed"
        return 1
    fi
}

deploy_contracts() {
    local network=$1
    log DEPLOY "Deploying contracts to $network..."
    
    case $network in
        "onsystem")
            cd "$PROJECT_ROOT"
            npx hardhat run "${DEPLOY_DIR}/deploy-onsystem.js" --network onsystem
            ;;
        "tron-shasta")
            node "${DEPLOY_DIR}/deploy-tron.js" shasta
            ;;
        "tron-mainnet")
            log WARN "Deploying to TRON mainnet - ensure you have real TRX!"
            read -p "Continue with mainnet deployment? (y/N): " confirm
            if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
                node "${DEPLOY_DIR}/deploy-tron.js" mainnet
            else
                log INFO "Mainnet deployment cancelled"
            fi
            ;;
        *)
            log ERROR "Unknown network: $network"
            return 1
            ;;
    esac
}

show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Build and deploy Lucid RDP smart contracts"
    echo
    echo "Commands:"
    echo "  build        Compile contracts and run tests"
    echo "  deploy       Deploy contracts to specified network"
    echo "  test         Run contract tests only"
    echo "  clean        Clean build artifacts"
    echo "  help         Show this help message"
    echo
    echo "Deploy Options:"
    echo "  --network    Target network: onsystem, tron-shasta, tron-mainnet"
    echo
    echo "Environment Variables:"
    echo "  ON_SYSTEM_CHAIN_RPC      On-System Chain RPC URL"
    echo "  TRON_PRIVATE_KEY         TRON deployment private key"
    echo "  PRIVATE_KEY              Ethereum-compatible private key"
    echo
    echo "Examples:"
    echo "  $0 build                             # Compile and test contracts"
    echo "  $0 deploy --network onsystem         # Deploy to On-System Chain"
    echo "  $0 deploy --network tron-shasta      # Deploy to TRON Shasta"
    echo "  $0 test                              # Run tests only"
}

main() {
    local command=${1:-help}
    local network="onsystem"
    
    # Parse arguments
    shift || true
    while [[ $# -gt 0 ]]; do
        case $1 in
            --network)
                network="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    case $command in
        "build")
            log INFO "Starting contract build process..."
            check_dependencies || exit 1
            setup_build_environment || exit 1
            create_contract_templates || exit 1
            compile_contracts || exit 1
            create_deployment_scripts || exit 1
            run_tests || exit 1
            log SUCCESS "Contract build completed successfully!"
            ;;
        "deploy")
            log INFO "Starting contract deployment..."
            deploy_contracts "$network" || exit 1
            log SUCCESS "Contract deployment completed!"
            ;;
        "test")
            log INFO "Running contract tests..."
            run_tests || exit 1
            log SUCCESS "Contract tests completed!"
            ;;
        "clean")
            log INFO "Cleaning build artifacts..."
            rm -rf "$BUILD_DIR" "${PROJECT_ROOT}/cache" "${PROJECT_ROOT}/node_modules"
            log SUCCESS "Clean completed"
            ;;
        "help")
            show_usage
            ;;
        *)
            echo "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"