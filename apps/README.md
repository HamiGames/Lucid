# Apps Directory

This directory contains all application modules for the Lucid RDP system as specified in Spec-1d.

## Structure

- `/admin-ui` - Next.js admin interface
- `/recorder` - Session recording daemon with ffmpeg/xrdp helpers
- `/chunker` - Data chunking service (native addon or Python)
- `/encryptor` - Encryption service using libsodium bindings
- `/merkle` - Merkle tree builder using BLAKE3 bindings
- `/chain-client` - Node.js service for On-System Data Chain interaction
- `/tron-node` - Node.js service using TronWeb for TRON network interaction
- `/walletd` - Key management service
- `/dht-node` - CRDT/DHT node for distributed data
- `/exporter` - S3-compatible backup service

## Implementation Notes

All applications are designed to run in distroless containers as specified in the distroless architecture requirements.
