#!/bin/bash
set -e

# This script builds the Lucid DevContainer image and pushes it to DockerHub
# Run this script from the root of the Lucid repository on the Raspberry Pi 5

# Define variables
IMAGE_NAME="pickme/lucid"
IMAGE_TAG="1.0"
BUILDER_NAME="lucid_builder"

echo "===== Building and Pushing Lucid DevContainer Image ====="
echo "Image: $IMAGE_NAME:$IMAGE_TAG"
echo "Builder: $BUILDER_NAME"
echo "Platform: linux/arm64"

# Ensure the builder exists and is selected
echo "Checking if builder '$BUILDER_NAME' exists..."
if ! docker buildx ls | grep -q "$BUILDER_NAME"; then
  echo "Error: Builder '$BUILDER_NAME' does not exist."
  echo "Creating builder: $BUILDER_NAME"
  docker buildx create --name $BUILDER_NAME --use
fi

# Use the specified builder
echo "Using builder: $BUILDER_NAME"
docker buildx use "$BUILDER_NAME"

# Ensure the network exists
echo "Ensuring network 'lucid-dev_lucid_net' exists..."
docker network inspect lucid-dev_lucid_net >/dev/null 2>&1 || \
  docker network create --driver bridge --attachable lucid-dev_lucid_net

# Pre-pull the base image to ensure it's available
echo "Pre-pulling base image to avoid timeout issues..."
docker pull python:3.12-slim-bookworm

# Build the image for ARM64 platform (Raspberry Pi 5)
echo "Building image for ARM64 platform..."
docker buildx build \
  --platform linux/arm64 \
  --tag "$IMAGE_NAME:$IMAGE_TAG" \
  --file .devcontainer/Dockerfile \
  --network=host \
  --push \
  .

echo "===== Build and Push Complete ====="
echo "Image built and pushed successfully: $IMAGE_NAME:$IMAGE_TAG"
echo "You can now pull this image on your development machine."