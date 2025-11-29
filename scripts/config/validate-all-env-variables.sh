#!/bin/bash
# Path: scripts/config/validate-all-env-variables.sh
# Comprehensive Environment Variables Validation Script
# Validates ALL variables from environment-variables-reference.md
# Checks for missing values, inconsistencies, and categorizes by action needed

set -euo pipefail

PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_DIR="/mnt/myssd/Lucid/Lucid/configs/environment"
REFERENCE_FILE="plan/instructions/environment-variables-reference.md"
REPORT_FILE="$ENV_DIR/env-validation-report-$(date '+%Y%m%d-%H%M%S').md"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1" >&2; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" >&2; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_detail() { echo -e "${CYAN}[DETAIL]${NC} $1" >&2; }

# =============================================================================
# DATA STRUCTURES
# =============================================================================

# Variable metadata: var_name -> "format|expected_file|description|action"
declare -A VAR_METADATA

# Variable values: "file|var_name" -> "value"
declare -A VAR_VALUES

# Variable locations: var_name -> "file1,file2,..."
declare -A VAR_LOCATIONS

# Missing variables: var_name -> "expected_file|format|action"
declare -A MISSING_VARS

# Inconsistent variables: var_name -> "file1:value1,file2:value2"
declare -A INCONSISTENT_VARS

# =============================================================================
# PARSE REFERENCE FILE
# =============================================================================

parse_reference_file() {
    log_info "Parsing environment-variables-reference.md..."
    
    local current_file=""
    local in_table=false
    local line_num=0
    local vars_parsed=0
    local total_lines=$(wc -l < "$PROJECT_ROOT/$REFERENCE_FILE" 2>/dev/null || echo "0")
    
    # Test file read
    if [[ ! -r "$PROJECT_ROOT/$REFERENCE_FILE" ]]; then
        log_error "Cannot read reference file"
        return 1
    fi
    
    log_info "Total lines to process: $total_lines"
    echo ""
    
    while IFS= read -r line || [[ -n "$line" ]]; do
        ((line_num++))
        
        # Show progress every 10 lines with percentage
        if (( line_num % 10 == 0 )) || (( line_num == 1 )); then
            local percent=$(( line_num * 100 / total_lines ))
            printf "\r${BLUE}[INFO]${NC} Processing: %3d%% (%d/%d lines) - Found %d variables..." "$percent" "$line_num" "$total_lines" "$vars_parsed" >&2
        fi
        
        # Detect file section (e.g., ### `.env.foundation` or ### `.env.foundation` (Phase 1: ...))
        if [[ "$line" =~ ^###[[:space:]]+\`\.env\.([^\`]+)\` ]]; then
            current_file=".env.${BASH_REMATCH[1]}"
            in_table=false
            printf "\n${GREEN}[INFO]${NC} Found section: $current_file (line $line_num)\n" >&2
            continue
        fi
        
        # Detect table start (header row) - more flexible pattern
        if [[ "$line" =~ ^\|.*Variable.*Name.*Format ]]; then
            in_table=true
            printf "${CYAN}[DETAIL]${NC} Table started for $current_file (line $line_num)\n" >&2
            continue
        fi
        
        # Skip table separator
        if [[ "$line" =~ ^\|[-:[:space:]]+\| ]]; then
            continue
        fi
        
        # Parse table row: | `VAR_NAME` | FORMAT | DESCRIPTION |
        # Match: | `VAR` | FORMAT | DESC | (with optional trailing content)
        if [[ "$in_table" == true && "$line" =~ ^\|[[:space:]]*\`([^\`]+)\`[[:space:]]*\|[[:space:]]*([^|]+)[[:space:]]*\|[[:space:]]*([^|]+) ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local format="${BASH_REMATCH[2]}"
            local description="${BASH_REMATCH[3]}"
            
            # Trim whitespace
            format="${format#"${format%%[![:space:]]*}"}"
            format="${format%"${format##*[![:space:]]}"}"
            description="${description#"${description%%[![:space:]]*}"}"
            description="${description%"${description##*[![:space:]]}"}"
            
            if [[ -n "$current_file" && -n "$var_name" ]]; then
                # Determine action needed
                local action="MANUAL"
                if [[ "$format" == "BASE64" ]] || [[ "$format" == "HEX" ]] || [[ "$var_name" =~ (SECRET|PASSWORD|KEY|PRIVATE) ]]; then
                    if [[ "$current_file" == ".env.secrets" ]] || [[ "$var_name" =~ (MONGODB_PASSWORD|REDIS_PASSWORD|ELASTICSEARCH_PASSWORD|JWT_SECRET|JWT_SECRET_KEY|ENCRYPTION_KEY|TOR_PASSWORD|TOR_CONTROL_PASSWORD) ]]; then
                        action="SEED"
                    else
                        action="CREATE"
                    fi
                elif [[ "$var_name" =~ (HOST|PORT|URL|URI|ONION) ]] && [[ "$current_file" != ".env.secrets" ]]; then
                    action="SEED"
                elif [[ "$var_name" =~ (TRON_PRIVATE_KEY|TRON_WALLET_ADDRESS) ]]; then
                    action="SEED"
                fi
                
                VAR_METADATA["$var_name"]="$format|$current_file|$description|$action"
                
                # Track expected files for this variable
                if [[ -z "${VAR_LOCATIONS[$var_name]:-}" ]]; then
                    VAR_LOCATIONS["$var_name"]="$current_file"
                else
                    VAR_LOCATIONS["$var_name"]="${VAR_LOCATIONS[$var_name]},$current_file"
                fi
                
                ((vars_parsed++))
                
                # Show first 10 variables parsed, then every 20th
                if [[ $vars_parsed -le 10 ]] || (( vars_parsed % 20 == 0 )); then
                    printf "${CYAN}[DETAIL]${NC}   Parsed variable #%d: $var_name -> $current_file\n" "$vars_parsed" >&2
                fi
            fi
        fi
        
        # Stop at end of table or section
        if [[ "$in_table" == true ]]; then
            if [[ "$line" =~ ^--- ]] || [[ "$line" =~ ^##[^#] ]]; then
                in_table=false
                if [[ -n "$current_file" ]]; then
                    printf "${CYAN}[DETAIL]${NC} Ended table for $current_file (line $line_num, $vars_parsed vars total)\n" >&2
                fi
                current_file=""
            fi
        fi
    done < "$PROJECT_ROOT/$REFERENCE_FILE"
    
    # Clear progress line and show final status
    printf "\r${GREEN}[SUCCESS]${NC} Parsing complete: 100%% (%d/%d lines) - Found %d variables                    \n" "$line_num" "$total_lines" "$vars_parsed" >&2
    
    if [[ $vars_parsed -eq 0 ]]; then
        log_error "No variables parsed from reference file! Check regex patterns."
        log_error "Last file section: $current_file"
        log_error "Last line processed: $line_num"
        log_error "in_table status: $in_table"
        # Show sample lines for debugging
        log_error "Sample lines from file:"
        head -n 35 "$PROJECT_ROOT/$REFERENCE_FILE" | tail -n 5 | while IFS= read -r sample_line; do
            log_error "  $sample_line"
        done
        return 1
    fi
    
    log_success "Parsed $vars_parsed variables from reference file (processed $line_num lines)"
}

# =============================================================================
# SCAN EXISTING FILES
# =============================================================================

scan_env_files() {
    echo ""
    log_info "Scanning existing .env.* files..."
    
    local files_found=0
    local vars_found=0
    local file_list=()
    
    # Collect all .env files first
    while IFS= read -r file; do
        [[ -f "$file" ]] && file_list+=("$file")
    done < <(find "$ENV_DIR" -maxdepth 1 -name ".env.*" -type f 2>/dev/null | sort)
    
    local total_files=${#file_list[@]}
    log_info "Found $total_files .env.* files to scan"
    echo ""
    
    # Process each file
    for file in "${file_list[@]}"; do
        ((files_found++))
        local file_basename=$(basename "$file")
        printf "\r${BLUE}[INFO]${NC} Scanning file %d/%d: $file_basename..." "$files_found" "$total_files" >&2
        
        # Read variables from file
        while IFS= read -r line || [[ -n "$line" ]]; do
            # Skip comments and empty lines
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "${line// /}" ]] && continue
            
            # Parse VAR_NAME=value
            if [[ "$line" =~ ^([A-Z_][A-Z0-9_]*)=(.*)$ ]]; then
                local var_name="${BASH_REMATCH[1]}"
                local value="${BASH_REMATCH[2]}"
                
                # Remove quotes
                value="${value#\"}"
                value="${value%\"}"
                value="${value#\'}"
                value="${value%\'}"
                
                # Store value
                VAR_VALUES["$file_basename|$var_name"]="$value"
                
                # Track location
                if [[ -z "${VAR_LOCATIONS[$var_name]:-}" ]]; then
                    VAR_LOCATIONS["$var_name"]="$file_basename"
                elif [[ ! "${VAR_LOCATIONS[$var_name]}" =~ $file_basename ]]; then
                    VAR_LOCATIONS["$var_name"]="${VAR_LOCATIONS[$var_name]},$file_basename"
                fi
                
                ((vars_found++))
            fi
        done < "$file"
    done
    
    printf "\r${GREEN}[SUCCESS]${NC} Scanned $files_found files, found $vars_found variable definitions                    \n" >&2
    echo ""
}

# =============================================================================
# VALIDATE VARIABLES
# =============================================================================

validate_variables() {
    echo ""
    log_info "Validating variables against reference..."
    
    local missing_count=0
    local found_count=0
    local empty_count=0
    local total_vars=${#VAR_METADATA[@]}
    local processed=0
    
    log_info "Validating $total_vars variables..."
    echo ""
    
    for var_name in "${!VAR_METADATA[@]}"; do
        ((processed++))
        
        # Show progress every 10 variables or at milestones
        if (( processed % 10 == 0 )) || (( processed == 1 )) || (( processed == total_vars )); then
            local percent=$(( processed * 100 / total_vars ))
            printf "\r${BLUE}[INFO]${NC} Validating: %3d%% (%d/%d variables) - Found: %d, Missing: %d..." "$percent" "$processed" "$total_vars" "$found_count" "$missing_count" >&2
        fi
        local metadata="${VAR_METADATA[$var_name]}"
        local format=$(echo "$metadata" | cut -d'|' -f1)
        local expected_file=$(echo "$metadata" | cut -d'|' -f2)
        local description=$(echo "$metadata" | cut -d'|' -f3)
        local action=$(echo "$metadata" | cut -d'|' -f4)
        
        # Check if variable exists in expected file
        local key="$expected_file|$var_name"
        local value="${VAR_VALUES[$key]:-}"
        
        if [[ -z "$value" ]]; then
            # Check if it exists in any file
            local found_in=""
            for file_key in "${!VAR_VALUES[@]}"; do
                if [[ "$file_key" =~ \|$var_name$ ]]; then
                    found_in=$(echo "$file_key" | cut -d'|' -f1)
                    break
                fi
            done
            
            if [[ -n "$found_in" ]]; then
                # Variable exists but in wrong file
                MISSING_VARS["$var_name"]="$expected_file|$format|$action|WRONG_FILE:$found_in"
            else
                # Variable completely missing
                MISSING_VARS["$var_name"]="$expected_file|$format|$action|MISSING"
            fi
            ((missing_count++))
        elif [[ -z "${value// /}" ]]; then
            # Variable exists but is empty
            MISSING_VARS["$var_name"]="$expected_file|$format|$action|EMPTY"
            ((empty_count++))
        else
            ((found_count++))
        fi
    done
    
    printf "\r${GREEN}[SUCCESS]${NC} Validation complete: 100%% (%d/%d variables) - Found: %d, Missing: %d, Empty: %d                    \n" "$processed" "$total_vars" "$found_count" "$missing_count" "$empty_count" >&2
    echo ""
}

# =============================================================================
# CHECK CONSISTENCY
# =============================================================================

check_consistency() {
    echo ""
    log_info "Checking for value inconsistencies across files..."
    
    local inconsistent_count=0
    local total_values=${#VAR_VALUES[@]}
    local processed=0
    
    log_info "Checking $total_values variable values for consistency..."
    echo ""
    
    # Group variables by name
    declare -A var_files
    for key in "${!VAR_VALUES[@]}"; do
        ((processed++))
        
        # Show progress every 50 values
        if (( processed % 50 == 0 )) || (( processed == 1 )); then
            local percent=$(( processed * 100 / total_values ))
            printf "\r${BLUE}[INFO]${NC} Checking consistency: %3d%% (%d/%d values) - Inconsistencies: %d..." "$percent" "$processed" "$total_values" "$inconsistent_count" >&2
        fi
        local var_name=$(echo "$key" | cut -d'|' -f2)
        local file=$(echo "$key" | cut -d'|' -f1)
        
        if [[ -z "${var_files[$var_name]:-}" ]]; then
            var_files["$var_name"]="$file"
        else
            var_files["$var_name"]="${var_files[$var_name]},$file"
        fi
    done
    
    # Check for same variable in multiple files
    for var_name in "${!var_files[@]}"; do
        local files="${var_files[$var_name]}"
        local file_count=$(echo "$files" | tr ',' '\n' | wc -l)
        
        if [[ $file_count -gt 1 ]]; then
            # Variable exists in multiple files - check if values match
            local first_value=""
            local first_file=""
            local conflicts=""
            
            for file in $(echo "$files" | tr ',' ' '); do
                local key="$file|$var_name"
                local value="${VAR_VALUES[$key]:-}"
                
                if [[ -z "$first_value" ]]; then
                    first_value="$value"
                    first_file="$file"
                elif [[ "$value" != "$first_value" ]]; then
                    if [[ -z "$conflicts" ]]; then
                        conflicts="$first_file:$first_value"
                    fi
                    conflicts="$conflicts,$file:$value"
                fi
            done
            
            if [[ -n "$conflicts" ]]; then
                INCONSISTENT_VARS["$var_name"]="$conflicts"
                ((inconsistent_count++))
            fi
        fi
    done
    
    printf "\r${GREEN}[SUCCESS]${NC} Consistency check complete: 100%% (%d/%d values checked)                    \n" "$processed" "$total_values" >&2
    
    if [[ $inconsistent_count -gt 0 ]]; then
        log_warning "Found $inconsistent_count variables with inconsistent values across files"
    else
        log_success "All variables are consistent across files"
    fi
    echo ""
}

# =============================================================================
# CATEGORIZE BY ACTION
# =============================================================================

categorize_by_action() {
    echo ""
    log_info "Categorizing missing variables by required action..."
    
    declare -A create_vars
    declare -A seed_vars
    declare -A manual_vars
    declare -A wrong_file_vars
    declare -A empty_vars
    
    local total_missing=${#MISSING_VARS[@]}
    local processed=0
    
    if [[ $total_missing -gt 0 ]]; then
        log_info "Categorizing $total_missing missing variables..."
        echo ""
    fi
    
    for var_name in "${!MISSING_VARS[@]}"; do
        ((processed++))
        
        # Show progress every 10 or at milestones
        if [[ $total_missing -gt 0 ]] && (( processed % 10 == 0 || processed == 1 || processed == total_missing )); then
            local percent=$(( processed * 100 / total_missing ))
            printf "\r${BLUE}[INFO]${NC} Categorizing: %3d%% (%d/%d variables)..." "$percent" "$processed" "$total_missing" >&2
        fi
        local info="${MISSING_VARS[$var_name]}"
        local expected_file=$(echo "$info" | cut -d'|' -f1)
        local format=$(echo "$info" | cut -d'|' -f2)
        local action=$(echo "$info" | cut -d'|' -f3)
        local status=$(echo "$info" | cut -d'|' -f4)
        
        case "$status" in
            WRONG_FILE:*)
                wrong_file_vars["$var_name"]="$info"
                ;;
            EMPTY)
                empty_vars["$var_name"]="$info"
                ;;
            MISSING)
                case "$action" in
                    CREATE)
                        create_vars["$var_name"]="$info"
                        ;;
                    SEED)
                        seed_vars["$var_name"]="$info"
                        ;;
                    MANUAL)
                        manual_vars["$var_name"]="$info"
                        ;;
                esac
                ;;
        esac
    done
    
    # Store categorized results
    CATEGORIZED_CREATE=("${!create_vars[@]}")
    CATEGORIZED_SEED=("${!seed_vars[@]}")
    CATEGORIZED_MANUAL=("${!manual_vars[@]}")
    CATEGORIZED_WRONG_FILE=("${!wrong_file_vars[@]}")
    CATEGORIZED_EMPTY=("${!empty_vars[@]}")
    
    if [[ $total_missing -gt 0 ]]; then
        printf "\r${GREEN}[SUCCESS]${NC} Categorization complete: 100%% (%d/%d variables)                    \n" "$processed" "$total_missing" >&2
    else
        log_success "No missing variables to categorize"
    fi
    echo ""
}

# =============================================================================
# GENERATE REPORT
# =============================================================================

generate_report() {
    echo ""
    log_info "Generating validation report..."
    
    local total_vars=${#VAR_METADATA[@]}
    local processed=0
    
    {
        echo "# Environment Variables Validation Report"
        echo ""
        echo "**Generated:** $(date '+%Y-%m-%d %H:%M:%S')"
        echo "**Project Root:** $PROJECT_ROOT"
        echo "**Environment Directory:** $ENV_DIR"
        echo ""
        echo "---"
        echo ""
        echo "## Summary"
        echo ""
        echo "| Category | Count |"
        echo "|----------|-------|"
        echo "| Total Variables (Reference) | $(echo "${!VAR_METADATA[@]}" | wc -w) |"
        echo "| Variables Found | $((${#VAR_METADATA[@]} - ${#MISSING_VARS[@]})) |"
        echo "| Variables Missing | ${#MISSING_VARS[@]} |"
        echo "| Variables Inconsistent | ${#INCONSISTENT_VARS[@]} |"
        echo "| Need CREATE | ${#CATEGORIZED_CREATE[@]} |"
        echo "| Need SEED | ${#CATEGORIZED_SEED[@]} |"
        echo "| Need MANUAL | ${#CATEGORIZED_MANUAL[@]} |"
        echo "| Wrong File | ${#CATEGORIZED_WRONG_FILE[@]} |"
        echo "| Empty Values | ${#CATEGORIZED_EMPTY[@]} |"
        echo ""
        echo "---"
        echo ""
        echo "## Variables Requiring CREATE (Generate)"
        echo ""
        if [[ ${#CATEGORIZED_CREATE[@]} -eq 0 ]]; then
            echo "*None*"
        else
            echo "| Variable | Expected File | Format | Description |"
            echo "|----------|---------------|--------|-------------|"
            for var_name in "${CATEGORIZED_CREATE[@]}"; do
                local metadata="${VAR_METADATA[$var_name]}"
                local format=$(echo "$metadata" | cut -d'|' -f1)
                local expected_file=$(echo "$metadata" | cut -d'|' -f2)
                local description=$(echo "$metadata" | cut -d'|' -f3)
                echo "| \`$var_name\` | \`$expected_file\` | $format | $description |"
            done
        fi
        echo ""
        echo "---"
        echo ""
        echo "## Variables Requiring SEED (Pull from Source)"
        echo ""
        if [[ ${#CATEGORIZED_SEED[@]} -eq 0 ]]; then
            echo "*None*"
        else
            echo "| Variable | Expected File | Format | Source File | Description |"
            echo "|----------|---------------|--------|-------------|-------------|"
            for var_name in "${CATEGORIZED_SEED[@]}"; do
                local metadata="${VAR_METADATA[$var_name]}"
                local format=$(echo "$metadata" | cut -d'|' -f1)
                local expected_file=$(echo "$metadata" | cut -d'|' -f2)
                local description=$(echo "$metadata" | cut -d'|' -f3)
                
                # Determine source file
                local source_file=".env.foundation"
                if [[ "$var_name" =~ (SECRET|PASSWORD|KEY) ]] && [[ "$expected_file" != ".env.secrets" ]]; then
                    source_file=".env.secrets"
                elif [[ "$var_name" =~ (TRON_) ]]; then
                    source_file=".env.support"
                elif [[ "$var_name" =~ (BLOCKCHAIN_) ]]; then
                    source_file=".env.core"
                elif [[ "$var_name" =~ (SESSION_) ]]; then
                    source_file=".env.application"
                fi
                
                echo "| \`$var_name\` | \`$expected_file\` | $format | \`$source_file\` | $description |"
            done
        fi
        echo ""
        echo "---"
        echo ""
        echo "## Variables Requiring MANUAL Entry"
        echo ""
        if [[ ${#CATEGORIZED_MANUAL[@]} -eq 0 ]]; then
            echo "*None*"
        else
            echo "| Variable | Expected File | Format | Description |"
            echo "|----------|---------------|--------|-------------|"
            for var_name in "${CATEGORIZED_MANUAL[@]}"; do
                local metadata="${VAR_METADATA[$var_name]}"
                local format=$(echo "$metadata" | cut -d'|' -f1)
                local expected_file=$(echo "$metadata" | cut -d'|' -f2)
                local description=$(echo "$metadata" | cut -d'|' -f3)
                echo "| \`$var_name\` | \`$expected_file\` | $format | $description |"
            done
        fi
        echo ""
        echo "---"
        echo ""
        echo "## Variables in Wrong File"
        echo ""
        if [[ ${#CATEGORIZED_WRONG_FILE[@]} -eq 0 ]]; then
            echo "*None*"
        else
            echo "| Variable | Expected File | Current File | Format |"
            echo "|----------|---------------|--------------|--------|"
            for var_name in "${CATEGORIZED_WRONG_FILE[@]}"; do
                local info="${MISSING_VARS[$var_name]}"
                local expected_file=$(echo "$info" | cut -d'|' -f1)
                local format=$(echo "$info" | cut -d'|' -f2)
                local current_file=$(echo "$info" | cut -d'|' -f4 | sed 's/WRONG_FILE://')
                echo "| \`$var_name\` | \`$expected_file\` | \`$current_file\` | $format |"
            done
        fi
        echo ""
        echo "---"
        echo ""
        echo "## Variables with Empty Values"
        echo ""
        if [[ ${#CATEGORIZED_EMPTY[@]} -eq 0 ]]; then
            echo "*None*"
        else
            echo "| Variable | Expected File | Format |"
            echo "|----------|---------------|--------|"
            for var_name in "${CATEGORIZED_EMPTY[@]}"; do
                local info="${MISSING_VARS[$var_name]}"
                local expected_file=$(echo "$info" | cut -d'|' -f1)
                local format=$(echo "$info" | cut -d'|' -f2)
                echo "| \`$var_name\` | \`$expected_file\` | $format |"
            done
        fi
        echo ""
        echo "---"
        echo ""
        echo "## Inconsistent Variables (Different Values Across Files)"
        echo ""
        if [[ ${#INCONSISTENT_VARS[@]} -eq 0 ]]; then
            echo "*None*"
        else
            echo "| Variable | Files and Values |"
            echo "|----------|------------------|"
            for var_name in "${!INCONSISTENT_VARS[@]}"; do
                local conflicts="${INCONSISTENT_VARS[$var_name]}"
                echo "| \`$var_name\` | $conflicts |"
            done
        fi
        echo ""
        echo "---"
        echo ""
        echo "## All Variables Status"
        echo ""
        echo "| Variable | Status | Expected File | Current Location | Format |"
        echo "|----------|--------|----------------|-------------------|--------|"
        for var_name in $(printf '%s\n' "${!VAR_METADATA[@]}" | sort); do
            local metadata="${VAR_METADATA[$var_name]}"
            local format=$(echo "$metadata" | cut -d'|' -f1)
            local expected_file=$(echo "$metadata" | cut -d'|' -f2)
            local current_location="${VAR_LOCATIONS[$var_name]:-MISSING}"
            
            local status="✅ FOUND"
            if [[ -n "${MISSING_VARS[$var_name]:-}" ]]; then
                status="❌ MISSING"
            elif [[ -n "${INCONSISTENT_VARS[$var_name]:-}" ]]; then
                status="⚠️ INCONSISTENT"
            fi
            
            echo "| \`$var_name\` | $status | \`$expected_file\` | $current_location | $format |"
        done
    } > "$REPORT_FILE"
    
    log_success "Report generated: $REPORT_FILE"
    log_info "Report contains $(wc -l < "$REPORT_FILE" 2>/dev/null || echo "0") lines"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    log_info "========================================"
    log_info "Environment Variables Validation"
    log_info "========================================"
    echo ""
    
    cd "$PROJECT_ROOT" || { log_error "Cannot access project root"; exit 1; }
    
    # Check reference file exists
    if [[ ! -f "$PROJECT_ROOT/$REFERENCE_FILE" ]]; then
        log_error "Reference file not found: $REFERENCE_FILE"
        log_error "Full path: $PROJECT_ROOT/$REFERENCE_FILE"
        exit 1
    fi
    
    # Verify file is readable
    if [[ ! -r "$PROJECT_ROOT/$REFERENCE_FILE" ]]; then
        log_error "Reference file is not readable: $REFERENCE_FILE"
        exit 1
    fi
    
    log_info "Reference file: $PROJECT_ROOT/$REFERENCE_FILE"
    log_info "File size: $(wc -l < "$PROJECT_ROOT/$REFERENCE_FILE") lines"
    
    # Check environment directory exists
    if [[ ! -d "$ENV_DIR" ]]; then
        log_error "Environment directory not found: $ENV_DIR"
        exit 1
    fi
    
    log_info "Environment directory: $ENV_DIR"
    
    # Initialize arrays
    CATEGORIZED_CREATE=()
    CATEGORIZED_SEED=()
    CATEGORIZED_MANUAL=()
    CATEGORIZED_WRONG_FILE=()
    CATEGORIZED_EMPTY=()
    
    # Execute validation steps
    parse_reference_file
    scan_env_files
    validate_variables
    check_consistency
    categorize_by_action
    generate_report
    
    echo ""
    log_success "========================================"
    log_success "Validation Complete!"
    log_success "========================================"
    echo ""
    log_info "Report saved to: $REPORT_FILE"
    log_info ""
    log_info "Summary:"
    log_info "  - Missing: ${#MISSING_VARS[@]} variables"
    log_info "  - Inconsistent: ${#INCONSISTENT_VARS[@]} variables"
    log_info "  - Need CREATE: ${#CATEGORIZED_CREATE[@]} variables"
    log_info "  - Need SEED: ${#CATEGORIZED_SEED[@]} variables"
    log_info "  - Need MANUAL: ${#CATEGORIZED_MANUAL[@]} variables"
    echo ""
}

main "$@"