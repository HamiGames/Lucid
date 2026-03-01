#!/bin/bash

# Lucid OpenAPI Generation Script
# Generates OpenAPI specifications and documentation for all service clusters

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCS_DIR="$PROJECT_ROOT/docs/api"
OPENAPI_DIR="$DOCS_DIR/openapi"
SCRIPTS_DIR="$PROJECT_ROOT/scripts/docs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    # Check for Node.js
    if ! command -v node &> /dev/null; then
        missing_deps+=("node")
    fi
    
    # Check for npm
    if ! command -v npm &> /dev/null; then
        missing_deps+=("npm")
    fi
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Check for pip
    if ! command -v pip3 &> /dev/null; then
        missing_deps+=("pip3")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install the missing dependencies and try again."
        exit 1
    fi
    
    log_success "All dependencies are available"
}

# Install required packages
install_packages() {
    log_info "Installing required packages..."
    
    # Install Node.js packages
    if [ -f "$PROJECT_ROOT/package.json" ]; then
        cd "$PROJECT_ROOT"
        npm install --silent
        log_success "Node.js packages installed"
    fi
    
    # Install Python packages
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        cd "$PROJECT_ROOT"
        pip3 install -r requirements.txt --quiet
        log_success "Python packages installed"
    fi
    
    # Install OpenAPI tools
    if ! command -v swagger-codegen &> /dev/null; then
        log_info "Installing swagger-codegen..."
        npm install -g swagger-codegen-cli
    fi
    
    if ! command -v redoc-cli &> /dev/null; then
        log_info "Installing redoc-cli..."
        npm install -g redoc-cli
    fi
}

# Validate OpenAPI specifications
validate_specs() {
    log_info "Validating OpenAPI specifications..."
    
    local invalid_specs=()
    
    for spec_file in "$OPENAPI_DIR"/*.yaml; do
        if [ -f "$spec_file" ]; then
            local filename=$(basename "$spec_file")
            log_info "Validating $filename..."
            
            # Use swagger-codegen to validate
            if swagger-codegen validate -i "$spec_file" > /dev/null 2>&1; then
                log_success "$filename is valid"
            else
                log_error "$filename is invalid"
                invalid_specs+=("$filename")
            fi
        fi
    done
    
    if [ ${#invalid_specs[@]} -ne 0 ]; then
        log_error "Invalid specifications found: ${invalid_specs[*]}"
        return 1
    fi
    
    log_success "All OpenAPI specifications are valid"
}

# Generate documentation
generate_docs() {
    log_info "Generating documentation..."
    
    # Create output directories
    mkdir -p "$DOCS_DIR/generated"
    mkdir -p "$DOCS_DIR/swagger-ui"
    mkdir -p "$DOCS_DIR/redoc"
    
    # Generate Swagger UI for each service
    for spec_file in "$OPENAPI_DIR"/*.yaml; do
        if [ -f "$spec_file" ]; then
            local filename=$(basename "$spec_file" .yaml)
            local service_name=$(echo "$filename" | tr '-' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')
            
            log_info "Generating Swagger UI for $service_name..."
            
            # Create service-specific Swagger UI
            mkdir -p "$DOCS_DIR/swagger-ui/$filename"
            
            # Copy Swagger UI files
            cp -r "$PROJECT_ROOT/node_modules/swagger-ui-dist"/* "$DOCS_DIR/swagger-ui/$filename/" 2>/dev/null || {
                log_warning "Swagger UI dist not found, downloading..."
                curl -sL https://github.com/swagger-api/swagger-ui/archive/v4.15.5.tar.gz | tar -xz -C /tmp
                cp -r /tmp/swagger-ui-4.15.5/dist/* "$DOCS_DIR/swagger-ui/$filename/"
            }
            
            # Create custom index.html
            cat > "$DOCS_DIR/swagger-ui/$filename/index.html" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lucid $service_name API Documentation</title>
    <link rel="stylesheet" type="text/css" href="./swagger-ui.css" />
    <link rel="icon" type="image/png" href="./favicon-32x32.png" sizes="32x32" />
    <link rel="icon" type="image/png" href="./favicon-16x16.png" sizes="16x16" />
    <style>
        html {
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }
        *, *:before, *:after {
            box-sizing: inherit;
        }
        body {
            margin:0;
            background: #fafafa;
        }
        .swagger-ui .topbar {
            background-color: #1f2937;
        }
        .swagger-ui .topbar .download-url-wrapper {
            display: none;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="./swagger-ui-bundle.js"></script>
    <script src="./swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: '../openapi/$filename.yaml',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null,
                onComplete: function() {
                    console.log('$service_name API documentation loaded');
                }
            });
        };
    </script>
</body>
</html>
EOF
            
            log_success "Swagger UI generated for $service_name"
        fi
    done
    
    # Generate ReDoc documentation
    log_info "Generating ReDoc documentation..."
    for spec_file in "$OPENAPI_DIR"/*.yaml; do
        if [ -f "$spec_file" ]; then
            local filename=$(basename "$spec_file" .yaml)
            local service_name=$(echo "$filename" | tr '-' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')
            
            log_info "Generating ReDoc for $service_name..."
            redoc-cli build "$spec_file" --output "$DOCS_DIR/redoc/$filename.html" --title "Lucid $service_name API"
            log_success "ReDoc generated for $service_name"
        fi
    done
}

# Generate client SDKs
generate_sdks() {
    log_info "Generating client SDKs..."
    
    mkdir -p "$DOCS_DIR/sdks"
    
    for spec_file in "$OPENAPI_DIR"/*.yaml; do
        if [ -f "$spec_file" ]; then
            local filename=$(basename "$spec_file" .yaml)
            local service_name=$(echo "$filename" | tr '-' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')
            
            log_info "Generating SDKs for $service_name..."
            
            # Generate JavaScript SDK
            mkdir -p "$DOCS_DIR/sdks/$filename/javascript"
            swagger-codegen generate -i "$spec_file" -l javascript -o "$DOCS_DIR/sdks/$filename/javascript" --additional-properties projectName="lucid-$filename-sdk"
            
            # Generate Python SDK
            mkdir -p "$DOCS_DIR/sdks/$filename/python"
            swagger-codegen generate -i "$spec_file" -l python -o "$DOCS_DIR/sdks/$filename/python" --additional-properties packageName="lucid_${filename}_sdk"
            
            # Generate Java SDK
            mkdir -p "$DOCS_DIR/sdks/$filename/java"
            swagger-codegen generate -i "$spec_file" -l java -o "$DOCS_DIR/sdks/$filename/java" --additional-properties groupId="org.lucid" artifactId="lucid-$filename-sdk"
            
            log_success "SDKs generated for $service_name"
        fi
    done
}

# Generate API reference
generate_api_reference() {
    log_info "Generating API reference..."
    
    # Create main index page
    cat > "$DOCS_DIR/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lucid API Documentation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f8fafc;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .header p {
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .service-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .service-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        .service-card h3 {
            margin: 0 0 10px 0;
            color: #2d3748;
            font-size: 1.3em;
        }
        .service-card p {
            margin: 0 0 15px 0;
            color: #718096;
            font-size: 0.9em;
        }
        .service-links {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .service-links a {
            display: inline-block;
            padding: 8px 16px;
            background: #4299e1;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 0.9em;
            transition: background 0.2s;
        }
        .service-links a:hover {
            background: #3182ce;
        }
        .service-links a.swagger {
            background: #85ea2d;
        }
        .service-links a.swagger:hover {
            background: #68d391;
        }
        .service-links a.redoc {
            background: #ed8936;
        }
        .service-links a.redoc:hover {
            background: #dd6b20;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            background: #2d3748;
            color: white;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Lucid API Documentation</h1>
        <p>Comprehensive API documentation for the Lucid blockchain system</p>
    </div>
    
    <div class="services-grid">
        <div class="service-card">
            <h3>API Gateway</h3>
            <p>Primary entry point for all API requests with routing and rate limiting</p>
            <div class="service-links">
                <a href="swagger-ui/api-gateway/" class="swagger">Swagger UI</a>
                <a href="redoc/api-gateway.html" class="redoc">ReDoc</a>
                <a href="openapi/api-gateway.yaml">OpenAPI Spec</a>
            </div>
        </div>
        
        <div class="service-card">
            <h3>Blockchain Core</h3>
            <p>Core blockchain operations and consensus mechanisms</p>
            <div class="service-links">
                <a href="swagger-ui/blockchain-core/" class="swagger">Swagger UI</a>
                <a href="redoc/blockchain-core.html" class="redoc">ReDoc</a>
                <a href="openapi/blockchain-core.yaml">OpenAPI Spec</a>
            </div>
        </div>
        
        <div class="service-card">
            <h3>Session Management</h3>
            <p>User session and data storage management</p>
            <div class="service-links">
                <a href="swagger-ui/session-management/" class="swagger">Swagger UI</a>
                <a href="redoc/session-management.html" class="redoc">ReDoc</a>
                <a href="openapi/session-management.yaml">OpenAPI Spec</a>
            </div>
        </div>
        
        <div class="service-card">
            <h3>RDP Services</h3>
            <p>Remote desktop protocol services</p>
            <div class="service-links">
                <a href="swagger-ui/rdp-services/" class="swagger">Swagger UI</a>
                <a href="redoc/rdp-services.html" class="redoc">ReDoc</a>
                <a href="openapi/rdp-services.yaml">OpenAPI Spec</a>
            </div>
        </div>
        
        <div class="service-card">
            <h3>Node Management</h3>
            <p>Worker node coordination and management</p>
            <div class="service-links">
                <a href="swagger-ui/node-management/" class="swagger">Swagger UI</a>
                <a href="redoc/node-management.html" class="redoc">ReDoc</a>
                <a href="openapi/node-management.yaml">OpenAPI Spec</a>
            </div>
        </div>
        
        <div class="service-card">
            <h3>Admin Interface</h3>
            <p>System administration and monitoring</p>
            <div class="service-links">
                <a href="swagger-ui/admin-interface/" class="swagger">Swagger UI</a>
                <a href="redoc/admin-interface.html" class="redoc">ReDoc</a>
                <a href="openapi/admin-interface.yaml">OpenAPI Spec</a>
            </div>
        </div>
        
        <div class="service-card">
            <h3>TRON Payment</h3>
            <p>TRON blockchain payment processing</p>
            <div class="service-links">
                <a href="swagger-ui/tron-payment/" class="swagger">Swagger UI</a>
                <a href="redoc/tron-payment.html" class="redoc">ReDoc</a>
                <a href="openapi/tron-payment.yaml">OpenAPI Spec</a>
            </div>
        </div>
        
        <div class="service-card">
            <h3>Auth Service</h3>
            <p>Authentication and authorization</p>
            <div class="service-links">
                <a href="swagger-ui/auth-service/" class="swagger">Swagger UI</a>
                <a href="redoc/auth-service.html" class="redoc">ReDoc</a>
                <a href="openapi/auth-service.yaml">OpenAPI Spec</a>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>Lucid Blockchain System API Documentation</p>
        <p>Generated on $(date)</p>
    </div>
</body>
</html>
EOF
    
    log_success "API reference generated"
}

# Clean up generated files
cleanup() {
    log_info "Cleaning up temporary files..."
    
    # Remove temporary files
    rm -rf /tmp/swagger-ui-* 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Main execution
main() {
    log_info "Starting Lucid OpenAPI generation..."
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Execute steps
    check_dependencies
    install_packages
    validate_specs
    generate_docs
    generate_sdks
    generate_api_reference
    cleanup
    
    log_success "OpenAPI generation completed successfully!"
    log_info "Documentation available at: $DOCS_DIR"
    log_info "Swagger UI available at: $DOCS_DIR/swagger-ui"
    log_info "ReDoc available at: $DOCS_DIR/redoc"
    log_info "Client SDKs available at: $DOCS_DIR/sdks"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Lucid OpenAPI Generation Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --validate     Only validate OpenAPI specifications"
        echo "  --docs         Only generate documentation"
        echo "  --sdks         Only generate client SDKs"
        echo "  --clean        Clean up generated files"
        echo ""
        echo "Examples:"
        echo "  $0                    # Generate all documentation"
        echo "  $0 --validate         # Only validate specs"
        echo "  $0 --docs             # Only generate docs"
        echo "  $0 --clean            # Clean up files"
        exit 0
        ;;
    --validate)
        check_dependencies
        validate_specs
        ;;
    --docs)
        check_dependencies
        install_packages
        validate_specs
        generate_docs
        generate_api_reference
        ;;
    --sdks)
        check_dependencies
        install_packages
        validate_specs
        generate_sdks
        ;;
    --clean)
        cleanup
        rm -rf "$DOCS_DIR/generated" "$DOCS_DIR/swagger-ui" "$DOCS_DIR/redoc" "$DOCS_DIR/sdks" "$DOCS_DIR/index.html"
        log_success "All generated files cleaned up"
        ;;
    *)
        main
        ;;
esac
