# LUCID SERVICE ENVIRONMENT GENERATOR
# Generates environment configuration files for all distroless services
# Creates .env files and compose configurations with proper environment variables

param(
    [string]$OutputDir = "configs/environment",
    [string]$TemplateDir = "configs/environment/templates",
    [switch]$GenerateCompose = $true,
    [switch]$GenerateEnv = $true,
    [switch]$Verbose = $false
)

# Set strict mode and error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Color functions for output
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { param([string]$Message) Write-ColorOutput "✅ $Message" "Green" }
function Write-Error { param([string]$Message) Write-ColorOutput "❌ $Message" "Red" }
function Write-Warning { param([string]$Message) Write-ColorOutput "⚠️ $Message" "Yellow" }
function Write-Info { param([string]$Message) Write-ColorOutput "ℹ️ $Message" "Cyan" }
function Write-Progress { param([string]$Message) Write-ColorOutput "🔄 $Message" "Blue" }

# Service environment templates
$ServiceEnvironments = @{
    "admin-ui" = @{
        NODE_ENV = "production"
        NEXT_TELEMETRY_DISABLED = "1"
        PORT = "3000"
        HOSTNAME = "0.0.0.0"
        NEXT_PUBLIC_API_URL = "http://localhost:8081"
        NEXT_PUBLIC_WS_URL = "ws://localhost:8081/ws"
        NEXT_PUBLIC_ADMIN_URL = "http://localhost:3000"
        ADMIN_SECRET_KEY = "lucid-admin-secret-key-change-in-production"
    }
    
    "blockchain-api" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        API_HOST = "0.0.0.0"
        API_PORT = "8084"
        UVICORN_WORKERS = "1"
        LOG_LEVEL = "INFO"
        MONGO_URI = "mongodb://lucid:lucid@mongodb:27017/lucid?authSource=admin&retryWrites=false&directConnection=true"
        MONGO_DB = "lucid"
        KEY_ENC_SECRET = "lucid-key-encryption-secret-change-in-production"
        TRON_NETWORK = "shasta"
        TRONGRID_API_KEY = ""
        TRON_HTTP_ENDPOINT = ""
        BLOCK_ONION = ""
        BLOCK_RPC_URL = ""
        REDIS_URL = "redis://redis:6379/0"
        JWT_SECRET_KEY = "lucid-jwt-secret-key-change-in-production"
    }
    
    "authentication-service" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        API_HOST = "0.0.0.0"
        API_PORT = "8085"
        LOG_LEVEL = "INFO"
        MONGO_URI = "mongodb://lucid:lucid@mongodb:27017/lucid?authSource=admin&retryWrites=false&directConnection=true"
        MONGO_DB = "lucid"
        JWT_SECRET_KEY = "lucid-jwt-secret-key-change-in-production"
        JWT_ALGORITHM = "HS256"
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES = "30"
        JWT_REFRESH_TOKEN_EXPIRE_DAYS = "7"
        HARDWARE_WALLET_TIMEOUT = "30"
        SESSION_TIMEOUT_MINUTES = "60"
        MAX_LOGIN_ATTEMPTS = "5"
        LOCKOUT_DURATION_MINUTES = "15"
    }
    
    "user-manager" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        API_HOST = "0.0.0.0"
        API_PORT = "8086"
        LOG_LEVEL = "INFO"
        MONGO_URI = "mongodb://lucid:lucid@mongodb:27017/lucid?authSource=admin&retryWrites=false&directConnection=true"
        MONGO_DB = "lucid"
        USER_SESSION_TIMEOUT = "3600"
        MAX_CONCURRENT_SESSIONS = "5"
        KYC_VERIFICATION_URL = ""
        KYC_API_KEY = ""
        ROLE_DEFAULT = "user"
        PERMISSION_CACHE_TTL = "300"
    }
    
    "mongodb" = @{
        MONGO_INITDB_ROOT_USERNAME = "lucid"
        MONGO_INITDB_ROOT_PASSWORD = "lucid"
        MONGO_INITDB_DATABASE = "lucid"
        MONGO_DB_USERNAME = "lucid"
        MONGO_DB_PASSWORD = "lucid"
        MONGO_DB_AUTH_SOURCE = "admin"
        MONGO_REPLICA_SET = ""
        MONGO_OPLOG_SIZE = "1024"
        MONGO_CACHE_SIZE_GB = "1"
        MONGO_WIRED_TIGER_CACHE_SIZE_GB = "1"
    }
    
    "redis" = @{
        REDIS_PASSWORD = "lucid-redis-password-change-in-production"
        REDIS_MAXMEMORY = "256mb"
        REDIS_MAXMEMORY_POLICY = "allkeys-lru"
        REDIS_TIMEOUT = "300"
        REDIS_DATABASES = "16"
        REDIS_SAVE = "900 1 300 10 60 10000"
    }
    
    "session-recorder" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        RECORDING_HOST = "0.0.0.0"
        RECORDING_PORT = "8087"
        LOG_LEVEL = "INFO"
        SESSION_STORAGE_PATH = "/data/sessions"
        CHUNK_SIZE_MB = "16"
        COMPRESSION_LEVEL = "6"
        ENCRYPTION_KEY = "lucid-session-encryption-key-change-in-production"
        MERKLE_HASH_ALGORITHM = "blake3"
        MAX_SESSION_DURATION_HOURS = "8"
        CLEANUP_INTERVAL_HOURS = "24"
        MONGO_URI = "mongodb://lucid:lucid@mongodb:27017/lucid?authSource=admin&retryWrites=false&directConnection=true"
    }
    
    "chunker" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        CHUNKER_HOST = "0.0.0.0"
        CHUNKER_PORT = "8088"
        LOG_LEVEL = "INFO"
        CHUNK_SIZE_MB = "16"
        COMPRESSION_ALGORITHM = "zstd"
        COMPRESSION_LEVEL = "6"
        MAX_CHUNKS_PER_SESSION = "10000"
        CHUNK_STORAGE_PATH = "/data/chunks"
        CLEANUP_INTERVAL_HOURS = "24"
    }
    
    "encryptor" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        ENCRYPTOR_HOST = "0.0.0.0"
        ENCRYPTOR_PORT = "8089"
        LOG_LEVEL = "INFO"
        ENCRYPTION_ALGORITHM = "XChaCha20-Poly1305"
        ENCRYPTION_KEY = "lucid-encryption-key-change-in-production"
        KEY_DERIVATION_ITERATIONS = "100000"
        SALT_LENGTH = "32"
        NONCE_LENGTH = "24"
    }
    
    "merkle-builder" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        MERKLE_HOST = "0.0.0.0"
        MERKLE_PORT = "8090"
        LOG_LEVEL = "INFO"
        HASH_ALGORITHM = "blake3"
        TREE_DEPTH_LIMIT = "32"
        MAX_LEAVES = "4294967296"
        CACHE_SIZE_MB = "256"
        WORKER_THREADS = "4"
    }
    
    "chain-client" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        CHAIN_CLIENT_HOST = "0.0.0.0"
        CHAIN_CLIENT_PORT = "8091"
        LOG_LEVEL = "INFO"
        RPC_URL = "http://localhost:8545"
        CHAIN_ID = "1337"
        PRIVATE_KEY = ""
        CONTRACT_ADDRESSES = '{"LucidAnchors":"","LucidChunkStore":""}'
        GAS_LIMIT = "100000"
        GAS_PRICE = "20000000000"
        TRANSACTION_TIMEOUT = "300"
        RETRY_ATTEMPTS = "3"
    }
    
    "tron-client" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        TRON_CLIENT_HOST = "0.0.0.0"
        TRON_CLIENT_PORT = "8092"
        LOG_LEVEL = "INFO"
        TRON_NETWORK = "shasta"
        TRONGRID_API_KEY = ""
        TRON_HTTP_ENDPOINT = ""
        PRIVATE_KEY = ""
        CONTRACT_ADDRESSES = '{"PayoutRouterV0":"","PayoutRouterKYC":"","USDT_TRC20":""}'
        GAS_LIMIT = "100000"
        GAS_PRICE = "1000"
        TRANSACTION_TIMEOUT = "300"
        RETRY_ATTEMPTS = "3"
    }
    
    "dht-node" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        DHT_NODE_HOST = "0.0.0.0"
        DHT_NODE_PORT = "8093"
        LOG_LEVEL = "INFO"
        BOOTSTRAP_NODES = ""
        MAX_PEERS = "100"
        MIN_PEERS = "10"
        PEER_DISCOVERY_INTERVAL = "60"
        DATA_STORAGE_PATH = "/data/dht"
        REPLICATION_FACTOR = "3"
        CONSISTENCY_LEVEL = "eventual"
    }
    
    "rdp-host" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        RDP_HOST = "0.0.0.0"
        RDP_PORT = "3389"
        LOG_LEVEL = "INFO"
        DISPLAY_NUMBER = "1"
        RESOLUTION = "1920x1080"
        COLOR_DEPTH = "24"
        XRDP_CONFIG_PATH = "/etc/xrdp"
        XRDP_LOG_PATH = "/var/log/xrdp"
        SESSION_TIMEOUT = "3600"
        MAX_CONNECTIONS = "10"
        CLIPBOARD_ENABLED = "true"
        FILE_TRANSFER_ENABLED = "true"
    }
    
    "hardware-wallet" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        WALLET_HOST = "0.0.0.0"
        WALLET_PORT = "8094"
        LOG_LEVEL = "INFO"
        WALLET_TYPES = "ledger,trezor,keepkey"
        DEVICE_TIMEOUT = "30"
        MAX_DEVICES = "10"
        KEY_DERIVATION_PATH = "m/44'/195'/0'/0/0"
        SIGNATURE_ALGORITHM = "ed25519"
        ENCRYPTION_ALGORITHM = "AES-256-GCM"
        VAULT_STORAGE_PATH = "/data/vault"
    }
    
    "policy-engine" = @{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONUNBUFFERED = "1"
        POLICY_HOST = "0.0.0.0"
        POLICY_PORT = "8095"
        LOG_LEVEL = "INFO"
        POLICY_STORAGE_PATH = "/data/policies"
        DEFAULT_POLICY = "deny-all"
        JIT_APPROVAL_ENABLED = "true"
        POLICY_CACHE_TTL = "300"
        VIOLATION_LOG_PATH = "/data/logs/violations"
        AUDIT_LOG_PATH = "/data/logs/audit"
    }
}

function Generate-EnvironmentFile {
    param([string]$ServiceName, [hashtable]$EnvironmentVars, [string]$OutputPath)
    
    Write-Progress "Generating environment file for $ServiceName"
    
    $envContent = @"
# LUCID $($ServiceName.ToUpper()) ENVIRONMENT CONFIGURATION
# Generated by generate-service-environments.ps1
# Service: $ServiceName
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

"@
    
    foreach ($key in $EnvironmentVars.Keys | Sort-Object) {
        $value = $EnvironmentVars[$key]
        $envContent += "`n$key=$value"
    }
    
    try {
        $outputDir = Split-Path $OutputPath
        if (-not (Test-Path $outputDir)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }
        
        $envContent | Out-File -FilePath $OutputPath -Encoding UTF8
        Write-Success "Generated environment file: $OutputPath"
    }
    catch {
        Write-Error "Failed to generate environment file: $_"
        throw
    }
}

function Generate-ComposeEnvironment {
    param([string]$ServiceName, [hashtable]$EnvironmentVars, [string]$OutputPath)
    
    Write-Progress "Generating compose environment for $ServiceName"
    
    $composeContent = @"
# LUCID $($ServiceName.ToUpper()) COMPOSE ENVIRONMENT
# Generated by generate-service-environments.ps1
# Service: $ServiceName
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

environment:
"@
    
    foreach ($key in $EnvironmentVars.Keys | Sort-Object) {
        $value = $EnvironmentVars[$key]
        $composeContent += "`n  - `"$key=$value`""
    }
    
    try {
        $outputDir = Split-Path $OutputPath
        if (-not (Test-Path $outputDir)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }
        
        $composeContent | Out-File -FilePath $OutputPath -Encoding UTF8
        Write-Success "Generated compose environment: $OutputPath"
    }
    catch {
        Write-Error "Failed to generate compose environment: $_"
        throw
    }
}

function Generate-MasterEnvironment {
    param([string]$OutputPath)
    
    Write-Progress "Generating master environment configuration"
    
    $masterContent = @"
# LUCID MASTER ENVIRONMENT CONFIGURATION
# Generated by generate-service-environments.ps1
# All service environment variables in one file
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

# =============================================================================
# CORE SYSTEM CONFIGURATION
# =============================================================================

# Docker Compose Configuration
COMPOSE_PROJECT_NAME=lucid
COMPOSE_FILE=infrastructure/compose/lucid-distroless-complete.yaml

# Network Configuration
LUCID_CORE_NETWORK=lucid_core_net
LUCID_CORE_SUBNET=172.21.0.0/24
LUCID_CORE_GATEWAY=172.21.0.1

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# MongoDB Configuration
MONGO_URI=mongodb://lucid:lucid@mongodb:27017/lucid?authSource=admin&retryWrites=false&directConnection=true
MONGO_DB=lucid
MONGO_INITDB_ROOT_USERNAME=lucid
MONGO_INITDB_ROOT_PASSWORD=lucid
MONGO_INITDB_DATABASE=lucid

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=lucid-redis-password-change-in-production
REDIS_MAXMEMORY=256mb
REDIS_MAXMEMORY_POLICY=allkeys-lru

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# JWT Configuration
JWT_SECRET_KEY=lucid-jwt-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption Configuration
KEY_ENC_SECRET=lucid-key-encryption-secret-change-in-production
ENCRYPTION_KEY=lucid-encryption-key-change-in-production
ADMIN_SECRET_KEY=lucid-admin-secret-key-change-in-production

# =============================================================================
# BLOCKCHAIN CONFIGURATION
# =============================================================================

# TRON Configuration
TRON_NETWORK=shasta
TRONGRID_API_KEY=
TRON_HTTP_ENDPOINT=

# On-System Chain Configuration
RPC_URL=http://localhost:8545
CHAIN_ID=1337
PRIVATE_KEY=

# Contract Addresses (JSON format)
CONTRACT_ADDRESSES={"LucidAnchors":"","LucidChunkStore":"","PayoutRouterV0":"","PayoutRouterKYC":"","USDT_TRC20":""}

# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================

# API Services
API_HOST=0.0.0.0
ADMIN_API_PORT=8081
BLOCKCHAIN_API_PORT=8084
AUTH_API_PORT=8085
USER_MANAGER_PORT=8086

# Recording Services
RECORDING_HOST=0.0.0.0
RECORDING_PORT=8087
CHUNKER_PORT=8088
ENCRYPTOR_PORT=8089
MERKLE_PORT=8090

# Blockchain Services
CHAIN_CLIENT_PORT=8091
TRON_CLIENT_PORT=8092
DHT_NODE_PORT=8093

# RDP Services
RDP_HOST=0.0.0.0
RDP_PORT=3389
WALLET_PORT=8094
POLICY_PORT=8095

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================

# Data Storage Paths
DATA_ROOT=/data
SESSION_STORAGE_PATH=/data/sessions
CHUNK_STORAGE_PATH=/data/chunks
VAULT_STORAGE_PATH=/data/vault
POLICY_STORAGE_PATH=/data/policies
DHT_STORAGE_PATH=/data/dht

# Log Storage Paths
LOG_ROOT=/data/logs
VIOLATION_LOG_PATH=/data/logs/violations
AUDIT_LOG_PATH=/data/logs/audit

# =============================================================================
# PERFORMANCE CONFIGURATION
# =============================================================================

# Python Configuration
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app

# Node.js Configuration
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1

# Service Limits
UVICORN_WORKERS=1
MAX_CONNECTIONS=10
MAX_SESSION_DURATION_HOURS=8
SESSION_TIMEOUT=3600

# =============================================================================
# DEVELOPMENT CONFIGURATION
# =============================================================================

# Logging
LOG_LEVEL=INFO

# Debug Settings
DEBUG=false
VERBOSE=false

# Development URLs
NEXT_PUBLIC_API_URL=http://localhost:8081
NEXT_PUBLIC_WS_URL=ws://localhost:8081/ws
NEXT_PUBLIC_ADMIN_URL=http://localhost:3000
"@
    
    try {
        $outputDir = Split-Path $OutputPath
        if (-not (Test-Path $outputDir)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }
        
        $masterContent | Out-File -FilePath $OutputPath -Encoding UTF8
        Write-Success "Generated master environment file: $OutputPath"
    }
    catch {
        Write-Error "Failed to generate master environment file: $_"
        throw
    }
}

function Main {
    Write-ColorOutput "LUCID SERVICE ENVIRONMENT GENERATOR" "Magenta"
    Write-ColorOutput "Generating environment configurations for all services" "Magenta"
    Write-ColorOutput ""
    
    try {
        # Ensure output directories exist
        if ($GenerateEnv) {
            $envOutputDir = Join-Path $OutputDir "services"
            if (-not (Test-Path $envOutputDir)) {
                New-Item -ItemType Directory -Path $envOutputDir -Force | Out-Null
            }
        }
        
        if ($GenerateCompose) {
            $composeOutputDir = Join-Path $OutputDir "compose"
            if (-not (Test-Path $composeOutputDir)) {
                New-Item -ItemType Directory -Path $composeOutputDir -Force | Out-Null
            }
        }
        
        # Generate configurations for each service
        foreach ($serviceName in $ServiceEnvironments.Keys) {
            $environmentVars = $ServiceEnvironments[$serviceName]
            
            Write-ColorOutput "`n" + "-"*60 "Yellow"
            Write-Info "Processing service: $serviceName"
            
            # Generate individual environment file
            if ($GenerateEnv) {
                $envPath = Join-Path $OutputDir "services" "$serviceName.env"
                Generate-EnvironmentFile $serviceName $environmentVars $envPath
            }
            
            # Generate compose environment
            if ($GenerateCompose) {
                $composePath = Join-Path $OutputDir "compose" "$serviceName-environment.yaml"
                Generate-ComposeEnvironment $serviceName $environmentVars $composePath
            }
        }
        
        # Generate master environment file
        $masterEnvPath = Join-Path $OutputDir "lucid-master.env"
        Generate-MasterEnvironment $masterEnvPath
        
        Write-ColorOutput "`n" + "="*80 "Magenta"
        Write-Success "Environment generation completed successfully!"
        Write-Info "Generated configurations for $($ServiceEnvironments.Count) services"
        Write-Info "Output directory: $OutputDir"
        Write-ColorOutput "="*80 "Magenta"
    }
    catch {
        Write-Error "Environment generation failed: $_"
        exit 1
    }
}

# Run main function
Main
