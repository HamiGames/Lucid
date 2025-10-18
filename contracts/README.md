# Smart Contracts

This directory contains the Solidity smart contracts for the Lucid RDP system as specified in Spec-1d and Spec-1b.

## Contracts

- `LucidAnchors.sol` - On-System Data Chain contract for session anchoring
- `PayoutRouterV0.sol` - Primary payout router contract (non-KYC)
- `PayoutRouterKYC.sol` - KYC-gated payout router contract
- `ParamRegistry.sol` - Bounded parameter registry for governance
- `Governor.sol` - Governance contract with timelock functionality

## Architecture

These contracts implement the governance and consensus mechanisms as outlined in SPEC-1B-v2-DISTROLESS.md:

- **On-System Data Chain**: LucidAnchors handles session anchoring and data storage
- **TRON Payment System**: PayoutRouter contracts handle USDT-TRC20 payouts (payment-only, isolated from blockchain consensus)
- **Governance**: Governor + ParamRegistry implement decentralized governance with timelock

## Deployment

Contracts are deployed to:
- **Testnet**: TRON Shasta for development and testing
- **Production**: TRON Mainnet for live operations

Contract addresses are baked into Docker images via build arguments during the CI/CD process.
