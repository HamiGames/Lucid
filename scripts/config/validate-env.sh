#!/bin/bash

# Environment Configuration Validator for Lucid RDP System
# This script validates environment configuration files for correctness and completeness

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date +'%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

print_info() {
    print_status "$BLUE" "INFO: $1"
}

print_success() {
    print_status "$GREEN" "SUCCESS: $1"
}

print_warning() {
    print_status "$YELLOW" "WARNING: $1"
}

print_error() {
    print_status "$RED" "ERROR: $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [ENV_FILE]

Environment Configuration Validator for Lucid RDP System

OPTIONS:
    -f, --file FILE         Environment file to validate
    -d, --directory DIR     Directory containing environment files
    -a, --all               Validate all environment files
    -s, --strict            Strict validation mode (fail on warnings)
    -v, --verbose           Verbose output
    --help                  Show this help message

EXAMPLES:
    $0 --file .env.production
    $0 --directory configs/environment
    $0 --all --strict
    $0 --file .env.development --verbose

EOF
}

# Required environment variables by category
declare -A REQUIRED_VARS=(
    # System Configuration
    ["PROJECT_NAME"]="string"
    ["PROJECT_VERSION"]="string"
    ["ENVIRONMENT"]="string"
    ["DEBUG"]="boolean"
    ["LOG_LEVEL"]="string"
    
    # API Gateway
    ["API_GATEWAY_HOST"]="string"
    ["API_GATEWAY_PORT"]="integer"
    ["API_RATE_LIMIT"]="integer"
    
    # Authentication
    ["JWT_SECRET"]="string"
    ["JWT_ALGORITHM"]="string"
    ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"]="integer"
    ["SESSION_TIMEOUT"]="integer"
    
    # Database
    ["MONGODB_HOST"]="string"
    ["MONGODB_PORT"]="integer"
    ["MONGODB_DATABASE"]="string"
    ["MONGODB_USERNAME"]="string"
    ["MONGODB_PASSWORD"]="string"
    ["REDIS_HOST"]="string"
    ["REDIS_PORT"]="integer"
    
    # Blockchain
    ["BLOCKCHAIN_NETWORK"]="string"
    ["BLOCKCHAIN_CONSENSUS"]="string"
    ["ANCHORING_ENABLED"]="boolean"
    
    # Security
    ["ENCRYPTION_KEY"]="string"
    ["SSL_ENABLED"]="boolean"
    ["SECURITY_HEADERS_ENABLED"]="boolean"
)

# Optional environment variables
declare -A OPTIONAL_VARS=(
    # Hardware
    ["HARDWARE_ACCELERATION"]="boolean"
    ["V4L2_ENABLED"]="boolean"
    ["GPU_ENABLED"]="boolean"
    
    # Monitoring
    ["PROMETHEUS_ENABLED"]="boolean"
    ["GRAFANA_ENABLED"]="boolean"
    ["HEALTH_CHECK_ENABLED"]="boolean"
    
    # Backup
    ["BACKUP_ENABLED"]="boolean"
    ["BACKUP_SCHEDULE"]="string"
    ["BACKUP_RETENTION_DAYS"]="integer"
    
    # Alerting
    ["ALERTING_ENABLED"]="boolean"
    ["ALERT_CPU_THRESHOLD"]="integer"
    ["ALERT_MEMORY_THRESHOLD"]="integer"
)

# Function to validate string value
validate_string() {
    local value=$1
    local var_name=$2
    
    if [ -z "$value" ]; then
        print_error "$var_name: String value cannot be empty"
        return 1
    fi
    
    # Check for common issues
    if [[ "$value" =~ ^[[:space:]]+$ ]]; then
        print_error "$var_name: String value cannot be only whitespace"
        return 1
    fi
    
    return 0
}

# Function to validate integer value
validate_integer() {
    local value=$1
    local var_name=$2
    
    if ! [[ "$value" =~ ^[0-9]+$ ]]; then
        print_error "$var_name: Value '$value' is not a valid integer"
        return 1
    fi
    
    return 0
}

# Function to validate boolean value
validate_boolean() {
    local value=$1
    local var_name=$2
    
    case "$value" in
        "true"|"false"|"True"|"False"|"TRUE"|"FALSE"|"1"|"0"|"yes"|"no"|"Yes"|"No"|"YES"|"NO")
            return 0
            ;;
        *)
            print_error "$var_name: Value '$value' is not a valid boolean"
            return 1
            ;;
    esac
}

# Function to validate port number
validate_port() {
    local value=$1
    local var_name=$2
    
    if ! validate_integer "$value" "$var_name"; then
        return 1
    fi
    
    if [ "$value" -lt 1 ] || [ "$value" -gt 65535 ]; then
        print_error "$var_name: Port number '$value' is out of valid range (1-65535)"
        return 1
    fi
    
    return 0
}

# Function to validate IP address
validate_ip() {
    local value=$1
    local var_name=$2
    
    if [[ "$value" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        local IFS='.'
        local -a ip_parts=($value)
        for part in "${ip_parts[@]}"; do
            if [ "$part" -gt 255 ]; then
                print_error "$var_name: Invalid IP address '$value'"
                return 1
            fi
        done
        return 0
    elif [[ "$value" == "localhost" ]] || [[ "$value" == "0.0.0.0" ]]; then
        return 0
    else
        print_error "$var_name: Invalid IP address format '$value'"
        return 1
    fi
}

# Function to validate URL
validate_url() {
    local value=$1
    local var_name=$2
    
    if [[ "$value" =~ ^https?:// ]]; then
        return 0
    else
        print_error "$var_name: Invalid URL format '$value'"
        return 1
    fi
}

# Function to validate secret/key
validate_secret() {
    local value=$1
    local var_name=$2
    
    if [ ${#value} -lt 16 ]; then
        print_warning "$var_name: Secret/key is shorter than recommended (16 characters)"
    fi
    
    if [[ "$value" =~ [[:space:]] ]]; then
        print_warning "$var_name: Secret/key contains whitespace characters"
    fi
    
    return 0
}

# Function to validate environment variable
validate_env_var() {
    local var_name=$1
    local value=$2
    local expected_type=$3
    
    case "$expected_type" in
        "string")
            validate_string "$value" "$var_name"
            ;;
        "integer")
            validate_integer "$value" "$var_name"
            ;;
        "boolean")
            validate_boolean "$value" "$var_name"
            ;;
        "port")
            validate_port "$value" "$var_name"
            ;;
        "ip")
            validate_ip "$value" "$var_name"
            ;;
        "url")
            validate_url "$value" "$var_name"
            ;;
        "secret")
            validate_secret "$value" "$var_name"
            ;;
        *)
            print_warning "$var_name: Unknown validation type '$expected_type'"
            ;;
    esac
}

# Function to validate environment file
validate_env_file() {
    local env_file=$1
    local strict_mode=$2
    local verbose=$3
    
    print_info "Validating environment file: $env_file"
    
    if [ ! -f "$env_file" ]; then
        print_error "Environment file not found: $env_file"
        return 1
    fi
    
    local errors=0
    local warnings=0
    local missing_required=0
    local missing_optional=0
    
    # Check required variables
    print_info "Checking required variables..."
    for var_name in "${!REQUIRED_VARS[@]}"; do
        local expected_type="${REQUIRED_VARS[$var_name]}"
        
        if grep -q "^${var_name}=" "$env_file"; then
            local value=$(grep "^${var_name}=" "$env_file" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
            
            if [ "$verbose" = true ]; then
                print_info "Validating $var_name=$value (type: $expected_type)"
            fi
            
            if ! validate_env_var "$var_name" "$value" "$expected_type"; then
                ((errors++))
            fi
            
            # Additional validations for specific variables
            case "$var_name" in
                "API_GATEWAY_PORT"|"MONGODB_PORT"|"REDIS_PORT")
                    if ! validate_port "$value" "$var_name"; then
                        ((errors++))
                    fi
                    ;;
                "API_GATEWAY_HOST"|"MONGODB_HOST"|"REDIS_HOST")
                    if [[ "$value" != "localhost" ]] && [[ "$value" != "0.0.0.0" ]]; then
                        if ! validate_ip "$value" "$var_name"; then
                            ((errors++))
                        fi
                    fi
                    ;;
                "JWT_SECRET"|"ENCRYPTION_KEY"|"MONGODB_PASSWORD")
                    if ! validate_secret "$value" "$var_name"; then
                        ((warnings++))
                    fi
                    ;;
            esac
        else
            print_error "Missing required variable: $var_name"
            ((missing_required++))
            ((errors++))
        fi
    done
    
    # Check optional variables
    print_info "Checking optional variables..."
    for var_name in "${!OPTIONAL_VARS[@]}"; do
        local expected_type="${OPTIONAL_VARS[$var_name]}"
        
        if grep -q "^${var_name}=" "$env_file"; then
            local value=$(grep "^${var_name}=" "$env_file" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
            
            if [ "$verbose" = true ]; then
                print_info "Validating optional $var_name=$value (type: $expected_type)"
            fi
            
            if ! validate_env_var "$var_name" "$value" "$expected_type"; then
                if [ "$strict_mode" = true ]; then
                    ((errors++))
                else
                    ((warnings++))
                fi
            fi
        else
            if [ "$verbose" = true ]; then
                print_info "Optional variable not set: $var_name"
            fi
            ((missing_optional++))
        fi
    done
    
    # Check for unknown variables
    print_info "Checking for unknown variables..."
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Z_]+=.*$ ]] && ! [[ "$line" =~ ^#.*$ ]]; then
            local var_name=$(echo "$line" | cut -d'=' -f1)
            
            if [[ -z "${REQUIRED_VARS[$var_name]:-}" ]] && [[ -z "${OPTIONAL_VARS[$var_name]:-}" ]]; then
                print_warning "Unknown variable: $var_name"
                ((warnings++))
            fi
        fi
    done < "$env_file"
    
    # Check for empty values
    print_info "Checking for empty values..."
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Z_]+=.*$ ]] && ! [[ "$line" =~ ^#.*$ ]]; then
            local var_name=$(echo "$line" | cut -d'=' -f1)
            local value=$(echo "$line" | cut -d'=' -f2-)
            
            if [ -z "$value" ] || [[ "$value" =~ ^[[:space:]]*$ ]]; then
                print_warning "Empty value for variable: $var_name"
                ((warnings++))
            fi
        fi
    done < "$env_file"
    
    # Check for duplicate variables
    print_info "Checking for duplicate variables..."
    local duplicates=$(grep -E '^[A-Z_]+=' "$env_file" | cut -d'=' -f1 | sort | uniq -d)
    if [ -n "$duplicates" ]; then
        print_error "Duplicate variables found: $duplicates"
        ((errors++))
    fi
    
    # Check for invalid characters in variable names
    print_info "Checking variable name format..."
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Z_]+=.*$ ]] && ! [[ "$line" =~ ^#.*$ ]]; then
            local var_name=$(echo "$line" | cut -d'=' -f1)
            
            if [[ "$var_name" =~ [^A-Z0-9_] ]]; then
                print_error "Invalid characters in variable name: $var_name"
                ((errors++))
            fi
        fi
    done < "$env_file"
    
    # Summary
    print_info "Validation summary for $env_file:"
    print_info "  Required variables: ${#REQUIRED_VARS[@]}"
    print_info "  Missing required: $missing_required"
    print_info "  Optional variables: ${#OPTIONAL_VARS[@]}"
    print_info "  Missing optional: $missing_optional"
    print_info "  Errors: $errors"
    print_info "  Warnings: $warnings"
    
    if [ $errors -gt 0 ]; then
        print_error "Validation failed with $errors errors"
        return 1
    elif [ $warnings -gt 0 ] && [ "$strict_mode" = true ]; then
        print_error "Validation failed with $warnings warnings (strict mode)"
        return 1
    elif [ $warnings -gt 0 ]; then
        print_warning "Validation completed with $warnings warnings"
        return 0
    else
        print_success "Validation completed successfully"
        return 0
    fi
}

# Function to validate all environment files
validate_all_files() {
    local directory=$1
    local strict_mode=$2
    local verbose=$3
    
    print_info "Validating all environment files in: $directory"
    
    if [ ! -d "$directory" ]; then
        print_error "Directory not found: $directory"
        return 1
    fi
    
    local total_files=0
    local passed_files=0
    local failed_files=0
    
    for env_file in "$directory"/.env* "$directory"/*.env; do
        if [ -f "$env_file" ]; then
            ((total_files++))
            print_info "Validating file: $env_file"
            
            if validate_env_file "$env_file" "$strict_mode" "$verbose"; then
                ((passed_files++))
                print_success "File validation passed: $env_file"
            else
                ((failed_files++))
                print_error "File validation failed: $env_file"
            fi
        fi
    done
    
    print_info "Validation summary:"
    print_info "  Total files: $total_files"
    print_info "  Passed: $passed_files"
    print_info "  Failed: $failed_files"
    
    if [ $failed_files -gt 0 ]; then
        print_error "Some files failed validation"
        return 1
    else
        print_success "All files passed validation"
        return 0
    fi
}

# Main execution
main() {
    # Parse command line arguments
    local env_file=""
    local directory=""
    local all_files=false
    local strict_mode=false
    local verbose=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--file)
                env_file="$2"
                shift 2
                ;;
            -d|--directory)
                directory="$2"
                shift 2
                ;;
            -a|--all)
                all_files=true
                shift
                ;;
            -s|--strict)
                strict_mode=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            -*)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                if [ -z "$env_file" ]; then
                    env_file="$1"
                else
                    print_error "Multiple files specified"
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Determine what to validate
    if [ "$all_files" = true ]; then
        if [ -z "$directory" ]; then
            directory="$PROJECT_ROOT/configs/environment"
        fi
        validate_all_files "$directory" "$strict_mode" "$verbose"
    elif [ -n "$env_file" ]; then
        validate_env_file "$env_file" "$strict_mode" "$verbose"
    elif [ -n "$directory" ]; then
        validate_all_files "$directory" "$strict_mode" "$verbose"
    else
        print_error "No file or directory specified"
        show_usage
        exit 1
    fi
}

# Run main function
main "$@"
