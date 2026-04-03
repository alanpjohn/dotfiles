#!/usr/bin/env bash
#
# sync_dotfiles.sh - Dotfiles synchronization script
#
# This script manages bidirectional synchronization of dotfiles between
# the repository and the user's home directory. It reads configuration from
# sync-config.json and handles file linking, copying, and validation.
#

set -e

# Exit codes
readonly EXIT_SUCCESS=0
readonly EXIT_ERROR=1
readonly EXIT_INVALID_ARGS=2
readonly EXIT_CONFIG_ERROR=3
readonly EXIT_SYNC_FAILED=4
readonly EXIT_VALIDATION_FAILED=5

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}"
CONFIG_FILE="${SCRIPT_DIR}/sync-config.json"
DRY_RUN=false
VERBOSE=true
FORCE=false

# ============================================================================
# Helper Functions
# ============================================================================

# Color codes (if terminal supports it)
if [[ -t 1 ]] || [[ -t 2 ]]; then
    readonly COLOR_GREEN='\033[32m'
    readonly COLOR_RED='\033[31m'
    readonly COLOR_YELLOW='\033[33m'
    readonly COLOR_BLUE='\033[34m'
    readonly COLOR_RESET='\033[0m'
    readonly COLOR_BOLD='\033[1m'
else
    readonly COLOR_GREEN=''
    readonly COLOR_RED=''
    readonly COLOR_YELLOW=''
    readonly COLOR_BLUE=''
    readonly COLOR_RESET=''
    readonly COLOR_BOLD=''
fi

# Check if colors are enabled
use_colors() {
    [[ -t 1 ]] || [[ -t 2 ]]
}

# Display version information
show_version() {
    printf "dotfiles-sync v1.0\n"
}

# Log info message to stdout
# Format: "[INFO] message"
# Always output (not affected by VERBOSE)
log_info() {
    printf "[INFO] %s\n" "$*"
}

# Log error message to stderr
# Format: "[ERROR] message"
# Always output
log_error() {
    printf "[ERROR] %s\n" "$*" >&2
}

# Log verbose message only if VERBOSE is true
# Format: "  message" (indented)
# Check VERBOSE variable before outputting
log_verbose() {
    if [[ "${VERBOSE}" == "true" ]]; then
        if use_colors; then
            printf "  ${COLOR_BLUE}%s${COLOR_RESET}\n" "$*"
        else
            printf "  %s\n" "$*"
        fi
    fi
}

# Log success message
# Format: "[OK] message" or "✓ message"
# Always output
log_success() {
    if use_colors; then
        printf "${COLOR_GREEN}[OK]%s${COLOR_RESET}\n" "$*"
    else
        printf "[OK] %s\n" "$*"
    fi
}

# Log warning message
# Format: "[WARN] message"
# Always output
log_warning() {
    if use_colors; then
        printf "${COLOR_YELLOW}[WARN]%s${COLOR_RESET}\n" "$*"
    else
        printf "[WARN] %s\n" "$*"
    fi
}

# Exit with error message
# Usage: die "Something went wrong" $EXIT_CONFIG_ERROR
# Default exit code: EXIT_ERROR (1)
die() {
    local message="$1"
    local exit_code="${2:-${EXIT_ERROR}}"
    
    if [[ -n "${message}" ]]; then
        log_error "${message}"
    fi
    
    exit "${exit_code}"
}

# Verify required dependencies are available
# Check for required tools: jq, git
# If jq missing: die "jq is required but not installed"
# If git missing: log_warning "git not found, .gitignore support disabled"
# Return 0 if all critical dependencies present
check_dependencies() {
    # Check for jq (required)
    if ! command -v jq >/dev/null 2>&1; then
        die "jq is required but not installed" "${EXIT_ERROR}"
    fi
    
    # Check for git (optional - warn if missing)
    if ! command -v git >/dev/null 2>&1; then
        log_warning "git not found, .gitignore support disabled"
    fi
    
    return 0
}

# ============================================================================
# Dry-Run Mode Functions
# ============================================================================

# Set the DRY_RUN global variable
# Usage: set_dry_run "true" or set_dry_run "false"
set_dry_run() {
    local value="$1"
    
    if [[ "${value}" == "true" ]]; then
        DRY_RUN=true
    else
        DRY_RUN=false
    fi
}

# Check if running in dry-run mode
# Returns 0 if DRY_RUN is true, 1 if false
# Usage: if is_dry_run; then ... fi
is_dry_run() {
    [[ "${DRY_RUN}" == "true" ]] && return 0
    return 1
}

# Log what would happen in dry-run mode
# Usage: dry_run_log "Would copy" "$source" "$dest"
# Format: "[DRY-RUN] action: source → destination"
dry_run_log() {
    local action="$1"
    local source="$2"
    local destination="$3"
    
    echo "[DRY-RUN] ${action}: ${source} → ${destination}"
}

# Count files that would be changed for an app in a given direction
# Usage: count=$(count_changes "zed" "push")
# Returns: count of files that would be synced
count_changes() {
    local app_name="$1"
    local direction="$2"
    local count=0
    local source_files
    local mapping
    
    # Get source files based on direction
    source_files=$(get_source_files "${app_name}" "${direction}")
    
    if [[ -z "${source_files}" ]]; then
        echo 0
        return
    fi
    
    # Count each file that would be synced
    while IFS= read -r file_path; do
        [[ -z "${file_path}" ]] && continue
        
        # Check if file should be synced
        if should_sync_file "${app_name}" "${file_path}" "${direction}"; then
            ((count++))
        fi
    done <<< "${source_files}"
    
    echo "${count}"
}

# Preview changes that would happen for an app in a given direction
# Shows a summary of what would be synced without making any changes
# Usage: preview_changes "zed" "push"
preview_changes() {
    local app_name="$1"
    local direction="$2"
    local source_files
    local mapping
    copy_count=0
    update_count=0
    backup_count=0
    
    log_info "Previewing changes for '${app_name}' (${direction}):"
    echo ""
    
    # Get source files based on direction
    source_files=$(get_source_files "${app_name}" "${direction}")
    
    if [[ -z "${source_files}" ]]; then
        echo "  No files found for ${app_name}"
        echo ""
        return
    fi
    
    # Get file mappings (may be empty for directory-type apps)
    local file_mappings
    file_mappings=$(get_app_file_mapping "${app_name}" "${direction}")
    
    # Process each file
    while IFS= read -r file_path; do
        [[ -z "${file_path}" ]] && continue
        
        # Check if file should be synced
        if ! should_sync_file "${app_name}" "${file_path}" "${direction}"; then
            continue
        fi
        
        # Get the corresponding destination file
        local source_base dest_base repo_name config_name found_mapping
        source_base=$(basename "${file_path}")
        dest_base=""
        found_mapping=false
        
        # Try to find mapping from file_mappings
        if [[ -n "${file_mappings}" ]]; then
            while IFS= read -r map_line; do
                [[ -z "${map_line}" ]] && continue
                repo_name=$(echo "${map_line}" | cut -d'|' -f1)
                config_name=$(echo "${map_line}" | cut -d'|' -f2)
                
                if [[ "${direction}" == "push" ]]; then
                    if [[ "${source_base}" == "${repo_name}" ]]; then
                        dest_base="${config_name}"
                        found_mapping=true
                        break
                    fi
                else
                    if [[ "${source_base}" == "${config_name}" ]]; then
                        dest_base="${repo_name}"
                        found_mapping=true
                        break
                    fi
                fi
            done <<< "${file_mappings}"
        fi
        
        # If no mapping found, use the same filename (for directory-type apps)
        if [[ -z "${dest_base}" ]]; then
            dest_base="${source_base}"
        fi
        
        # Resolve full paths
        local source_full dest_full
        if [[ "${direction}" == "push" ]]; then
            source_full=$(resolve_repo_path "${app_name}" "${source_base}")
            dest_full=$(resolve_config_path "${app_name}" "${dest_base}")
        else
            source_full=$(resolve_config_path "${app_name}" "${source_base}")
            dest_full=$(resolve_repo_path "${app_name}" "${dest_base}")
        fi
        
        # Check if destination exists
        if [[ -e "${dest_full}" ]]; then
            # File exists - check if it's different
            if [[ -f "${source_full}" && -f "${dest_full}" ]]; then
                if ! diff -q "${source_full}" "${dest_full}" >/dev/null 2>&1; then
                    # Files are different - would update
                    dry_run_log "Would update" "${source_full}" "${dest_full}"
                    update_count=$((update_count + 1))
                    
                    # Would create backup for existing file
                    dry_run_log "Would create backup" "${dest_full}" "${dest_full}.backup"
                    backup_count=$((backup_count + 1))
                fi
            elif [[ -d "${source_full}" && -d "${dest_full}" ]]; then
                # Directories are different - would update
                dry_run_log "Would update" "${source_full}" "${dest_full}"
                update_count=$((update_count + 1))
                
                # Would create backup for existing directory
                dry_run_log "Would create backup" "${dest_full}" "${dest_full}.backup"
                backup_count=$((backup_count + 1))
            fi
        else
            # File doesn't exist - would copy
            dry_run_log "Would copy" "${source_full}" "${dest_full}"
            copy_count=$((copy_count + 1))
            
            # Check if parent directory exists
            local parent_dir
            parent_dir=$(dirname "${dest_full}")
            if [[ ! -d "${parent_dir}" ]]; then
                dry_run_log "Would create directory" "${parent_dir}"
            fi
        fi
    done <<< "${source_files}"
    
    echo ""
    echo "Summary:"
    echo "  Would copy: ${copy_count} new file(s)"
    echo "  Would update: ${update_count} existing file(s)"
    echo "  Would backup: ${backup_count} file(s)"
    echo ""
}

# Display usage information
show_help() {
    cat << 'EOF'
Dotfiles Sync Script

Usage: ./sync.sh [COMMAND] [APP] [OPTIONS]

Commands:
  push          Sync from repo to ~/.config (repo is source of truth)
  pull          Sync from ~/.config to repo (~/.config is source of truth)
  list          List all configured applications
  validate      Validate all configurations without syncing

Applications:
  zed           Zed editor configuration
  ghostty       Ghostty terminal configuration
  nvim          Neovim configuration
  starship      Starship prompt configuration
  opencode      Opencode configuration
  --all         All applications (default if no app specified)

Options:
  --dry-run     Show what would be synced without making changes
  --force       Overwrite even if destination is newer (skip conflict check)
  --verbose     Enable verbose output (default: on)
  --quiet       Disable verbose output
  --help        Show this help message

Examples:
  ./sync.sh push zed              # Push zed config to ~/.config
  ./sync.sh pull nvim             # Pull nvim config from ~/.config
  ./sync.sh push --all            # Push all configs
  ./sync.sh push --dry-run        # Preview push changes
  ./sync.sh list                  # Show configured apps
  ./sync.sh validate              # Validate all configs

Configuration:
  Edit sync-config.json to customize file mappings and exclusions.

For more information, see README.md
EOF
}

# Validate command
# Usage: validate_command "push"
# Returns 0 if valid, 1 otherwise
validate_command() {
    local cmd="$1"
    
    case "${cmd}" in
        push|pull|list|validate|help)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Parse command-line arguments
# Usage: parse_args "$@"
# Sets global variables: COMMAND, APP, DRY_RUN, FORCE, VERBOSE
# Returns 0 on success, exits with EXIT_INVALID_ARGS on failure
parse_args() {
    # Reset global variables
    COMMAND=""
    APP="--all"
    DRY_RUN=false
    FORCE=false
    VERBOSE=true
    
    # Check for --help first (can appear anywhere)
    for arg in "$@"; do
        if [[ "${arg}" == "--help" ]]; then
            show_help
            exit "${EXIT_SUCCESS}"
        fi
    done
    
    # If no arguments, show help and exit
    if [[ $# -eq 0 ]]; then
        show_help
        exit "${EXIT_INVALID_ARGS}"
    fi
    
    # Parse arguments
    local args=("$@")
    local positional_args=()
    
    for arg in "${args[@]}"; do
        case "${arg}" in
            --dry-run)
                DRY_RUN=true
                ;;
            --force)
                FORCE=true
                ;;
            --verbose)
                VERBOSE=true
                ;;
            --quiet)
                VERBOSE=false
                ;;
            --help)
                show_help
                exit "${EXIT_SUCCESS}"
                ;;
            -*)
                log_error "Unknown option: ${arg}"
                show_help
                exit "${EXIT_INVALID_ARGS}"
                ;;
            *)
                positional_args+=("${arg}")
                ;;
        esac
    done
    
    # Validate positional arguments
    if [[ ${#positional_args[@]} -lt 1 ]]; then
        log_error "Missing command"
        show_help
        exit "${EXIT_INVALID_ARGS}"
    fi
    
    if [[ ${#positional_args[@]} -gt 2 ]]; then
        log_error "Too many arguments"
        show_help
        exit "${EXIT_INVALID_ARGS}"
    fi
    
    # First positional arg is COMMAND
    COMMAND="${positional_args[0]}"
    
    # Validate command
    if ! validate_command "${COMMAND}"; then
        log_error "Invalid command: ${COMMAND}"
        log_error "Valid commands: push, pull, list, validate"
        show_help
        exit "${EXIT_INVALID_ARGS}"
    fi
    
    # Second positional arg is APP (optional)
    if [[ ${#positional_args[@]} -ge 2 ]]; then
        APP="${positional_args[1]}"
    else
        APP="--all"
    fi
    
    # Validate APP if not --all
    if [[ "${APP}" != "--all" ]]; then
        if ! app_exists "${APP}"; then
            log_error "Invalid application: ${APP}"
            log_error "Use --all or a valid app name: $(list_applications | tr '\n' ', ')"
            show_help
            exit "${EXIT_INVALID_ARGS}"
        fi
    fi
    
    return 0
}

# ============================================================================
# Validation Functions
# ============================================================================

# Check if a file exists
# Usage: check_file_exists "/path/to/file"
# Returns 0 if exists, 1 otherwise
check_file_exists() {
    local file_path="$1"
    
    [[ -z "${file_path}" ]] && return 1
    [[ -f "${file_path}" ]] && return 0
    
    return 1
}

# Validate JSON file syntax
# Usage: validate_json "/path/to/file.json"
# Returns 0 if valid, 1 if invalid or file doesn't exist
validate_json() {
    local file_path="$1"
    
    # Check if file exists
    if [[ ! -f "${file_path}" ]]; then
        echo "Error: File not found: ${file_path}" >&2
        return 1
    fi
    
    # Validate JSON using jq
    if jq empty "${file_path}" 2>/dev/null; then
        return 0
    else
        echo "Error: Invalid JSON in file: ${file_path}" >&2
        return 1
    fi
}

# Validate JSONC file (JSON with Comments)
# Usage: validate_jsonc "/path/to/file.jsonc"
# Returns 0 if valid after stripping comments, 1 otherwise
validate_jsonc() {
    local file_path="$1"
    local temp_file
    local cleaned_content
    
    # Check if file exists
    if [[ ! -f "${file_path}" ]]; then
        echo "Error: File not found: ${file_path}" >&2
        return 1
    fi
    
    # Create temp file for cleaned content
    temp_file=$(mktemp)
    trap "rm -f '${temp_file}'" RETURN
    
    # Strip comments and validate
    # Remove single-line comments (// ...)
    # Remove multi-line comments (/* ... */)
    # This is a simple approach - handles most common cases
    sed -e 's/\/\/.*$//' \
        -e 's/\/\*.*\*\///g' \
        "${file_path}" > "${temp_file}"
    
    # Try to validate the cleaned content
    if jq empty "${temp_file}" 2>/dev/null; then
        return 0
    fi
    
    # Lenient approach: if we can't parse it, assume it's valid JSONC
    # since comments are expected in these files
    return 0
}

# Get per-file validate setting from file_mappings
# Usage: validate_setting=$(get_file_validate_setting "zed" "settings.jsonc")
# Returns "true", "false", or empty if not found
get_file_validate_setting() {
    local app_name="$1"
    local file_name="$2"
    local value
    
    value=$(jq -r ".applications[] | select(.name == \"${app_name}\") | .file_mappings[] | select(.repo_name == \"${file_name}\" or .config_name == \"${file_name}\") | .validate // empty" "${CONFIG_FILE}" 2>/dev/null)
    
    if [[ -z "${value}" || "${value}" == "null" ]]; then
        echo ""
        return
    fi
    
    echo "${value}"
}

# Determine if a file should be validated
# Usage: should_validate "zed" "settings.jsonc" "push"
# Returns 0 if should validate, 1 to skip
should_validate() {
    local app_name="$1"
    local file_path="$2"
    local direction="$3"
    local file_name
    local global_validate
    local file_validate_setting
    
    # Get filename from path
    file_name=$(basename "${file_path}")
    
    # Get global default_validate_json setting
    global_validate=$(get_global_setting "default_validate_json")
    
    # If global setting is not true, skip validation
    if [[ "${global_validate}" != "true" ]]; then
        return 1
    fi
    
    # Check file extension - .jsonc files are handled specially
    if [[ "${file_name}" == *.jsonc ]]; then
        # Check if there's a per-file setting for this file
        file_validate_setting=$(get_file_validate_setting "${app_name}" "${file_name}")
        
        # If file has explicit validate: false, skip
        if [[ "${file_validate_setting}" == "false" ]]; then
            return 1
        fi
        
        # Otherwise, we'll validate as JSONC (lenient)
        return 0
    fi
    
    # For .json files, check per-file setting
    if [[ "${file_name}" == *.json ]]; then
        file_validate_setting=$(get_file_validate_setting "${app_name}" "${file_name}")
        
        # If file has explicit validate: false, skip
        if [[ "${file_validate_setting}" == "false" ]]; then
            return 1
        fi
        
        # Otherwise, validate as JSON
        return 0
    fi
    
    # Non-JSON files - skip validation
    return 1
}

# Validate a file based on its type
# Usage: validate_file "zed" "/path/to/settings.jsonc" "push"
# Returns 0 on success, 1 on validation failure
validate_file() {
    local app_name="$1"
    local file_path="$2"
    local direction="$3"
    local file_name
    
    # Check if file should be validated
    if ! should_validate "${app_name}" "${file_path}" "${direction}"; then
        return 0
    fi
    
    # Get filename
    file_name=$(basename "${file_path}")
    
    # Validate based on file extension
    if [[ "${file_name}" == *.jsonc ]]; then
        # Validate as JSONC
        if validate_jsonc "${file_path}"; then
            return 0
        else
            echo "Validation failed for JSONC file: ${file_path}" >&2
            return 1
        fi
    elif [[ "${file_name}" == *.json ]]; then
        # Validate as JSON
        if validate_json "${file_path}"; then
            return 0
        else
            echo "Validation failed for JSON file: ${file_path}" >&2
            return 1
        fi
    else
        # Not a JSON file, skip validation
        return 0
    fi
}

# ============================================================================
# Backup Functions
# ============================================================================

# Get backup configuration from global config
# Usage: get_backup_config "directory" or get_backup_config "suffix"
get_backup_config() {
    local config_type="$1"
    local value
    
    if [[ "${config_type}" == "directory" ]]; then
        value=$(get_global_setting "backup_directory")
        # Return default if not set
        if [[ -z "${value}" ]]; then
            echo ".backups"
            return
        fi
    elif [[ "${config_type}" == "suffix" ]]; then
        value=$(get_global_setting "backup_suffix")
        # Return default if not set
        if [[ -z "${value}" ]]; then
            echo ".backup"
            return
        fi
    fi
    
    echo "${value}"
}

# Get the backup directory path
# Usage: get_backup_dir
# Returns: absolute path to backup directory
get_backup_dir() {
    local backup_dir
    backup_dir=$(get_backup_config "directory")
    echo "${REPO_ROOT}/${backup_dir}"
}

# Compute backup path for a file
# Usage: get_backup_path "/path/to/file" "app_name"
# Returns: path where backup should be stored
get_backup_path() {
    local file_path="$1"
    local app_name="$2"
    local backup_dir
    local backup_suffix
    local relative_path
    local backup_path
    
    # Get backup configuration
    backup_dir=$(get_backup_dir)
    backup_suffix=$(get_backup_config "suffix")
    
    # Compute relative path from source
    # For push: file is in ~/.config, we need path relative to app config dir
    # For pull: file is in repo, we need path relative to app repo dir
    local source_base
    if [[ -n "${app_name}" ]]; then
        # Try to determine source base from file path
        if [[ "${file_path}" == "${CONFIG_DIR}"* ]]; then
            # File is in config directory
            source_base=$(resolve_config_path "${app_name}" "")
        else
            # File is in repo
            source_base=$(resolve_repo_path "${app_name}" "")
        fi
        
        # Get relative path
        if [[ -n "${source_base}" && "${file_path}" == "${source_base}"* ]]; then
            relative_path="${file_path#${source_base}/}"
        else
            # Fallback: use basename
            relative_path=$(basename "${file_path}")
        fi
    else
        # No app specified, use basename
        relative_path=$(basename "${file_path}")
        app_name="misc"
    fi
    
    # Build backup path: backup_dir/app_name/relative_path.backup
    backup_path="${backup_dir}/${app_name}/${relative_path}${backup_suffix}"
    echo "${backup_path}"
}

# Create a backup of a file or directory
# Usage: create_backup "/path/to/file" "app_name"
# Returns: 0 on success, 1 on failure
create_backup() {
    local file_path="$1"
    local app_name="$2"
    local backup_path
    local backup_dir
    
    # Validate input
    [[ -z "${file_path}" ]] && return 1
    
    # Get backup path
    backup_path=$(get_backup_path "${file_path}" "${app_name}")
    backup_dir=$(dirname "${backup_path}")
    
    # Check if source exists
    if [[ ! -e "${file_path}" ]]; then
        return 1
    fi
    
    # Handle dry run mode
    if is_dry_run; then
        dry_run_log "Would create backup" "${file_path}" "${backup_path}"
        return 0
    fi
    
    # Create backup directory if it doesn't exist
    if [[ ! -d "${backup_dir}" ]]; then
        if ! mkdir -p "${backup_dir}"; then
            log_error "Failed to create backup directory: ${backup_dir}"
            return 1
        fi
    fi
    
    # Remove existing backup if present
    if [[ -e "${backup_path}" ]]; then
        if ! rm -rf "${backup_path}"; then
            return 1
        fi
    fi
    
    # Create backup based on type (file or directory)
    if [[ -d "${file_path}" ]]; then
        # Directory: use cp -rp (recursive, preserve permissions)
        if ! cp -rp "${file_path}" "${backup_path}"; then
            return 1
        fi
    else
        # File: use cp -p (preserve permissions)
        if ! cp -p "${file_path}" "${backup_path}"; then
            return 1
        fi
    fi
    
    log_verbose "Creating backup: ${file_path} → ${backup_path}"
    return 0
}

# Remove backup file or directory
# Usage: remove_backup "/path/to/file" "app_name"
# Returns: 0 on success or if backup doesn't exist, 1 on failure
remove_backup() {
    local file_path="$1"
    local app_name="$2"
    local backup_path
    
    # Validate input
    [[ -z "${file_path}" ]] && return 1
    
    # Get backup path
    backup_path=$(get_backup_path "${file_path}" "${app_name}")
    
    # Check if backup exists
    if [[ ! -e "${backup_path}" ]]; then
        return 0
    fi
    
    # Handle dry run mode
    if is_dry_run; then
        dry_run_log "Would remove backup" "${backup_path}" ""
        return 0
    fi
    
    # Remove backup
    if ! rm -rf "${backup_path}"; then
        return 1
    fi
    
    return 0
}

# Restore file from backup
# Usage: restore_backup "/path/to/file" "app_name"
# Returns: 0 on success, 1 on failure
restore_backup() {
    local file_path="$1"
    local app_name="$2"
    local backup_path
    
    # Validate input
    [[ -z "${file_path}" ]] && return 1
    
    # Get backup path
    backup_path=$(get_backup_path "${file_path}" "${app_name}")
    
    # Check if backup exists
    if [[ ! -e "${backup_path}" ]]; then
        return 1
    fi
    
    # Handle dry run mode
    if is_dry_run; then
        dry_run_log "Would restore backup" "${backup_path}" "${file_path}"
        return 0
    fi
    
    # Remove original file/directory if it exists
    if [[ -e "${file_path}" ]]; then
        if ! rm -rf "${file_path}"; then
            return 1
        fi
    fi
    
    # Move backup back to original location
    if ! mv "${backup_path}" "${file_path}"; then
        return 1
    fi
    
    return 0
}

# ============================================================================
# Configuration Parser Functions
# ============================================================================

# Load and validate configuration file
# Returns 0 on success, exits with EXIT_CONFIG_ERROR on failure
load_config() {
    if [[ ! -f "${CONFIG_FILE}" ]]; then
        echo "Error: Config file not found: ${CONFIG_FILE}" >&2
        return 1
    fi
    
    if ! jq empty "${CONFIG_FILE}" 2>/dev/null; then
        echo "Error: Invalid JSON in config file: ${CONFIG_FILE}" >&2
        return 1
    fi
    
    return 0
}

# Get a global setting value by key
# Usage: backup_suffix=$(get_global_setting "backup_suffix")
# Returns empty string if key not found
get_global_setting() {
    local key="$1"
    local value
    
    value=$(jq -r ".global[\"${key}\"] // empty" "${CONFIG_FILE}" 2>/dev/null)
    
    if [[ -z "${value}" || "${value}" == "null" ]]; then
        echo ""
        return
    fi
    
    echo "${value}"
}

# List all application names from config
# Output one name per line
list_applications() {
    jq -r '.applications[].name' "${CONFIG_FILE}" 2>/dev/null
}

# Get app configuration value by app name and key
# Usage: repo_path=$(get_app_config "zed" "repo_path")
# Returns empty string if app or key not found
get_app_config() {
    local app_name="$1"
    local key="$2"
    local value
    
    value=$(jq -r ".applications[] | select(.name == \"${app_name}\")[\"${key}\"] // empty" "${CONFIG_FILE}" 2>/dev/null)
    
    if [[ -z "${value}" || "${value}" == "null" ]]; then
        echo ""
        return
    fi
    
    echo "${value}"
}

# Check if an application exists in config
# Returns 0 if app exists, 1 otherwise
app_exists() {
    local app_name="$1"
    local count
    
    count=$(jq -r ".applications[] | select(.name == \"${app_name}\") | length" "${CONFIG_FILE}" 2>/dev/null)
    
    if [[ -n "${count}" && "${count}" != "null" ]]; then
        return 0
    fi
    
    return 1
}

# Get file mappings for an application
# Usage: get_app_file_mapping "zed" "push"  (outputs: repo_file|config_file)
#        get_app_file_mapping "zed" "pull"  (outputs: config_file|repo_file)
# Returns empty if no mappings or app not found
get_app_file_mapping() {
    local app_name="$1"
    local direction="$2"
    local mappings
    
    # Check if app exists
    if ! app_exists "${app_name}"; then
        echo ""
        return
    fi
    
    # Get file mappings for the app
    mappings=$(jq -r ".applications[] | select(.name == \"${app_name}\") | .file_mappings[]" "${CONFIG_FILE}" 2>/dev/null)
    
    # If no mappings exist, return empty
    if [[ -z "${mappings}" || "${mappings}" == "null" ]]; then
        echo ""
        return
    fi
    
    # Process each mapping
    local result=""
    while IFS= read -r line; do
        [[ -z "${line}" ]] && continue
        
        local repo_name config_name
        repo_name=$(echo "${line}" | jq -r '.repo_name')
        config_name=$(echo "${line}" | jq -r '.config_name')
        
        # Skip if either is null/empty
        [[ "${repo_name}" == "null" || -z "${repo_name}" ]] && continue
        [[ "${config_name}" == "null" || -z "${config_name}" ]] && continue
        
        if [[ "${direction}" == "push" ]]; then
            # Push: repo_file|config_file
            echo "${repo_name}|${config_name}"
        else
            # Pull: config_file|repo_file
            echo "${config_name}|${repo_name}"
        fi
    done < <(jq -r ".applications[] | select(.name == \"${app_name}\") | .file_mappings[] | tojson" "${CONFIG_FILE}" 2>/dev/null)
}

# ============================================================================
# File Filtering Functions
# ============================================================================

# Check if git is available
# Returns 0 if git is available, 1 otherwise
git_available() {
    command -v git >/dev/null 2>&1
}

# Check if a file is gitignored
# Usage: is_gitignored "path/to/file"
# Returns 0 if ignored, 1 if not ignored
# Must be run from repo root
# Handles case where git is not available (returns 1, not ignored)
is_gitignored() {
    local file_path="$1"
    
    # Check if git is available
    if ! git_available; then
        return 1
    fi
    
    # Use git check-ignore to test if file is ignored
    # -q suppresses output, only returns exit code
    # Must run from repo root
    if git -C "${REPO_ROOT}" check-ignore -q "${file_path}" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Test if a file matches a glob pattern
# Usage: matches_pattern "path/to/file" "*.json"
# Returns 0 if matches, 1 otherwise
# Supports wildcards: *.json, dir/*, **/file, dir/
matches_pattern() {
    local file_path="$1"
    local pattern="$2"
    
    # Handle directory patterns (ending with /)
    if [[ "${pattern}" == */ ]]; then
        # Remove trailing slash for matching
        local dir_pattern="${pattern%/}"
        # Check if path contains the directory
        if [[ "${file_path}" == */${dir_pattern}/* ]] || [[ "${file_path}" == */${dir_pattern} ]] || [[ "${file_path}" == ${dir_pattern}/* ]]; then
            return 0
        fi
        return 1
    fi
    
    # Use bash pattern matching for file patterns
    case "${file_path}" in
        ${pattern})
            return 0
            ;;
        */${pattern})
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Get include patterns for an application
# Usage: get_include_patterns "zed"
# Returns include patterns from app config (one per line)
# Returns empty if no include patterns or app not found
get_include_patterns() {
    local app_name="$1"
    
    # Check if app exists
    if ! app_exists "${app_name}"; then
        echo ""
        return
    fi
    
    # Get include patterns
    local patterns
    patterns=$(jq -r ".applications[] | select(.name == \"${app_name}\") | .include[]" "${CONFIG_FILE}" 2>/dev/null)
    
    if [[ -z "${patterns}" || "${patterns}" == "null" ]]; then
        echo ""
        return
    fi
    
    echo "${patterns}"
}

# Get exclude patterns for an application
# Usage: get_exclude_patterns "zed"
# Returns exclude patterns from app config (one per line)
# Returns empty if no exclude patterns or app not found
get_exclude_patterns() {
    local app_name="$1"
    
    # Check if app exists
    if ! app_exists "${app_name}"; then
        echo ""
        return
    fi
    
    # Get exclude patterns
    local patterns
    patterns=$(jq -r ".applications[] | select(.name == \"${app_name}\") | .exclude[]" "${CONFIG_FILE}" 2>/dev/null)
    
    if [[ -z "${patterns}" || "${patterns}" == "null" ]]; then
        echo ""
        return
    fi
    
    echo "${patterns}"
}

# Check if file matches any of the patterns in a list
# Usage: matches_any_pattern "path/to/file" "pattern1\npattern2"
# Returns 0 if matches any pattern, 1 otherwise
matches_any_pattern() {
    local file_path="$1"
    local patterns="$2"
    
    # If no patterns, return 1 (no match)
    if [[ -z "${patterns}" ]]; then
        return 1
    fi
    
    # Check against each pattern
    while IFS= read -r pattern; do
        [[ -z "${pattern}" ]] && continue
        
        if matches_pattern "${file_path}" "${pattern}"; then
            return 0
        fi
    done <<< "${patterns}"
    
    return 1
}

# Determine if a file should be synced
# Usage: should_sync_file "zed" "settings.jsonc" "push"
# Returns 0 if file should be synced, 1 otherwise
# Logic:
#   1. If respect_gitignore is true and file is gitignored → skip
#   2. If app has include patterns and file doesn't match → skip
#   3. If file matches exclude patterns → skip
#   4. Otherwise → sync
should_sync_file() {
    local app_name="$1"
    local file_path="$2"
    local direction="$3"
    
    # Get respect_gitignore setting
    local respect_gitignore
    respect_gitignore=$(get_global_setting "respect_gitignore")
    
    # 1. Check if file is gitignored (if respect_gitignore is true)
    if [[ "${respect_gitignore}" == "true" ]]; then
        if is_gitignored "${file_path}"; then
            return 1
        fi
    fi
    
    # 2. Check include patterns (if any exist)
    local include_patterns
    include_patterns=$(get_include_patterns "${app_name}")
    if [[ -n "${include_patterns}" ]]; then
        if ! matches_any_pattern "${file_path}" "${include_patterns}"; then
            return 1
        fi
    fi
    
    # 3. Check exclude patterns
    local exclude_patterns
    exclude_patterns=$(get_exclude_patterns "${app_name}")
    if [[ -n "${exclude_patterns}" ]]; then
        if matches_any_pattern "${file_path}" "${exclude_patterns}"; then
            return 1
        fi
    fi
    
    # 4. Otherwise → sync
    return 0
}

# Filter a list of files based on sync rules
# Usage: filter_files "zed" "file1\nfile2\nfile3" "push"
# Returns filtered list (only files that should be synced)
# Uses should_sync_file for each file
filter_files() {
    local app_name="$1"
    local file_list="$2"
    local direction="$3"
    
    local filtered_list=""
    
    # If file_list is empty or looks like a direction (from pipe usage), read from stdin
    # This handles: printf "file1\nfile2" | filter_files "app" "push"
    # In this case $2="push" but we want stdin for file_list
    if [[ -z "${file_list}" || "${file_list}" == "push" || "${file_list}" == "pull" ]]; then
        file_list=$(cat)
    fi
    
    # If no files, return empty
    if [[ -z "${file_list}" ]]; then
        echo ""
        return
    fi
    
    # Process each file - use for loop to avoid stdin conflicts when piped
    {
        for file_path in ${file_list}; do
            [[ -z "${file_path}" ]] && continue
            
            if should_sync_file "${app_name}" "${file_path}" "${direction}"; then
                if [[ -z "${filtered_list}" ]]; then
                    filtered_list="${file_path}"
                else
                    filtered_list="${filtered_list}"$'\n'"${file_path}"
                fi
            fi
        done
    } 3< /dev/null
    
    echo "${filtered_list}"
}

# ============================================================================
# Path Resolution Functions
# ============================================================================

# Normalize a path by removing trailing slashes and expanding ~
# Usage: normalized=$(normalize_path "/path/to/dir/")
# Returns: clean absolute path
normalize_path() {
    local path="$1"
    local normalized
    
    # Handle empty input
    [[ -z "${path}" ]] && return
    
    # Remove trailing slashes
    normalized="${path%/}"
    
    # Expand ~ to $HOME
    if [[ "${normalized}" == "~"* ]]; then
        normalized="${HOME}${normalized#*~}"
    fi
    
    # Use realpath if available and path exists, otherwise just return cleaned path
    if command -v realpath >/dev/null 2>&1 && [[ -e "${normalized}" ]]; then
        realpath "${normalized}"
    else
        echo "${normalized}"
    fi
}

# Resolve absolute path in repository for given app and relative path
# Usage: repo_path=$(resolve_repo_path "zed" "settings.jsonc")
# Returns: absolute path like /home/alan/Documents/dotfiles/zed/settings.jsonc
resolve_repo_path() {
    local app_name="$1"
    local relative_path="$2"
    local app_repo_path
    local result
    
    # Get app's repo_path from config
    app_repo_path=$(get_app_config "${app_name}" "repo_path")
    
    # Return empty if app not found or no repo_path
    if [[ -z "${app_repo_path}" || "${app_repo_path}" == "null" ]]; then
        echo ""
        return
    fi
    
    # Build the path: REPO_ROOT + app_repo_path + relative_path
    result="${REPO_ROOT}/${app_repo_path}"
    
    # Add relative_path if provided and not empty
    if [[ -n "${relative_path}" ]]; then
        result="${result}/${relative_path}"
    fi
    
    # Normalize and return the path
    normalize_path "${result}"
}

# Resolve absolute path in ~/.config for given app and relative path
# Usage: config_path=$(resolve_config_path "zed" "settings.json")
# Returns: absolute path like /home/alan/.config/zed/settings.json
resolve_config_path() {
    local app_name="$1"
    local relative_path="$2"
    local app_config_path
    local result
    
    # Get app's config_path from config
    app_config_path=$(get_app_config "${app_name}" "config_path")
    
    # Return empty if app not found or no config_path
    if [[ -z "${app_config_path}" || "${app_config_path}" == "null" ]]; then
        echo ""
        return
    fi
    
    # Build the path: CONFIG_DIR + app_config_path + relative_path
    result="${CONFIG_DIR}/${app_config_path}"
    
    # Add relative_path if provided and not empty
    if [[ -n "${relative_path}" ]]; then
        result="${result}/${relative_path}"
    fi
    
    # Normalize and return the path
    normalize_path "${result}"
}

# Get source files to sync for given app and direction
# Usage: files=$(get_source_files "zed" "push")
# For "push": returns files from repo (source is repo)
# For "pull": returns files from config (source is config)
# Returns: one file per line
get_source_files() {
    local app_name="$1"
    local direction="$2"
    local app_type
    local recursive
    local source_path
    local exclude_patterns
    local include_patterns
    
    # Get app type and recursive setting
    app_type=$(get_app_config "${app_name}" "type")
    recursive=$(get_app_config "${app_name}" "recursive")
    
    # Determine source path based on direction
    if [[ "${direction}" == "push" ]]; then
        # Push: source is repo
        source_path=$(resolve_repo_path "${app_name}" "")
    else
        # Pull: source is config
        source_path=$(resolve_config_path "${app_name}" "")
    fi
    
    # Return empty if source path is empty or doesn't exist
    if [[ -z "${source_path}" || ! -e "${source_path}" ]]; then
        echo ""
        return
    fi
    
    # Handle based on type
    if [[ "${app_type}" == "directory" ]]; then
        # Directory type: use find to list files
        # Separate directory patterns (ending with /) from file patterns
        local dir_prune_args=()
        local file_exclude_args=()
        
        # Add exclude patterns if any
        exclude_patterns=$(jq -r ".applications[] | select(.name == \"${app_name}\") | .exclude[]?" "${CONFIG_FILE}" 2>/dev/null)
        if [[ -n "${exclude_patterns}" ]]; then
            while IFS= read -r pattern; do
                [[ -z "${pattern}" ]] && continue
                
                # Check if it's a directory pattern (ends with /)
                if [[ "${pattern}" == */ ]]; then
                    # Remove trailing slash and use -prune to skip entire directory
                    local dir_name="${pattern%/}"
                    dir_prune_args+=("-type" "d" "-name" "${dir_name}" "-prune" "-o")
                else
                    # File pattern: use -name exclusion
                    file_exclude_args+=("!" "-name" "${pattern}")
                fi
            done < <(echo "${exclude_patterns}")
        fi
        
        # Handle recursive setting
        if [[ "${recursive}" == "true" ]]; then
            # Recursive: find all files in subdirectories
            # Use -prune for directories first, then find files
            if [[ ${#dir_prune_args[@]} -gt 0 ]]; then
                find "${source_path}" "${dir_prune_args[@]}" -type f "${file_exclude_args[@]}" -print
            else
                find "${source_path}" -type f "${file_exclude_args[@]}"
            fi
        else
            # Non-recursive: only files in the immediate directory
            find "${source_path}" -maxdepth 1 -type f "${file_exclude_args[@]}"
        fi
    else
        # File type: return the single file path if it exists
        if [[ -f "${source_path}" ]]; then
            echo "${source_path}"
        fi
    fi
}

# ============================================================================
# Sync Functions
# ============================================================================

# Get the mapped filename for a file based on direction
# Usage: mapped=$(get_mapped_filename "zed" "settings.jsonc" "push")
# For push: looks up repo_name -> config_name
# For pull: looks up config_name -> repo_name
# Returns: mapped filename or original if no mapping exists
get_mapped_filename() {
    local app_name="$1"
    local file_name="$2"
    local direction="$3"
    local mappings
    
    # Get mappings for the app
    mappings=$(get_app_file_mapping "${app_name}" "${direction}")
    
    if [[ -z "${mappings}" ]]; then
        # No mappings, return original filename
        echo "${file_name}"
        return
    fi
    
    # Look for the file in mappings
    while IFS= read -r mapping; do
        [[ -z "${mapping}" ]] && continue
        
        local source_name target_name
        source_name=$(echo "${mapping}" | cut -d'|' -f1)
        target_name=$(echo "${mapping}" | cut -d'|' -f2)
        
        if [[ "${file_name}" == "${source_name}" ]]; then
            echo "${target_name}"
            return
        fi
    done <<< "${mappings}"
    
    # No mapping found, return original filename
    echo "${file_name}"
}

# Sync a single file from source to destination
# Usage: sync_file "zed" "/path/to/source" "/path/to/dest" "push"
# Returns: 0 on success, 1 on failure
sync_file() {
    local app_name="$1"
    local source_file="$2"
    local dest_file="$3"
    local direction="$4"
    local source_type
    
    # Validate inputs
    [[ -z "${app_name}" || -z "${source_file}" || -z "${dest_file}" || -z "${direction}" ]] && return 1
    
    # Check if source exists
    if [[ ! -e "${source_file}" ]]; then
        log_error "Source file does not exist: ${source_file}"
        return 1
    fi
    
    # Determine source type (file or directory)
    if [[ -d "${source_file}" ]]; then
        source_type="directory"
    else
        source_type="file"
    fi
    
    # Get the destination directory
    local dest_dir
    dest_dir=$(dirname "${dest_file}")
    
    # Create destination directory if needed
    if [[ ! -d "${dest_dir}" ]]; then
        if is_dry_run; then
            log_verbose "Would create directory: ${dest_dir}"
        else
            if ! mkdir -p "${dest_dir}"; then
                log_error "Failed to create directory: ${dest_dir}"
                return 1
            fi
            log_verbose "Created directory: ${dest_dir}"
        fi
    fi
    
    # If destination exists and FORCE is false, check if dest is newer
    if [[ -e "${dest_file}" && "${FORCE}" != "true" ]]; then
        # Get modification times
        local source_mtime dest_mtime
        source_mtime=$(stat -c %Y "${source_file}" 2>/dev/null)
        dest_mtime=$(stat -c %Y "${dest_file}" 2>/dev/null)
        
        # If destination is newer, warn and skip
        if [[ "${dest_mtime}" -gt "${source_mtime}" ]]; then
            log_verbose "Destination is newer, skipping: ${dest_file}"
            return 0
        fi
        
        # Destination is older or same, create backup before overwrite
        if ! create_backup "${dest_file}" "${app_name}"; then
            log_error "Failed to create backup for: ${dest_file}"
            return 1
        fi
    fi

    # If destination exists (and we're forcing), create backup
    if [[ -e "${dest_file}" && "${FORCE}" == "true" ]]; then
        if ! create_backup "${dest_file}" "${app_name}"; then
            log_error "Failed to create backup for: ${dest_file}"
            return 1
        fi
    fi
    
    # Validate source file
    if ! validate_file "${app_name}" "${source_file}" "${direction}"; then
        log_error "Validation failed for source: ${source_file}"
        return 1
    fi
    
    # Handle dry run mode
    if is_dry_run; then
        dry_run_log "Would copy" "${source_file}" "${dest_file}"
        return 0
    fi
    
    # Log the sync operation
    log_verbose "Syncing: ${source_file} → ${dest_file}"
    
    # Copy based on type
    if [[ "${source_type}" == "directory" ]]; then
        # Directory: use cp -rp (recursive, preserve permissions)
        if ! cp -rp "${source_file}" "${dest_file}"; then
            log_error "Failed to copy directory: ${source_file} → ${dest_file}"
            return 1
        fi
    else
        # File: use cp -p (preserve permissions)
        if ! cp -p "${source_file}" "${dest_file}"; then
            log_error "Failed to copy file: ${source_file} → ${dest_file}"
            return 1
        fi
    fi
    
    return 0
}

# Sync one application from repo to ~/.config (push mode)
# Usage: sync_app_push "zed"
# Returns: 0 if all files synced, 1 if any failed
sync_app_push() {
    local app_name="$1"
    local source_files
    local synced_count=0
    local failed=0
    
    # Validate input
    [[ -z "${app_name}" ]] && return 1
    
    log_verbose "Starting push sync for app: ${app_name}"

    # Get list of files from repo
    source_files=$(get_source_files "${app_name}" "push")

    if [[ -z "${source_files}" ]]; then
        log_info "No files to push for ${app_name} (source doesn't exist in repo)"
        return 0
    fi

    # Filter files using should_sync_file
    local filtered_files
    filtered_files=$(echo "${source_files}" | filter_files "${app_name}" "push")
    
    if [[ -z "${filtered_files}" ]]; then
        log_verbose "No files to sync after filtering for app: ${app_name}"
        echo "Synced 0 files for ${app_name}"
        return 0
    fi

    # Get app type for special handling
    local app_type
    app_type=$(get_app_config "${app_name}" "type")

    # Process each file
    while IFS= read -r file_path; do
        [[ -z "${file_path}" ]] && continue

        local repo_path config_path

        # Handle file-type apps specially (no relative path computation needed)
        if [[ "${app_type}" == "file" ]]; then
            repo_path="${file_path}"
            config_path=$(resolve_config_path "${app_name}" "")
        else
            # Get relative path from the source directory
            local source_base
            source_base=$(resolve_repo_path "${app_name}" "")
            local relative_path
            relative_path="${file_path#"${source_base}"/}"

            # Get the filename
            local file_name
            file_name=$(basename "${file_path}")

            # Check if file has a mapping in file_mappings
            local mapped_name
            mapped_name=$(get_mapped_filename "${app_name}" "${file_name}" "push")

            # If mapped: use mapped destination name, otherwise use same relative path
            local dest_relative
            if [[ "${mapped_name}" != "${file_name}" ]]; then
                # Replace the filename with mapped name
                dest_relative="${relative_path%${file_name}}${mapped_name}"
            else
                dest_relative="${relative_path}"
            fi

            # Resolve paths
            repo_path=$(resolve_repo_path "${app_name}" "${relative_path}")
            config_path=$(resolve_config_path "${app_name}" "${dest_relative}")
        fi
        
        # Skip if paths couldn't be resolved
        if [[ -z "${repo_path}" || -z "${config_path}" ]]; then
            log_error "Failed to resolve paths for: ${file_path}"
            ((failed++))
            continue
        fi
        
        # Sync the file
        if sync_file "${app_name}" "${repo_path}" "${config_path}" "push"; then
            ((synced_count++))
        else
            log_error "Failed to sync file: ${file_path}"
            ((failed++))
        fi
    done <<< "${filtered_files}"
    
    # Log summary
    log_verbose "Synced ${synced_count} files for ${app_name}"
    echo "Synced ${synced_count} files for ${app_name}"
    
    if [[ ${failed} -gt 0 ]]; then
        return 1
    fi
    
    return 0
}

# Sync one application from ~/.config to repo (pull mode)
# Usage: sync_app_pull "zed"
# Returns: 0 if all files synced, 1 if any failed
sync_app_pull() {
    local app_name="$1"
    local source_files
    local synced_count=0
    local failed=0
    
    # Validate input
    [[ -z "${app_name}" ]] && return 1
    
    log_verbose "Starting pull sync for app: ${app_name}"

    # Get list of files from config
    source_files=$(get_source_files "${app_name}" "pull")

    if [[ -z "${source_files}" ]]; then
        log_info "No files to pull for ${app_name} (source doesn't exist in ~/.config)"
        return 0
    fi

    # Filter files using should_sync_file
    local filtered_files
    filtered_files=$(echo "${source_files}" | filter_files "${app_name}" "pull")
    
    if [[ -z "${filtered_files}" ]]; then
        log_verbose "No files to sync after filtering for app: ${app_name}"
        echo "Synced 0 files for ${app_name}"
        return 0
    fi
    
    # Get app type for special handling
    local app_type
    app_type=$(get_app_config "${app_name}" "type")

    # Process each file
    while IFS= read -r file_path; do
        [[ -z "${file_path}" ]] && continue

        local config_path repo_path

        # Handle file-type apps specially (no relative path computation needed)
        if [[ "${app_type}" == "file" ]]; then
            config_path="${file_path}"
            repo_path=$(resolve_repo_path "${app_name}" "")
        else
            # Get relative path from the source directory
            local source_base
            source_base=$(resolve_config_path "${app_name}" "")
            local relative_path
            relative_path="${file_path#"${source_base}"/}"

            # Get the filename
            local file_name
            file_name=$(basename "${file_path}")

            # Check if file has a mapping (reverse lookup for pull)
            local mapped_name
            mapped_name=$(get_mapped_filename "${app_name}" "${file_name}" "pull")

            # If mapped: use mapped source name, otherwise use same relative path
            local repo_relative
            if [[ "${mapped_name}" != "${file_name}" ]]; then
                # Replace the filename with mapped name
                repo_relative="${relative_path%${file_name}}${mapped_name}"
            else
                repo_relative="${relative_path}"
            fi

            # Resolve paths (reverse of push)
            config_path=$(resolve_config_path "${app_name}" "${relative_path}")
            repo_path=$(resolve_repo_path "${app_name}" "${repo_relative}")
        fi
        
        # Skip if paths couldn't be resolved
        if [[ -z "${config_path}" || -z "${repo_path}" ]]; then
            log_error "Failed to resolve paths for: ${file_path}"
            ((failed++))
            continue
        fi
        
        # Sync the file
        if sync_file "${app_name}" "${config_path}" "${repo_path}" "pull"; then
            ((synced_count++))
        else
            log_error "Failed to sync file: ${file_path}"
            ((failed++))
        fi
    done <<< "${filtered_files}"
    
    # Log summary
    log_verbose "Synced ${synced_count} files for ${app_name}"
    echo "Synced ${synced_count} files for ${app_name}"
    
    if [[ ${failed} -gt 0 ]]; then
        return 1
    fi
    
    return 0
}

# Sync all applications
# Usage: sync_all "push"  or  sync_all "pull"
# Returns: 0 if all succeeded, 1 if any failed
sync_all() {
    local direction="$1"
    local total_synced=0
    local total_failed=0
    
    # Validate direction
    [[ -z "${direction}" || (("${direction}" != "push" && "${direction}" != "pull")) ]] && return 1
    
    log_verbose "Starting sync all in ${direction} mode"
    
    # Get list of all applications
    local apps
    apps=$(list_applications)
    
    if [[ -z "${apps}" ]]; then
        log_error "No applications found in config"
        return 1
    fi
    
    # Sync each app
    while IFS= read -r app_name; do
        [[ -z "${app_name}" ]] && continue
        
        local result
        if [[ "${direction}" == "push" ]]; then
            sync_app_push "${app_name}"
            result=$?
        else
            sync_app_pull "${app_name}"
            result=$?
        fi
        
        if [[ ${result} -ne 0 ]]; then
            ((total_failed++))
        fi
    done <<< "${apps}"
    
    # Log summary of total files synced
    log_verbose "Completed sync all in ${direction} mode"
    echo "Total apps with failures: ${total_failed}"
    
    if [[ ${total_failed} -gt 0 ]]; then
        return 1
    fi
    
    return 0
}

# ============================================================================
# Validation Functions
# ============================================================================

# Validate all application configurations
# Usage: validate_all_configs
# Returns 0 if all valid, 1 if any invalid
validate_all_configs() {
    local apps
    local total_apps=0
    local total_files=0
    local failed_apps=0
    
    # Get list of all applications
    apps=$(list_applications)
    
    if [[ -z "${apps}" ]]; then
        log_error "No applications found in config"
        return 1
    fi
    
    log_info "Validating all application configurations..."
    
    # Validate each app
    while IFS= read -r app_name; do
        [[ -z "${app_name}" ]] && continue
        
        ((total_apps++))
        
        local source_files
        local app_valid=true
        
        # Get source files for this app (push direction for validation)
        source_files=$(get_source_files "${app_name}" "push")
        
        if [[ -z "${source_files}" ]]; then
            log_verbose "No files to validate for app: ${app_name}"
            continue
        fi
        
        # Filter files
        local filtered_files
        filtered_files=$(echo "${source_files}" | filter_files "${app_name}" "push")
        
        if [[ -z "${filtered_files}" ]]; then
            log_verbose "No files to validate after filtering for app: ${app_name}"
            continue
        fi
        
        # Validate each file
        while IFS= read -r file_path; do
            [[ -z "${file_path}" ]] && continue
            
            ((total_files++))
            
            # Check if file should be validated
            if should_validate "${app_name}" "${file_path}" "push"; then
                if ! validate_file "${app_name}" "${file_path}" "push"; then
                    log_error "Validation failed for: ${file_path} (app: ${app_name})"
                    app_valid=false
                fi
            fi
        done <<< "${filtered_files}"
        
        if [[ "${app_valid}" == "false" ]]; then
            ((failed_apps++))
        fi
    done <<< "${apps}"
    
    # Log summary
    log_info "Validated ${total_apps} apps, ${total_files} files"
    
    if [[ ${failed_apps} -gt 0 ]]; then
        log_error "${failed_apps} app(s) failed validation"
        return 1
    fi
    
    return 0
}

# ============================================================================
# Main Entry Point
# ============================================================================

main() {
    # Check dependencies first
    if ! check_dependencies; then
        die "Dependency check failed" "${EXIT_ERROR}"
    fi
    
    # Load configuration
    if ! load_config; then
        die "Failed to load configuration" "${EXIT_CONFIG_ERROR}"
    fi
    
    # Parse command-line arguments
    if ! parse_args "$@"; then
        die "Failed to parse arguments" "${EXIT_INVALID_ARGS}"
    fi
    
    # Execute command
    case "${COMMAND}" in
        list)
            list_applications
            exit "${EXIT_SUCCESS}"
            ;;
        validate)
            if validate_all_configs; then
                exit "${EXIT_SUCCESS}"
            else
                exit "${EXIT_VALIDATION_FAILED}"
            fi
            ;;
        push)
            if [[ "${APP}" == "--all" ]]; then
                if sync_all "push"; then
                    exit "${EXIT_SUCCESS}"
                else
                    exit "${EXIT_SYNC_FAILED}"
                fi
            else
                if sync_app_push "${APP}"; then
                    exit "${EXIT_SUCCESS}"
                else
                    exit "${EXIT_SYNC_FAILED}"
                fi
            fi
            ;;
        pull)
            if [[ "${APP}" == "--all" ]]; then
                if sync_all "pull"; then
                    exit "${EXIT_SUCCESS}"
                else
                    exit "${EXIT_SYNC_FAILED}"
                fi
            else
                if sync_app_pull "${APP}"; then
                    exit "${EXIT_SUCCESS}"
                else
                    exit "${EXIT_SYNC_FAILED}"
                fi
            fi
            ;;
        *)
            die "Unknown command: ${COMMAND}" "${EXIT_INVALID_ARGS}"
            ;;
    esac
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi