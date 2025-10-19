#!/bin/bash
# scripts/registry/cleanup-dockerhub.sh
# Full cleanup of pickme/lucid Docker Hub registry

set -e

echo "Starting Docker Hub registry cleanup for pickme/lucid..."

# Check if required tools are available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo "Error: curl is not installed or not in PATH"
    exit 1
fi

# Configuration
DOCKER_HUB_USERNAME="pickme"
REPOSITORY_NAME="lucid"
DOCKER_HUB_API_URL="https://hub.docker.com/v2"

# Function to get Docker Hub token
get_docker_hub_token() {
    echo "Authenticating to Docker Hub..."
    read -s -p "Enter Docker Hub password for $DOCKER_HUB_USERNAME: " DOCKER_HUB_PASSWORD
    echo
    
    TOKEN=$(curl -s -H "Content-Type: application/json" -X POST \
        -d "{\"username\": \"$DOCKER_HUB_USERNAME\", \"password\": \"$DOCKER_HUB_PASSWORD\"}" \
        https://hub.docker.com/v2/users/login/ | jq -r .token)
    
    if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
        echo "Error: Failed to authenticate to Docker Hub"
        exit 1
    fi
    
    echo "Successfully authenticated to Docker Hub"
}

# Function to list all tags for the repository
list_repository_tags() {
    echo "Listing all tags for $DOCKER_HUB_USERNAME/$REPOSITORY_NAME..."
    
    local page=1
    local all_tags=""
    
    while true; do
        local response=$(curl -s -H "Authorization: JWT $TOKEN" \
            "$DOCKER_HUB_API_URL/repositories/$DOCKER_HUB_USERNAME/$REPOSITORY_NAME/tags/?page=$page&page_size=100")
        
        local tags=$(echo "$response" | jq -r '.results[]?.name // empty')
        
        if [ -z "$tags" ]; then
            break
        fi
        
        all_tags="$all_tags$tags"$'\n'
        page=$((page + 1))
    done
    
    echo "$all_tags" | grep -v '^$'
}

# Function to delete a specific tag
delete_tag() {
    local tag=$1
    echo "Deleting tag: $tag"
    
    local response=$(curl -s -w "%{http_code}" -o /dev/null \
        -X DELETE \
        -H "Authorization: JWT $TOKEN" \
        "$DOCKER_HUB_API_URL/repositories/$DOCKER_HUB_USERNAME/$REPOSITORY_NAME/tags/$tag/")
    
    if [ "$response" = "204" ]; then
        echo "Successfully deleted tag: $tag"
    else
        echo "Failed to delete tag: $tag (HTTP: $response)"
    fi
}

# Function to clean local Docker cache
clean_local_cache() {
    echo "Cleaning local Docker cache on Windows 11..."
    docker system prune -a --volumes -f
    docker builder prune -a -f
    
    # Remove any local images for this repository
    echo "Removing local images for $DOCKER_HUB_USERNAME/$REPOSITORY_NAME..."
    docker images "$DOCKER_HUB_USERNAME/$REPOSITORY_NAME" --format "table {{.Repository}}:{{.Tag}}" | tail -n +2 | while read image; do
        if [ ! -z "$image" ]; then
            echo "Removing local image: $image"
            docker rmi "$image" 2>/dev/null || true
        fi
    done
}

# Main execution
main() {
    echo "=== Docker Hub Registry Cleanup ==="
    echo "Repository: $DOCKER_HUB_USERNAME/$REPOSITORY_NAME"
    echo
    
    # Get authentication token
    get_docker_hub_token
    
    # List current tags
    echo
    TAGS=$(list_repository_tags)
    
    if [ -z "$TAGS" ]; then
        echo "No tags found for $DOCKER_HUB_USERNAME/$REPOSITORY_NAME"
    else
        echo "Found the following tags:"
        echo "$TAGS"
        echo
        
        # Confirm deletion
        read -p "Do you want to delete all these tags? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo "Deleting all tags..."
            echo "$TAGS" | while read tag; do
                if [ ! -z "$tag" ]; then
                    delete_tag "$tag"
                fi
            done
        else
            echo "Deletion cancelled"
        fi
    fi
    
    # Clean local cache
    echo
    clean_local_cache
    
    # Verify cleanup
    echo
    echo "Verifying cleanup..."
    docker search "$DOCKER_HUB_USERNAME/$REPOSITORY_NAME" 2>/dev/null || echo "No results found (cleanup successful)"
    
    echo
    echo "Docker Hub cleanup completed successfully!"
}

# Simplified version without jq dependency
echo "=== Simplified Docker Hub Registry Cleanup ==="
echo "Repository: $DOCKER_HUB_USERNAME/$REPOSITORY_NAME"
echo
echo "Note: This script will clean local Docker cache and remove local images."
echo "For full Docker Hub cleanup, use the Docker Hub web interface:"
echo "https://hub.docker.com/r/$DOCKER_HUB_USERNAME/$REPOSITORY_NAME"
echo

# Clean local cache
clean_local_cache

# Verify cleanup
echo
echo "Verifying local cleanup..."
docker images "$DOCKER_HUB_USERNAME/$REPOSITORY_NAME" 2>/dev/null || echo "No local images found (cleanup successful)"

echo
echo "Local Docker cleanup completed successfully!"
echo "Please manually clean Docker Hub registry via web interface if needed."
