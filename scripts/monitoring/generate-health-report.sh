#!/bin/bash
# Health Report Generation Script
# LUCID-STRICT Layer 2 Monitoring
# Purpose: Generate detailed health report for system diagnostics
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
REPORT_DIR="${HEALTH_REPORT_DIR:-/data/reports/health}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/health-report.log}"
COMPOSE_FILE="${LUCID_COMPOSE_FILE:-/opt/lucid/docker-compose.yml}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lucid}"
MONGO_USER="${MONGO_USER:-lucid}"
MONGO_PASS="${MONGO_PASS:-lucid}"
TRON_NODE_URL="${TRON_NODE_URL:-https://api.shasta.trongrid.io}"
REPORT_FORMAT="${REPORT_FORMAT:-html}" # html, json, txt, pdf
REPORT_RETENTION_DAYS="${REPORT_RETENTION_DAYS:-30}"

# Service definitions
SERVICES=(
    "lucid_mongo"
    "tor-proxy"
    "lucid_api"
    "api-gateway"
    "lucid-blockchain"
    "lucid-recording"
    "lucid-storage"
    "lucid-gui"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${1}" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

# Create directories if they don't exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$REPORT_DIR"

echo "========================================"
log_info "📊 LUCID Health Report Generator"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Generate detailed health report for system diagnostics"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -f, --format FORMAT     Report format (html,json,txt,pdf) (default: html)"
    echo "  -o, --output FILE       Output file path"
    echo "  -d, --directory DIR     Report directory (default: $REPORT_DIR)"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -c, --compress          Compress report files"
    echo "  -e, --email ADDRESS     Email report to address"
    echo "  -s, --schedule          Schedule regular report generation"
    echo "  -l, --list              List existing reports"
    echo "  -r, --retention DAYS    Set report retention in days (default: 30)"
    echo "  --include-logs          Include service logs in report"
    echo "  --include-metrics       Include detailed metrics in report"
    echo "  --include-network       Include network diagnostics in report"
    echo "  --include-security      Include security audit in report"
    echo ""
    echo "Environment Variables:"
    echo "  HEALTH_REPORT_DIR       Health report directory (default: /data/reports/health)"
    echo "  REPORT_FORMAT           Default report format (default: html)"
    echo "  REPORT_RETENTION_DAYS   Report retention period (default: 30)"
    echo "  LUCID_COMPOSE_FILE      Docker compose file path"
    echo "  MONGO_HOST              MongoDB host (default: localhost)"
    echo "  TRON_NODE_URL           TRON node URL for blockchain checks"
    echo ""
    echo "Examples:"
    echo "  $0 --format html --compress  Generate compressed HTML report"
    echo "  $0 --format json --output /tmp/health.json  Generate JSON report"
    echo "  $0 --email admin@example.com  Email report"
    echo "  $0 --schedule               Schedule daily reports"
    echo "  $0 --list                   List existing reports"
}

# Parse command line arguments
OUTPUT_FILE=""
VERBOSE=false
COMPRESS=false
EMAIL_ADDRESS=""
SCHEDULE=false
LIST_REPORTS=false
INCLUDE_LOGS=false
INCLUDE_METRICS=false
INCLUDE_NETWORK=false
INCLUDE_SECURITY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -f|--format)
            REPORT_FORMAT="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -d|--directory)
            REPORT_DIR="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--compress)
            COMPRESS=true
            shift
            ;;
        -e|--email)
            EMAIL_ADDRESS="$2"
            shift 2
            ;;
        -s|--schedule)
            SCHEDULE=true
            shift
            ;;
        -l|--list)
            LIST_REPORTS=true
            shift
            ;;
        -r|--retention)
            REPORT_RETENTION_DAYS="$2"
            shift 2
            ;;
        --include-logs)
            INCLUDE_LOGS=true
            shift
            ;;
        --include-metrics)
            INCLUDE_METRICS=true
            shift
            ;;
        --include-network)
            INCLUDE_NETWORK=true
            shift
            ;;
        --include-security)
            INCLUDE_SECURITY=true
            shift
            ;;
        -*)
            log_error "Unknown option $1"
            show_usage
            exit 1
            ;;
        *)
            log_error "Unexpected argument: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to list existing reports
list_existing_reports() {
    log_info "Existing health reports:"
    echo ""
    
    local report_files=($(find "$REPORT_DIR" -name "health-report-*" -type f | sort -r))
    
    if [[ ${#report_files[@]} -eq 0 ]]; then
        log_warning "No health reports found"
        return 0
    fi
    
    printf "%-40s %-20s %-15s %-10s %-15s\n" "REPORT FILE" "CREATED" "AGE" "SIZE" "TYPE"
    echo "--------------------------------------------------------------------------------------------------------"
    
    for report_file in "${report_files[@]}"; do
        local file_name=$(basename "$report_file")
        local created=$(stat -c %y "$report_file" 2>/dev/null || stat -f %Sm "$report_file" 2>/dev/null || echo "unknown")
        local age=$(find "$report_file" -type f -printf '%T@\n' 2>/dev/null | awk '{print int((systime() - $1) / 86400)}' || echo "unknown")
        local size=$(stat -c %s "$report_file" 2>/dev/null || stat -f %z "$report_file" 2>/dev/null || echo "unknown")
        local file_type="unknown"
        
        if [[ "$file_name" == *.html ]]; then
            file_type="HTML"
        elif [[ "$file_name" == *.json ]]; then
            file_type="JSON"
        elif [[ "$file_name" == *.txt ]]; then
            file_type="TEXT"
        elif [[ "$file_name" == *.pdf ]]; then
            file_type="PDF"
        elif [[ "$file_name" == *.gz ]]; then
            file_type="COMPRESSED"
        fi
        
        printf "%-40s %-20s %-15s %-10s %-15s\n" "$file_name" "${created% *}" "${age}d" "${size}B" "$file_type"
    done
    
    echo ""
}

# Function to collect system information
collect_system_info() {
    log_info "Collecting system information..."
    
    local sys_info=""
    
    # Basic system info
    sys_info+="System: $(uname -n)\n"
    sys_info+="OS: $(uname -o)\n"
    sys_info+="Kernel: $(uname -r)\n"
    sys_info+="Architecture: $(uname -m)\n"
    sys_info+="Uptime: $(uptime)\n"
    sys_info+="Date: $(date)\n"
    sys_info+="Lucid Version: $(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')\n\n"
    
    # CPU information
    sys_info+="CPU Information:\n"
    sys_info+="Model: $(cat /proc/cpuinfo | grep "model name" | head -1 | cut -d: -f2 | xargs)\n"
    sys_info+="Cores: $(nproc)\n"
    sys_info+="Load Average: $(uptime | awk -F'load average:' '{print $2}')\n\n"
    
    # Memory information
    sys_info+="Memory Information:\n"
    sys_info+="$(free -h)\n\n"
    
    # Disk information
    sys_info+="Disk Information:\n"
    sys_info+="$(df -h)\n\n"
    
    # Network interfaces
    sys_info+="Network Interfaces:\n"
    sys_info+="$(ip addr show | grep -E '^[0-9]+:|inet ')\n\n"
    
    echo -e "$sys_info"
}

# Function to collect service information
collect_service_info() {
    log_info "Collecting service information..."
    
    local service_info=""
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        service_info+="Docker Compose Services:\n"
        service_info+="Compose File: $COMPOSE_FILE\n\n"
        
        for service in "${SERVICES[@]}"; do
            if docker-compose -f "$COMPOSE_FILE" ps "$service" &>/dev/null; then
                local status=$(docker-compose -f "$COMPOSE_FILE" ps "$service" --format "table {{.State}}" | tail -1)
                local image=$(docker-compose -f "$COMPOSE_FILE" ps "$service" --format "table {{.Image}}" | tail -1)
                local ports=$(docker-compose -f "$COMPOSE_FILE" ps "$service" --format "table {{.Ports}}" | tail -1)
                
                service_info+="Service: $service\n"
                service_info+="  Status: $status\n"
                service_info+="  Image: $image\n"
                service_info+="  Ports: $ports\n"
                
                # Include logs if requested
                if [[ "$INCLUDE_LOGS" == "true" ]]; then
                    service_info+="  Recent Logs:\n"
                    service_info+="$(docker-compose -f "$COMPOSE_FILE" logs --tail=5 "$service" 2>/dev/null | sed 's/^/    /')\n"
                fi
                
                service_info+="\n"
            else
                service_info+="Service: $service\n"
                service_info+="  Status: Not found in compose file\n\n"
            fi
        done
    else
        service_info+="Docker Compose File: NOT FOUND\n"
        service_info+="Compose File Path: $COMPOSE_FILE\n\n"
    fi
    
    echo -e "$service_info"
}

# Function to collect MongoDB information
collect_mongodb_info() {
    log_info "Collecting MongoDB information..."
    
    local mongo_info=""
    
    # Test MongoDB connection
    local auth_string=""
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASS" ]]; then
        auth_string="-u $MONGO_USER -p $MONGO_PASS --authenticationDatabase admin"
    fi
    
    if mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string --eval "db.runCommand({ping: 1})" &>/dev/null; then
        mongo_info+="MongoDB Connection: OK\n"
        mongo_info+="Host: $MONGO_HOST:$MONGO_PORT\n"
        mongo_info+="Database: $MONGO_DB\n\n"
        
        # Get database stats
        local db_stats=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string "$MONGO_DB" --quiet --eval "db.stats()" 2>/dev/null || echo "Unable to get stats")
        mongo_info+="Database Statistics:\n"
        mongo_info+="$db_stats\n\n"
        
        # Get collection information
        local collections=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string "$MONGO_DB" --quiet --eval "db.getCollectionNames()" 2>/dev/null || echo "Unable to get collections")
        mongo_info+="Collections:\n"
        mongo_info+="$collections\n\n"
    else
        mongo_info+="MongoDB Connection: FAILED\n"
        mongo_info+="Host: $MONGO_HOST:$MONGO_PORT\n"
        mongo_info+="Database: $MONGO_DB\n\n"
    fi
    
    echo -e "$mongo_info"
}

# Function to collect network information
collect_network_info() {
    log_info "Collecting network information..."
    
    local network_info=""
    
    # Internet connectivity
    if ping -c 1 8.8.8.8 &>/dev/null; then
        network_info+="Internet Connectivity: OK\n"
    else
        network_info+="Internet Connectivity: FAILED\n"
    fi
    
    # Tor proxy status
    if nc -z localhost 9050 2>/dev/null; then
        network_info+="Tor SOCKS Proxy: OK (port 9050)\n"
    else
        network_info+="Tor SOCKS Proxy: FAILED\n"
    fi
    
    if nc -z localhost 9051 2>/dev/null; then
        network_info+="Tor Control Port: OK (port 9051)\n"
    else
        network_info+="Tor Control Port: FAILED\n"
    fi
    
    # TRON node connectivity
    if command -v curl &> /dev/null; then
        if curl -s --connect-timeout 10 "$TRON_NODE_URL/wallet/getnowblock" &>/dev/null; then
            network_info+="TRON Node: OK ($TRON_NODE_URL)\n"
        else
            network_info+="TRON Node: CONNECTION ISSUES ($TRON_NODE_URL)\n"
        fi
    else
        network_info+="TRON Node: Cannot test (curl not available)\n"
    fi
    
    network_info+="\n"
    
    # Network interfaces details
    network_info+="Network Interface Details:\n"
    network_info+="$(ip addr show)\n\n"
    
    # Routing table
    network_info+="Routing Table:\n"
    network_info+="$(ip route show)\n\n"
    
    echo -e "$network_info"
}

# Function to collect security information
collect_security_info() {
    log_info "Collecting security information..."
    
    local security_info=""
    
    # Check for security updates
    if command -v apt &> /dev/null; then
        local updates=$(apt list --upgradable 2>/dev/null | wc -l)
        security_info+="Available Updates: $updates\n"
    elif command -v yum &> /dev/null; then
        local updates=$(yum check-update --quiet 2>/dev/null | wc -l)
        security_info+="Available Updates: $updates\n"
    else
        security_info+="Package Manager: Not detected\n"
    fi
    
    # Check file permissions
    local sensitive_files=("/data/keys" "/opt/lucid" "/var/log")
    security_info+="\nFile Permissions Check:\n"
    
    for dir in "${sensitive_files[@]}"; do
        if [[ -d "$dir" ]]; then
            local perms=$(stat -c %a "$dir" 2>/dev/null || echo "unknown")
            security_info+="  $dir: $perms\n"
        else
            security_info+="  $dir: Not found\n"
        fi
    done
    
    # Check running processes
    security_info+="\nRunning Lucid Processes:\n"
    local lucid_processes=$(ps aux | grep -i lucid | grep -v grep || echo "No Lucid processes found")
    security_info+="$lucid_processes\n\n"
    
    # Check Docker security
    if command -v docker &> /dev/null; then
        security_info+="Docker Security:\n"
        local docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
        security_info+="  Version: $docker_version\n"
        
        # Check for privileged containers
        local privileged_containers=$(docker ps --filter "label=privileged=true" --format "table {{.Names}}" 2>/dev/null | tail -n +2 || echo "none")
        security_info+="  Privileged Containers: $privileged_containers\n\n"
    fi
    
    echo -e "$security_info"
}

# Function to generate HTML report
generate_html_report() {
    local report_file="$1"
    local report_timestamp=$(date +"%Y%m%d_%H%M%S")
    
    log_info "Generating HTML report..."
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lucid System Health Report - $report_timestamp</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #007acc; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .section { margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #007acc; }
        .status-ok { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-error { color: #dc3545; }
        pre { background-color: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; }
        .summary { background-color: #e3f2fd; padding: 15px; border-radius: 4px; margin: 20px 0; }
        .timestamp { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Lucid System Health Report</h1>
        <p class="timestamp">Generated: $(date)</p>
        
        <div class="summary">
            <h2>Executive Summary</h2>
            <p><strong>System:</strong> $(uname -n)</p>
            <p><strong>Lucid Version:</strong> $(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')</p>
            <p><strong>Report Generated:</strong> $(date)</p>
            <p><strong>System Uptime:</strong> $(uptime)</p>
        </div>
        
        <div class="section">
            <h2>System Information</h2>
            <pre>$(collect_system_info)</pre>
        </div>
        
        <div class="section">
            <h2>Service Status</h2>
            <pre>$(collect_service_info)</pre>
        </div>
        
        <div class="section">
            <h2>MongoDB Status</h2>
            <pre>$(collect_mongodb_info)</pre>
        </div>
EOF
    
    if [[ "$INCLUDE_NETWORK" == "true" ]]; then
        cat >> "$report_file" << EOF
        
        <div class="section">
            <h2>Network Status</h2>
            <pre>$(collect_network_info)</pre>
        </div>
EOF
    fi
    
    if [[ "$INCLUDE_SECURITY" == "true" ]]; then
        cat >> "$report_file" << EOF
        
        <div class="section">
            <h2>Security Status</h2>
            <pre>$(collect_security_info)</pre>
        </div>
EOF
    fi
    
    cat >> "$report_file" << EOF
        
        <div class="section">
            <h2>Report Metadata</h2>
            <p><strong>Report ID:</strong> $report_timestamp</p>
            <p><strong>Generated by:</strong> Lucid Health Report Generator</p>
            <p><strong>Report Format:</strong> HTML</p>
        </div>
    </div>
</body>
</html>
EOF
    
    log_success "HTML report generated: $report_file"
}

# Function to generate JSON report
generate_json_report() {
    local report_file="$1"
    local report_timestamp=$(date +"%Y%m%d_%H%M%S")
    
    log_info "Generating JSON report..."
    
    cat > "$report_file" << EOF
{
    "report_id": "$report_timestamp",
    "timestamp": "$(date -Iseconds)",
    "system": {
        "hostname": "$(uname -n)",
        "os": "$(uname -o)",
        "kernel": "$(uname -r)",
        "architecture": "$(uname -m)",
        "uptime": "$(uptime)",
        "lucid_version": "$(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')"
    },
    "system_info": "$(collect_system_info | sed 's/"/\\"/g' | tr '\n' '\\n')",
    "services": "$(collect_service_info | sed 's/"/\\"/g' | tr '\n' '\\n')",
    "mongodb": "$(collect_mongodb_info | sed 's/"/\\"/g' | tr '\n' '\\n')",
EOF
    
    if [[ "$INCLUDE_NETWORK" == "true" ]]; then
        cat >> "$report_file" << EOF
    "network": "$(collect_network_info | sed 's/"/\\"/g' | tr '\n' '\\n')",
EOF
    fi
    
    if [[ "$INCLUDE_SECURITY" == "true" ]]; then
        cat >> "$report_file" << EOF
    "security": "$(collect_security_info | sed 's/"/\\"/g' | tr '\n' '\\n')",
EOF
    fi
    
    cat >> "$report_file" << EOF
    "metadata": {
        "format": "JSON",
        "generator": "Lucid Health Report Generator",
        "includes_logs": $INCLUDE_LOGS,
        "includes_metrics": $INCLUDE_METRICS,
        "includes_network": $INCLUDE_NETWORK,
        "includes_security": $INCLUDE_SECURITY
    }
}
EOF
    
    log_success "JSON report generated: $report_file"
}

# Function to generate text report
generate_text_report() {
    local report_file="$1"
    local report_timestamp=$(date +"%Y%m%d_%H%M%S")
    
    log_info "Generating text report..."
    
    cat > "$report_file" << EOF
========================================
LUCID SYSTEM HEALTH REPORT
========================================
Report ID: $report_timestamp
Generated: $(date)
System: $(uname -n)
Lucid Version: $(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')

========================================
EXECUTIVE SUMMARY
========================================
System Uptime: $(uptime)
Report Generated: $(date)
Report Format: TEXT

========================================
SYSTEM INFORMATION
========================================
$(collect_system_info)

========================================
SERVICE STATUS
========================================
$(collect_service_info)

========================================
MONGODB STATUS
========================================
$(collect_mongodb_info)
EOF
    
    if [[ "$INCLUDE_NETWORK" == "true" ]]; then
        cat >> "$report_file" << EOF

========================================
NETWORK STATUS
========================================
$(collect_network_info)
EOF
    fi
    
    if [[ "$INCLUDE_SECURITY" == "true" ]]; then
        cat >> "$report_file" << EOF

========================================
SECURITY STATUS
========================================
$(collect_security_info)
EOF
    fi
    
    cat >> "$report_file" << EOF

========================================
REPORT METADATA
========================================
Report ID: $report_timestamp
Generated by: Lucid Health Report Generator
Report Format: TEXT
Includes Logs: $INCLUDE_LOGS
Includes Metrics: $INCLUDE_METRICS
Includes Network: $INCLUDE_NETWORK
Includes Security: $INCLUDE_SECURITY

========================================
END OF REPORT
========================================
EOF
    
    log_success "Text report generated: $report_file"
}

# Function to cleanup old reports
cleanup_old_reports() {
    log_info "Cleaning up old reports (older than $REPORT_RETENTION_DAYS days)..."
    
    local old_reports=($(find "$REPORT_DIR" -name "health-report-*" -type f -mtime +$REPORT_RETENTION_DAYS))
    
    if [[ ${#old_reports[@]} -eq 0 ]]; then
        log_info "No old reports to cleanup"
        return 0
    fi
    
    local removed=0
    for old_report in "${old_reports[@]}"; do
        if rm "$old_report"; then
            log_info "Removed old report: $(basename "$old_report")"
            ((removed++))
        else
            log_warning "Failed to remove old report: $(basename "$old_report")"
        fi
    done
    
    log_success "Cleaned up $removed old reports"
}

# Function to email report
email_report() {
    local report_file="$1"
    local email_address="$2"
    
    if [[ -z "$email_address" ]]; then
        log_error "Email address not provided"
        return 1
    fi
    
    log_info "Emailing report to: $email_address"
    
    if command -v mail &> /dev/null; then
        local subject="Lucid System Health Report - $(date +%Y%m%d-%H%M%S)"
        local body="Please find attached the Lucid system health report generated on $(date)."
        
        if [[ "$REPORT_FORMAT" == "html" ]]; then
            echo "$body" | mail -s "$subject" -a "$report_file" "$email_address"
        else
            echo "$body" | mail -s "$subject" -a "$report_file" "$email_address"
        fi
        
        log_success "Report emailed successfully"
        return 0
    else
        log_error "Mail command not available"
        return 1
    fi
}

# Function to schedule reports
schedule_reports() {
    log_info "Setting up scheduled report generation..."
    
    local cron_entry="0 6 * * * $0 --format html --compress >> $LOG_FILE 2>&1"
    
    # Check if entry already exists
    if crontab -l 2>/dev/null | grep -q "$0"; then
        log_warning "Scheduled report entry already exists"
        return 0
    fi
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
    
    if [[ $? -eq 0 ]]; then
        log_success "Scheduled report created (daily at 6 AM)"
    else
        log_error "Failed to create scheduled report"
        return 1
    fi
}

# Main function
main() {
    # Handle special operations
    if [[ "$LIST_REPORTS" == "true" ]]; then
        list_existing_reports
        return 0
    fi
    
    if [[ "$SCHEDULE" == "true" ]]; then
        schedule_reports
        return $?
    fi
    
    # Generate report filename
    local report_timestamp=$(date +"%Y%m%d_%H%M%S")
    local report_filename="health-report-$report_timestamp.$REPORT_FORMAT"
    
    if [[ -n "$OUTPUT_FILE" ]]; then
        local report_file="$OUTPUT_FILE"
    else
        local report_file="$REPORT_DIR/$report_filename"
    fi
    
    # Generate report based on format
    case "$REPORT_FORMAT" in
        "html")
            generate_html_report "$report_file"
            ;;
        "json")
            generate_json_report "$report_file"
            ;;
        "txt")
            generate_text_report "$report_file"
            ;;
        "pdf")
            log_error "PDF format not yet implemented"
            return 1
            ;;
        *)
            log_error "Unsupported report format: $REPORT_FORMAT"
            return 1
            ;;
    esac
    
    # Compress report if requested
    if [[ "$COMPRESS" == "true" ]]; then
        if gzip "$report_file"; then
            log_success "Report compressed: $report_file.gz"
            report_file="$report_file.gz"
        else
            log_warning "Failed to compress report"
        fi
    fi
    
    # Email report if requested
    if [[ -n "$EMAIL_ADDRESS" ]]; then
        email_report "$report_file" "$EMAIL_ADDRESS"
    fi
    
    # Cleanup old reports
    cleanup_old_reports
    
    log_success "Health report generation completed: $report_file"
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up..."
    # Cleanup will be handled by individual functions
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
