# LUCID Sessions Environment Variables

This document lists all environment variables used across the sessions directory, standardized with the `LUCID_` prefix for consistency and security.

## Core Session Management

### Session ID Generation

- `LUCID_SESSION_ID_ENTROPY_BITS` - Session ID entropy bits (default: 256)

- `LUCID_SESSION_EXPIRY_HOURS` - Session expiry time in hours (default: 8)

- `LUCID_SESSION_CLEANUP_HOURS` - Session cleanup interval in hours (default: 24)

### Session Orchestrator

- `LUCID_SESSION_OUTPUT_DIR` - Session output directory (default: /data/sessions)

## Chunking and Compression

### Chunker Configuration

- `LUCID_CHUNKER_OUTPUT_DIR` - Chunker output directory (default: /data/chunks)

- `LUCID_CHUNK_SIZE_MIN` - Minimum chunk size in bytes (default: 8388608 - 8MB)

- `LUCID_CHUNK_SIZE_MAX` - Maximum chunk size in bytes (default: 16777216 - 16MB)

- `LUCID_COMPRESSION_LEVEL` - Zstd compression level (default: 3)

### Chunk Manager

- `LUCID_CHUNK_MANAGER_DIR` - Chunk manager directory (default: ./data/chunks)

- `LUCID_MAX_CHUNK_SIZE` - Maximum chunk size (default: 16777216 - 16MB)

- `LUCID_CHUNK_COMPRESSION_LEVEL` - Chunk compression level (default: 3)

### Compression Engine

- `LUCID_COMPRESSION_PATH` - Compression output path (default: /data/compression)

- `LUCID_DEFAULT_COMPRESSION_LEVEL` - Default compression level (default: 3)

- `LUCID_MAX_CHUNK_SIZE` - Maximum chunk size for compression (default: 1048576 - 1MB)

- `LUCID_COMPRESSION_THRESHOLD` - Compression threshold (default: 1024 - 1KB)

## Encryption

### Session Encryptor

- `LUCID_ENCRYPTION_OUTPUT_DIR` - Encryption output directory (default: /data/encrypted)

- `LUCID_MASTER_KEY` - Master encryption key (hex format)

### Encryption Manager

- `LUCID_ENCRYPTION_MASTER_KEY` - Master encryption key (hex format)

## Merkle Tree and Blockchain

### Merkle Builder

- `LUCID_MERKLE_OUTPUT_DIR` - Merkle tree output directory (default: /data/merkle_roots)

### Blockchain Integration

- `LUCID_BLOCKCHAIN_CONFIG_PATH` - Blockchain configuration path (default: /data/blockchain)

- `LUCID_TRON_NETWORK_URL` - TRON network URL (default: https://api.trongrid.io)

- `LUCID_CONTRACT_ADDRESS` - Smart contract address

- `LUCID_PRIVATE_KEY` - Blockchain private key

- `LUCID_GAS_LIMIT` - Gas limit for transactions (default: 1000000)

- `LUCID_GAS_PRICE` - Gas price for transactions (default: 1000000)

### Manifest Management

- `LUCID_MANIFEST_DIR` - Manifest directory (default: /data/manifests)

- `LUCID_MANIFEST_PATH` - Manifest path (default: /data/manifests)

- `LUCID_MANIFEST_CHUNK_SIZE` - Manifest chunk size (default: 1048576 - 1MB)

- `LUCID_MANIFEST_SIGNATURE_ALGORITHM` - Signature algorithm (default: Ed25519)

- `LUCID_MANIFEST_HASH_ALGORITHM` - Hash algorithm (default: BLAKE3)

## Pipeline Management

### Pipeline Configuration

- `LUCID_CHUNK_SIZE_MB` - Chunk size in MB (default: 16)

- `LUCID_MAX_SESSION_SIZE_GB` - Maximum session size in GB (default: 100)

- `LUCID_ENCRYPTION_CHUNK_SIZE` - Encryption chunk size (default: 65536 - 64KB)

- `LUCID_MERKLE_BATCH_SIZE` - Merkle batch size (default: 1000)

- `LUCID_PIPELINE_COMPRESSION_LEVEL` - Pipeline compression level (default: 6)

### Storage Configuration

- `LUCID_STORAGE_ROOT` - Storage root directory (default: ./data/session_storage)

- `LUCID_TEMP_STORAGE` - Temporary storage directory (default: ./data/temp)

- `LUCID_MONGODB_URI` - MongoDB connection URI (default: mongodb://localhost:27017/lucid)

## Session Recording

### Main Recorder

- `LUCID_RECORDER_TEMP_DIR` - Recorder temporary directory (default: system temp)

- `LUCID_RECORDER_MAX_CHUNK_SIZE` - Recorder max chunk size (default: 16777216 - 16MB)

- `LUCID_RECORDER_VIDEO_CODEC` - Video codec (default: h264)

- `LUCID_RECORDER_AUDIO_ENABLED` - Audio recording enabled (default: true)

- `LUCID_RECORDER_KEYLOG_ENABLED` - Keystroke logging enabled (default: false)

### Recording Service

- `LUCID_RECORDING_PATH` - Recording output path (default: /data/recordings)

- `LUCID_FFMPEG_PATH` - FFmpeg executable path (default: /usr/bin/ffmpeg)

- `LUCID_XRDP_DISPLAY` - XRDP display (default: :10)

- `LUCID_HARDWARE_ACCELERATION` - Hardware acceleration enabled (default: true)

- `LUCID_VIDEO_CODEC` - Video codec (default: h264_v4l2m2m)

- `LUCID_AUDIO_CODEC` - Audio codec (default: opus)

- `LUCID_BITRATE` - Recording bitrate (default: 2000k)

- `LUCID_FPS` - Recording FPS (default: 30)

- `LUCID_RESOLUTION` - Recording resolution (default: 1920x1080)

### Video Capture

- `LUCID_VIDEO_CAPTURE_PATH` - Video capture path (default: /data/video_capture)

## Security and Monitoring

### Input Control

- `LUCID_INPUT_CONTROL_PATH` - Input control path (default: /data/input_control)

- `LUCID_INPUT_VALIDATION_TIMEOUT` - Input validation timeout (default: 5.0)

- `LUCID_MAX_INPUT_SIZE` - Maximum input size (default: 1048576 - 1MB)

### Policy Enforcement

- `LUCID_POLICY_PATH` - Policy configuration path (default: /data/policies)

- `LUCID_POLICY_CACHE_SIZE` - Policy cache size (default: 1000)

- `LUCID_POLICY_CACHE_TTL` - Policy cache TTL in seconds (default: 3600)

### Audit Trail

- `LUCID_AUDIT_LOG_PATH` - Audit log path (default: /var/log/lucid/audit)

- `LUCID_AUDIT_SESSIONS_PATH` - Audit sessions path (default: /var/log/lucid/sessions)

- `LUCID_AUDIT_KEYSTROKES_PATH` - Audit keystrokes path (default: /var/log/lucid/keystrokes)

- `LUCID_AUDIT_WINDOWS_PATH` - Audit windows path (default: /var/log/lucid/windows)

- `LUCID_AUDIT_RESOURCES_PATH` - Audit resources path (default: /var/log/lucid/resources)

- `LUCID_MONGODB_URL` - MongoDB URL for audit (default: mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin)

### Keystroke Monitoring

- `LUCID_KEYSTROKE_LOG_PATH` - Keystroke log path (default: /var/log/lucid/keystrokes)

- `LUCID_KEYSTROKE_CACHE_PATH` - Keystroke cache path (default: /tmp/lucid/keystrokes)

- `LUCID_KEYSTROKE_MAX_EVENTS` - Maximum keystroke events (default: 10000)

- `LUCID_KEYSTROKE_BATCH_SIZE` - Keystroke batch size (default: 100)

- `LUCID_KEYSTROKE_FLUSH_INTERVAL` - Keystroke flush interval (default: 30)

### Resource Monitoring

- `LUCID_RESOURCE_LOG_PATH` - Resource log path (default: /var/log/lucid/resources)

- `LUCID_RESOURCE_CACHE_PATH` - Resource cache path (default: /tmp/lucid/resources)

- `LUCID_RESOURCE_MONITOR_INTERVAL` - Resource monitor interval (default: 5.0)

- `LUCID_RESOURCE_MAX_EVENTS` - Maximum resource events (default: 10000)

- `LUCID_RESOURCE_BATCH_SIZE` - Resource batch size (default: 100)

### Window Focus Monitoring

- `LUCID_WINDOW_LOG_PATH` - Window log path (default: /var/log/lucid/windows)

- `LUCID_WINDOW_CACHE_PATH` - Window cache path (default: /tmp/lucid/windows)

- `LUCID_WINDOW_MONITOR_INTERVAL` - Window monitor interval (default: 1.0)

- `LUCID_WINDOW_MAX_EVENTS` - Maximum window events (default: 10000)

- `LUCID_WINDOW_BATCH_SIZE` - Window batch size (default: 100)

## Usage Notes

1. All environment variables are prefixed with `LUCID_` for consistency and to avoid conflicts with system variables.

1. Default values are provided for all variables to ensure the system can run without explicit configuration.

1. Sensitive variables like encryption keys should be set securely and not stored in plain text.

1. Path variables use forward slashes for cross-platform compatibility.

1. Boolean variables use string values ("true"/"false") and are converted internally.

1. Numeric variables are converted to appropriate types (int/float) internally.

1. All paths are created automatically if they don't exist.

## Security Considerations

- Master keys and private keys should be generated securely and stored in environment variables or secure key management systems.

- Database credentials should use proper authentication mechanisms.

- Log paths should have appropriate permissions set.

- Consider using Docker secrets or Kubernetes secrets for sensitive configuration in production environments.
