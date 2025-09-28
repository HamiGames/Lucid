#!/bin/bash
set -e

# This script integrates lucid-dev.yaml into the Lucid DevContainer image
# Run this script from the root of the Lucid repository on the Raspberry Pi 5

# Define variables
IMAGE_NAME="pickme/lucid"
BASE_TAG="1.0"
COMPOSE_TAG="1.0-compose"
BUILDER_NAME="lucid_builder"
COMPOSE_DIR="06-orchestration-runtime/compose"
LUCID_DEV_YAML="$COMPOSE_DIR/lucid-dev.yaml"
LUCID_BLOCKCHAIN_YAML="$COMPOSE_DIR/lucid-blockchain-core.dev.yaml"

echo "===== Integrating Compose Files into DevContainer Image ====="
echo "Base Image: $IMAGE_NAME:$BASE_TAG"
echo "Target Image: $IMAGE_NAME:$COMPOSE_TAG"
echo "Builder: $BUILDER_NAME"

# Ensure the builder exists and is selected
echo "Checking if builder '$BUILDER_NAME' exists..."
if ! docker buildx ls | grep -q "$BUILDER_NAME"; then
  echo "Error: Builder '$BUILDER_NAME' does not exist."
  echo "Please create it with: docker buildx create --name $BUILDER_NAME --use"
  exit 1
fi

# Use the specified builder
echo "Using builder: $BUILDER_NAME"
docker buildx use "$BUILDER_NAME"

# Check if the compose directory exists
if [ ! -d "$COMPOSE_DIR" ]; then
  echo "Creating compose directory: $COMPOSE_DIR"
  mkdir -p "$COMPOSE_DIR"
fi

# Check if lucid-dev.yaml exists
if [ ! -f "$LUCID_DEV_YAML" ]; then
  echo "Error: $LUCID_DEV_YAML not found."
  echo "Please ensure the file exists or clone the repository first."
  exit 1
fi

# Create a temporary Dockerfile for the compose-enabled image
echo "Creating temporary Dockerfile..."
cat > .devcontainer/Dockerfile.compose << EOF
# Start with the base Lucid image
FROM $IMAGE_NAME:$BASE_TAG

# Copy the compose files
COPY $COMPOSE_DIR/ /workspaces/Lucid/$COMPOSE_DIR/

# Create a .env file template in the compose directory
RUN touch /workspaces/Lucid/$COMPOSE_DIR/.env && \
    echo "# Lucid environment variables" > /workspaces/Lucid/$COMPOSE_DIR/.env && \
    echo "ONION=" >> /workspaces/Lucid/$COMPOSE_DIR/.env && \
    echo "BLOCK_ONION=" >> /workspaces/Lucid/$COMPOSE_DIR/.env && \
    echo "TOR_CONTROL_PASSWORD=" >> /workspaces/Lucid/$COMPOSE_DIR/.env && \
    echo "MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false" >> /workspaces/Lucid/$COMPOSE_DIR/.env

# Ensure the compose directory has the right permissions
RUN chmod -R 755 /workspaces/Lucid/$COMPOSE_DIR
EOF

# Build the updated image
echo "Building updated image with compose files..."
docker buildx build \
  --platform linux/arm64 \
  --tag "$IMAGE_NAME:$COMPOSE_TAG" \
  --file .devcontainer/Dockerfile.compose \
  --push \
  .

echo "===== Integration Complete ====="
echo "Image built and pushed successfully: $IMAGE_NAME:$COMPOSE_TAG"
echo "You can now use this image in your devcontainer.json configuration"
echo "Update your devcontainer.json to use the image: $IMAGE_NAME:$COMPOSE_TAG"

# Clean up
rm .devcontainer/Dockerfile.compose