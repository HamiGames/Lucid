#!/bin/bash
# Timelock Governance Deployment Script for Linux/Pi
# This script deploys the timelock governance service on Linux/Pi

set -e

# Default values
MONGO_URI="mongodb://lucid:lucid@127.0.0.1:27019/lucid?authSource=admin"
OUTPUT_DIR="/data/timelock"
CONFIG_FILE=""
BUILD=false
TEST=false

# Function to show usage
show_usage() {
    echo "Timelock Governance Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -m, --mongo-uri URI     MongoDB connection URI"
    echo "  -o, --output-dir DIR    Output directory for timelock data"
    echo "  -c, --config FILE       Path to configuration file"
    echo "  -b, --build             Build Docker image before deployment"
    echo "  -t, --test              Run tests after deployment"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --build --test"
    echo "  $0 --mongo-uri mongodb://localhost:27017/lucid --output-dir /tmp/timelock"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mongo-uri)
            MONGO_URI="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -b|--build)
            BUILD=true
            shift
            ;;
        -t|--test)
            TEST=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

echo "Starting Timelock Governance Deployment..."

# Create output directory
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Creating output directory: $OUTPUT_DIR"
    sudo mkdir -p "$OUTPUT_DIR"
    sudo chown -R $USER:$USER "$OUTPUT_DIR"
fi

# Install Python dependencies if needed
echo "Checking Python dependencies..."
if [ -f "requirements.timelock.txt" ]; then
    echo "Installing Python dependencies..."
    pip3 install -r requirements.timelock.txt
fi

# Build Docker image if requested
if [ "$BUILD" = true ]; then
    echo "Building Docker image..."
    docker build -f Dockerfile.timelock -t lucid-timelock:latest .
    
    if [ $? -ne 0 ]; then
        echo "Docker build failed"
        exit 1
    fi
    
    echo "Docker image built successfully"
fi

# Set environment variables
export MONGO_URI="$MONGO_URI"
export LUCID_TIMELOCK_OUTPUT_DIR="$OUTPUT_DIR"

if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    export LUCID_TIMELOCK_CONFIG_FILE="$CONFIG_FILE"
fi

# Run tests if requested
if [ "$TEST" = true ]; then
    echo "Running timelock tests..."
    python3 test_timelock.py
    
    if [ $? -ne 0 ]; then
        echo "Tests failed"
        exit 1
    fi
    
    echo "All tests passed!"
fi

# Start timelock service
echo "Starting timelock governance service..."

START_ARGS=("start_timelock.py")

if [ -n "$CONFIG_FILE" ]; then
    START_ARGS+=("--config" "$CONFIG_FILE")
fi

START_ARGS+=("--output-dir" "$OUTPUT_DIR")
START_ARGS+=("--mongo-uri" "$MONGO_URI")

python3 "${START_ARGS[@]}"

echo "Timelock governance service started successfully!"
echo "Timelock Governance Deployment Complete!"
