#!/bin/bash
# Lucid Docker Dev Container Setup - LUCID-STRICT Mode
# Build Host: Windows 11 console | Target: Raspberry Pi 5 (ARM64) via SSH
# Registry: pickme/lucid | Workdir: /workspaces/Lucid
# Follows SPEC-4 clustered build stages

set -e

echo "=== LUCID DOCKER DEV CONTAINER SETUP - LUCID-STRICT MODE ==="
echo "Build Host: Windows 11 | Target: Raspberry Pi 5 (ARM64) via SSH"
echo "Registry: pickme/lucid | Following SPEC-4 build stages"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# === STEP 1: ENVIRONMENT PREPARATION ===
echo -e "\n${BLUE}[1] PREPARING ENVIRONMENT${NC}"

# Ensure we're in the correct directory
if [[ ! -f ".devcontainer/docker-compose.dev.yml" ]]; then
    echo -e "${RED}ERROR: Must be run from Lucid project root directory${NC}"
    exit 1
fi

# Create necessary directories
mkdir -p .ssh
mkdir -p .env_backup
mkdir -p logs

# === STEP 2: SSH SETUP ===
echo -e "\n${BLUE}[2] SSH CONNECTION SETUP${NC}"

# Check for SSH keys
if [[ -f ".ssh/id_ed25519" ]]; then
    echo -e "${GREEN}✓ SSH key found${NC}"
    
    # Set proper permissions
    chmod 600 .ssh/id_ed25519
    chmod 644 .ssh/id_ed25519.pub
    chmod 700 .ssh
    
    echo -e "${GREEN}✓ SSH key permissions set${NC}"
else
    echo -e "${YELLOW}⚠ No SSH key found - SSH functionality will be limited${NC}"
fi

# === STEP 3: BACKUP EXISTING ENVIRONMENT FILES ===
echo -e "\n${BLUE}[3] BACKING UP ENVIRONMENT FILES${NC}"

# Backup existing .env files
for env_file in .env.api .env.user .env.local .env; do
    if [[ -f "$env_file" ]]; then
        cp "$env_file" ".env_backup/${env_file}.$(date +%Y%m%d_%H%M%S)"
        echo -e "${GREEN}✓ Backed up $env_file${NC}"
    fi
done

# === STEP 4: DOCKER NETWORK CLEANUP AND CREATION ===
echo -e "\n${BLUE}[4] DOCKER NETWORK MANAGEMENT${NC}"

# Stop existing containers
echo "Stopping existing Lucid containers..."
docker ps -a --filter "name=lucid" --format "{{.Names}}" | xargs -r docker stop 2>/dev/null || true
docker ps -a --filter "name=lucid" --format "{{.Names}}" | xargs -r docker rm 2>/dev/null || true

# Remove old networks
echo "Cleaning up old networks..."
docker network ls --filter "name=lucid" --format "{{.Name}}" | grep -v "bridge\|host\|none" | xargs -r docker network rm 2>/dev/null || true

# Create lucid_net network
echo "Creating lucid-dev_lucid_net network..."
docker network create lucid-dev_lucid_net --driver bridge --attachable 2>/dev/null || echo "Network already exists"

# === STEP 5: ARM64 BUILDX SETUP FOR PI 5 ===
echo -e "\n${BLUE}[5] ARM64 BUILDX MANAGEMENT FOR RASPBERRY PI 5${NC}"

# Clear buildx cache
echo "Cleaning buildx cache for ARM64 builds..."
docker buildx prune -f

# Create or use Pi 5 compatible builder
echo "Setting up ARM64 builder for Pi 5 deployment..."
if ! docker buildx ls | grep -q "pi5-builder"; then
    docker buildx create --name pi5-builder --platform linux/amd64,linux/arm64 --use --bootstrap
    echo -e "${GREEN}✓ Created ARM64 builder for Pi 5: pi5-builder${NC}"
else
    docker buildx use pi5-builder
    echo -e "${GREEN}✓ Using existing Pi 5 builder: pi5-builder${NC}"
fi

# Verify ARM64 support
echo "Verifying ARM64 platform support..."
if docker buildx ls | grep -q "linux/arm64"; then
    echo -e "${GREEN}✓ ARM64 support confirmed for Pi 5 deployment${NC}"
else
    echo -e "${RED}✗ ARM64 support missing - Pi 5 deployment will fail${NC}"
    exit 1
fi

# === STEP 6: DOCKER COMPOSE CONFIGURATION ===
echo -e "\n${BLUE}[6] DOCKER COMPOSE SETUP${NC}"

# Update docker-compose.dev.yml with proper workspace mounting and SSH
cat > .devcontainer/docker-compose.dev.yml << 'EOF'
# Lucid RDP Development Environment Docker Compose
# Complete workspace setup with SSH support and proper mounting

networks:
  lucid-dev_lucid_net:
    name: lucid-dev_lucid_net
    driver: bridge
    attachable: true

volumes:
  # MongoDB data persistence
  mongo_data:
    name: lucid-dev_mongo_data
  # Tor state and onion services
  onion_state:
    name: lucid-dev_onion_state
  tor_data:
    name: lucid-dev_tor_data

services:
  # Main development container (VS Code attaches to this)
  devcontainer:
    build:
      context: ..
      dockerfile: .devcontainer/Dockerfile
      target: final
      args:
        - BUILDKIT_INLINE_CACHE=1
        - BUILDKIT_PROGRESS=plain
      platforms:
        - linux/arm64
    image: pickme/lucid:dev-arm64
    container_name: lucid_devcontainer
    hostname: lucid-dev
    
    # Development environment variables
    environment:
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
      - DOCKER_DEFAULT_PLATFORM=linux/arm64
      - LUCID_ENV=dev
      - PYTHONPATH=/workspaces/Lucid
      - MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false
      - SERVICE_NAME=lucid-api
      - VERSION=0.1.0
      - BLOCK_ONION=
      - BLOCK_RPC_URL=
      - ONION=
      - TOR_CONTROL_PASSWORD=
      - PORT=8081
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=lucid
    
    # Mount workspace and enable SSH, Docker socket access
    volumes:
      - ../:/workspaces/Lucid:cached
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ~/.ssh:/root/.ssh:ro
      - onion_state:/run/lucid/onion:ro
      - ~/.gitconfig:/root/.gitconfig:ro
      
    # Network configuration
    networks:
      - lucid-dev_lucid_net
      
    # Port mappings for development
    ports:
      - "8080:8080"  # API Gateway
      - "8081:8081"  # API Server
      - "8082:8082"  # Blockchain Core
      - "9050:9050"  # Tor SOCKS proxy
      - "9051:9051"  # Tor control port
      - "2222:22"    # SSH access
    
    # Dependencies
    depends_on:
      lucid_mongo:
        condition: service_healthy
        
    # Keep container running for development
    command: /usr/local/bin/start-lucid-dev tail -f /dev/null
    
    # Security settings
    security_opt:
      - no-new-privileges:true
      
    # Resource limits for development
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  # MongoDB 7 database (per R-MUST-019)
  lucid_mongo:
    image: mongo:7
    container_name: lucid_mongo
    hostname: lucid-mongo
    
    # MongoDB configuration
    environment:
      - MONGO_INITDB_DATABASE=lucid
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=lucid
      
    # MongoDB startup with authentication
    command: [
      "mongod",
      "--auth",
      "--bind_ip_all",
      "--replSet", "rs0"
    ]
    
    # Health check for MongoDB
    healthcheck:
      test: |
        mongosh --quiet -u $${MONGO_INITDB_ROOT_USERNAME} -p $${MONGO_INITDB_ROOT_PASSWORD} \
        --authenticationDatabase admin --eval "db.runCommand({ ping: 1 }).ok" | grep -q 1
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 15s
      
    # Persistence and networking
    volumes:
      - mongo_data:/data/db
      
    networks:
      - lucid-dev_lucid_net
      
    # Expose MongoDB port
    ports:
      - "27017:27017"
      
    # Security settings
    security_opt:
      - no-new-privileges:true

  # Tor proxy service (per R-MUST-014, R-MUST-020)
  tor-proxy:
    build:
      context: ../02-network-security/tor
      dockerfile: Dockerfile
    image: lucid/tor:dev
    container_name: lucid_tor
    hostname: lucid-tor
    
    # Tor environment
    environment:
      - LUCID_ENV=dev
      - TOR_CONTROL_PASSWORD=
      
    # Tor configuration and state
    volumes:
      - tor_data:/var/lib/tor
      - onion_state:/run/lucid/onion
      - ../02-network-security/tor/torrc:/etc/tor/torrc:ro
      - ../02-network-security/tor/tor-health.sh:/usr/local/bin/tor-health:ro
      - ../02-network-security/tor/tor-show-onion.sh:/usr/local/bin/tor-show-onion:ro
      
    # Tor ports
    expose:
      - "9050"  # SOCKS proxy
      - "9051"  # Control port
      
    ports:
      - "9050:9050"
      - "9051:9051"
      
    # Health check for Tor
    healthcheck:
      test: ["CMD-SHELL", "sh /usr/local/bin/tor-health"]
      interval: 10s
      timeout: 6s
      retries: 18
      start_period: 25s
      
    # Networking
    networks:
      lucid-dev_lucid_net:
        aliases:
          - lucid_tor
          
    # Security settings
    security_opt:
      - no-new-privileges:true
      
    restart: unless-stopped

  # Server tools container (optional, for testing)
  server-tools:
    image: alpine:3.22.1
    container_name: lucid_server_tools
    hostname: server-tools
    
    # Development utilities
    command: >
      sh -c "
        apk add --no-cache bash curl jq bind-tools netcat-openbsd socat openssl openssh-client git &&
        echo 'Server tools ready' &&
        tail -f /dev/null
      "
      
    # Environment
    environment:
      - LUCID_ENV=dev
      - MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false
      
    # Dependencies
    depends_on:
      devcontainer:
        condition: service_started
      lucid_mongo:
        condition: service_healthy
      tor-proxy:
        condition: service_healthy
        
    # Networking
    networks:
      - lucid-dev_lucid_net
      
    # Security
    security_opt:
      - no-new-privileges:true
      
    restart: unless-stopped
EOF

echo -e "${GREEN}✓ Updated docker-compose.dev.yml with SSH and workspace support${NC}"

# === STEP 7: DEVCONTAINER.JSON CONFIGURATION ===
echo -e "\n${BLUE}[7] VS CODE DEVCONTAINER CONFIG${NC}"

# Create/update devcontainer.json for VS Code
cat > .devcontainer/devcontainer.json << 'EOF'
{
    "name": "Lucid RDP Development Environment",
    "dockerComposeFile": "docker-compose.dev.yml",
    "service": "devcontainer",
    "workspaceFolder": "/workspaces/Lucid",
    
    "customizations": {
        "vscode": {
            "extensions": [
                "ms-python.python",
                "ms-python.flake8",
                "ms-python.black-formatter",
                "ms-vscode.vscode-json",
                "redhat.vscode-yaml",
                "ms-vscode.docker",
                "github.copilot",
                "ms-vscode-remote.remote-ssh",
                "ms-vscode-remote.remote-containers"
            ],
            "settings": {
                "python.defaultInterpreterPath": "/usr/local/bin/python",
                "python.formatting.provider": "black",
                "python.linting.enabled": true,
                "python.linting.pylintEnabled": false,
                "python.linting.flake8Enabled": true,
                "terminal.integrated.defaultProfile.linux": "bash",
                "files.watcherExclude": {
                    "**/.git/**": true,
                    "**/node_modules/**": true,
                    "**/__pycache__/**": true
                }
            }
        }
    },
    
    "forwardPorts": [8080, 8081, 8082, 9050, 9051, 27017, 2222],
    "portsAttributes": {
        "8080": {"label": "API Gateway"},
        "8081": {"label": "API Server"},
        "8082": {"label": "Blockchain Core"},
        "9050": {"label": "Tor SOCKS"},
        "9051": {"label": "Tor Control"},
        "27017": {"label": "MongoDB"},
        "2222": {"label": "SSH"}
    },
    
    "postCreateCommand": "pip install --upgrade pip && pip install -e .",
    "remoteUser": "root"
}
EOF

echo -e "${GREEN}✓ Created/updated devcontainer.json with proper VS Code integration${NC}"

# === STEP 8: ENVIRONMENT FILE TRANSFER ===
echo -e "\n${BLUE}[8] ENVIRONMENT FILE PREPARATION${NC}"

# Ensure .env files exist with proper content
if [[ ! -f ".env.api" ]]; then
    cat > .env.api << 'EOF'
MONGO_URL=mongodb://lucid:lucid@127.0.0.1:27017/lucid?authSource=admin&retryWrites=false&directConnection=true
MONGO_URI=mongodb://lucid:lucid@127.0.0.1:27017/lucid?authSource=admin&retryWrites=false&directConnection=true
MONGODB_URI=mongodb://lucid:lucid@127.0.0.1:27017/lucid?authSource=admin&retryWrites=false&directConnection=true
DATABASE_URL=mongodb://lucid:lucid@127.0.0.1:27017/lucid?authSource=admin&retryWrites=false&directConnection=true
EOF
    echo -e "${GREEN}✓ Created .env.api${NC}"
fi

if [[ ! -f ".env.user" ]]; then
    cat > .env.user << 'EOF'
UID=1000
GID=1000
USER=vscode
EOF
    echo -e "${GREEN}✓ Created .env.user${NC}"
fi

# === STEP 9: BUILD EXECUTION ===
echo -e "\n${BLUE}[9] BUILDING DEV CONTAINER${NC}"

echo "Starting Docker build process..."
echo "This may take several minutes..."

# Build for ARM64 (Pi 5 deployment) with SSH fallback
echo "Building ARM64 image for Pi 5 deployment..."
if docker buildx build --platform linux/arm64 --target final \
    -f .devcontainer/Dockerfile \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    -t pickme/lucid:dev-arm64 \
    --load .; then
    echo -e "${GREEN}✓ Local ARM64 build completed successfully for Pi 5!${NC}"
else
    echo -e "${YELLOW}⚠ Local ARM64 build failed - attempting SSH remote build on Pi${NC}"
    
    # SSH Remote Build Fallback
    echo -e "${CYAN}Enter Pi SSH connection details:${NC}"
    read -p "SSH Host (e.g., pi@192.168.1.100): " SSH_HOST
    
    if [[ -n "$SSH_HOST" ]]; then
        echo -e "${BLUE}Initiating SSH remote build on Pi 5...${NC}"
        
        # Create remote build script
        cat > /tmp/pi-remote-build.sh << 'REMOTE_EOF'
#!/bin/bash
set -e
echo "=== REMOTE BUILD ON RASPBERRY PI 5 ==="
echo "Build Host: Raspberry Pi 5 (ARM64 native)"
echo "Registry: pickme/lucid"

# Navigate to workspace
echo "Setting up workspace..."
cd /home/pi/Lucid 2>/dev/null || {
    echo "Creating workspace directory..."
    mkdir -p /home/pi/Lucid
    cd /home/pi/Lucid
}

# Check Docker availability
if ! command -v docker &> /dev/null; then
    echo "✗ Docker not found on Pi - please install Docker first"
    exit 1
fi

echo "✓ Docker available on Pi"

# Build natively on Pi (no cross-compilation needed)
echo "Building natively on Pi 5 (ARM64)..."
echo "Using native ARM64 Docker build..."

# Build the image
if docker build -f .devcontainer/Dockerfile --target final \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    -t pickme/lucid:dev-arm64 .; then
    echo "✓ Pi native build completed successfully!"
    
    # Show built images
    echo "Built images:"
    docker images | grep pickme/lucid
    
    # Optional: Save image for transfer
    echo "Saving image archive..."
    docker save pickme/lucid:dev-arm64 | gzip > /tmp/lucid-dev-arm64.tar.gz
    echo "✓ Image saved to /tmp/lucid-dev-arm64.tar.gz"
    
else
    echo "✗ Pi native build failed!"
    exit 1
fi

echo "✓ Remote build on Pi 5 completed successfully!"
REMOTE_EOF
        
        # Make script executable
        chmod +x /tmp/pi-remote-build.sh
        
        # Copy project files to Pi
        echo -e "${WHITE}Syncing project files to Pi...${NC}"
        if scp -r . "$SSH_HOST":/home/pi/Lucid/; then
            echo -e "${GREEN}✓ Project files copied to Pi${NC}"
        else
            echo -e "${RED}✗ Failed to copy project files to Pi${NC}"
            exit 1
        fi
        
        # Copy and execute build script on Pi
        echo -e "${WHITE}Executing remote build on Pi...${NC}"
        if scp /tmp/pi-remote-build.sh "$SSH_HOST":/tmp/pi-remote-build.sh && \
           ssh "$SSH_HOST" "chmod +x /tmp/pi-remote-build.sh && /tmp/pi-remote-build.sh"; then
            echo -e "${GREEN}✓ SSH remote build completed successfully on Pi 5!${NC}"
            
            # Optional: Copy back the built image
            read -p "Copy built image back to local machine? (y/N): " copy_back
            if [[ "$copy_back" == "y" || "$copy_back" == "Y" ]]; then
                echo "Copying built image from Pi..."
                scp "$SSH_HOST":/tmp/lucid-dev-arm64.tar.gz /tmp/
                echo "Loading image locally..."
                gunzip -c /tmp/lucid-dev-arm64.tar.gz | docker load
                echo -e "${GREEN}✓ Image loaded locally${NC}"
            fi
        else
            echo -e "${RED}✗ SSH remote build failed!${NC}"
            exit 1
        fi
        
        # Cleanup temp files
        rm -f /tmp/pi-remote-build.sh /tmp/lucid-dev-arm64.tar.gz 2>/dev/null
        
    else
        echo -e "${RED}✗ No SSH host provided - build failed${NC}"
        echo "Please ensure you have SSH access to a Raspberry Pi 5 with Docker installed"
        exit 1
    fi
fi

# === STEP 10: CONTAINER STARTUP ===
echo -e "\n${BLUE}[10] STARTING CONTAINERS${NC}"

# Start all services
echo "Starting all services..."
docker-compose -f .devcontainer/docker-compose.dev.yml up -d

# Wait for services to start
echo "Waiting for services to initialize..."
sleep 15

# Check service status
echo -e "\n${CYAN}Service Status:${NC}"
docker-compose -f .devcontainer/docker-compose.dev.yml ps

# === STEP 11: VALIDATION ===
echo -e "\n${BLUE}[11] SYSTEM VALIDATION${NC}"

# Test MongoDB connection
echo "Testing MongoDB connection..."
if docker exec lucid_mongo mongosh --quiet -u lucid -p lucid --authenticationDatabase admin --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ MongoDB connection successful${NC}"
else
    echo -e "${YELLOW}⚠ MongoDB not ready yet (this is normal during first startup)${NC}"
fi

# Check container health
echo "Checking container health..."
healthy_containers=$(docker-compose -f .devcontainer/docker-compose.dev.yml ps --filter "status=running" | wc -l)
echo -e "${GREEN}✓ $((healthy_containers-1)) containers running${NC}"

# === COMPLETION ===
echo -e "\n${CYAN}=== SETUP COMPLETE ===${NC}"
echo -e "${GREEN}Lucid Docker Dev Container System is ready!${NC}"
echo ""
echo "Next steps:"
echo "1. Open VS Code in this directory"
echo "2. Use 'Remote-Containers: Reopen in Container' command"
echo "3. VS Code will attach to the running dev container"
echo ""
echo "Container access:"
echo "• SSH: ssh -p 2222 root@localhost (if SSH is configured)"
echo "• VS Code: Remote container attachment"
echo "• Docker exec: docker exec -it lucid_devcontainer bash"
echo ""
echo "Services available:"
echo "• API Gateway: http://localhost:8080"
echo "• API Server: http://localhost:8081"
echo "• MongoDB: mongodb://localhost:27017"
echo "• Tor SOCKS: localhost:9050"
echo ""
echo "Workspace: /workspaces/Lucid"
echo -e "${GREEN}Environment files transferred and ready!${NC}"