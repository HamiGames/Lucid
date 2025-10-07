# LUCID STAGE 1 - BLOCKCHAIN GROUP PI DEPLOYMENT
# Target: pickme@192.168.0.75
# Path: /mnt/myssd/Lucid
# Generated: 2025-10-05 06:20:23 UTC

# SSH to Pi
ssh pickme@192.168.0.75

# Navigate to project
cd /mnt/myssd/Lucid

# Pull latest changes
git pull origin main

# Pull Stage 1 Blockchain Group images
docker pull pickme/lucid:blockchain-core
docker pull pickme/lucid:blockchain-ledger
docker pull pickme/lucid:blockchain-vm
docker pull pickme/lucid:blockchain-sessions-data
docker pull pickme/lucid:blockchain-governance
# Start Stage 1 services with profile
docker-compose -f infrastructure/compose/lucid-dev.yaml --profile blockchain up -d

# Verify blockchain services
docker ps --filter "label=org.lucid.stage=1" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health check Stage 1 services
docker exec blockchain-core curl -f http://localhost:8080/health || echo 'blockchain-core health check failed'
docker exec blockchain-ledger curl -f http://localhost:8080/health || echo 'blockchain-ledger health check failed'
docker exec blockchain-virtual-machine curl -f http://localhost:8080/health || echo 'blockchain-virtual-machine health check failed'
docker exec blockchain-sessions-data curl -f http://localhost:8080/health || echo 'blockchain-sessions-data health check failed'
docker exec blockchain-governances curl -f http://localhost:8080/health || echo 'blockchain-governances health check failed'
# Check blockchain consensus status
docker logs blockchain-core --tail=50

# Verify governance hooks
docker logs blockchain-governances --tail=20

# Exit SSH
exit
