# Dotfiles Sync Script

The Dotfiles Sync Script is a powerful bash utility designed to synchronize configuration files (dotfiles) between a git repository and the user's `~/.config` directory. It provides bidirectional sync support, allowing you to push configurations from your repository to your home directory or pull changes from your home directory back into the repository.

This script is particularly useful for managing configuration files across multiple machines or for backing up your dotfiles to a git repository. It supports various configuration formats, handles file renaming between repository and config directories, and includes features like dry-run mode, backup creation, and JSON validation.

## Features

The script includes a comprehensive set of features designed to make dotfile management simple and reliable:

- **Two-way sync (push/pull)**: Synchronize files in either direction between your repository and `~/.config`. Push updates from the repository to your home directory, or pull changes from your home directory back into the repository.

- **File renaming support**: The script supports mapping different filenames between the repository and config directories. This is useful when the same configuration file has different names in different contexts.

- **Dry-run mode**: Preview what would happen during a sync operation without making any changes. This allows you to verify the expected behavior before committing to the sync.

- **Backup creation**: Before overwriting any existing file, the script automatically creates a backup with a configurable suffix (default: `.backup`). You can restore from these backups if needed.

- **.gitignore support**: The script can respect your repository's `.gitignore` file and skip syncing files that are ignored by git. This prevents accidentally syncing sensitive or machine-specific files.

- **JSON/JSONC validation**: Built-in validation for JSON and JSONC (JSON with Comments) files. The script can validate configuration files before syncing to catch syntax errors early.

- **Include/exclude patterns**: Fine-grained control over which files are synchronized using glob patterns. You can specify which files to include and which to exclude for each application.

- **Recursive directory sync**: Support for syncing entire directory trees with the option to enable recursive mode for applications that store their configurations in subdirectories.

- **Color-coded output**: When running in a terminal that supports it, the script provides color-coded output for easy reading of status messages, warnings, and errors.

- **Verbose and quiet modes**: Control the verbosity of output with `--verbose` (enabled by default) and `--quiet` options.

- **Force sync option**: Override the default behavior that skips files when the destination is newer than the source using the `--force` flag.

## Requirements

Before using the Dotfiles Sync Script, ensure your system meets the following requirements:

### bash 4.0 or higher

The script uses bash features such as associative arrays and process substitution. Most modern Linux distributions include bash 4.0 or later by default. You can check your bash version by running:

```bash
bash --version
```

### jq (JSON parser)

jq is required for parsing the configuration file and validating JSON files. It is a lightweight command-line JSON processor.

**Installation on Ubuntu/Debian:**

```bash
sudo apt-get install jq
```

**Installation on Arch Linux/CachyOS:**

```bash
sudo pacman -S jq
```

**Installation on macOS (with Homebrew):**

```bash
brew install jq
```

**Installation on Fedora/RHEL:**

```bash
sudo dnf install jq
```

### git (optional)

git is optional and only required if you want to enable `.gitignore` support. Without git, the script will simply skip the gitignore-related functionality.

**Installation on Ubuntu/Debian:**

```bash
sudo apt-get install git
```

**Installation on Arch Linux/CachyOS:**

```bash
sudo pacman -S git
```

## Installation

Follow these steps to install the Dotfiles Sync Script:

### Step 1: Navigate to the scripts directory

```bash
cd ~/Documents/dotfiles/scripts
```

### Step 2: Make the script executable

```bash
chmod +x sync_dotfiles.sh
```

### Step 3: (Optional) Add to PATH for system-wide access

If you want to run the script from anywhere, you can create a symbolic link:

```bash
sudo ln -s $(pwd)/sync_dotfiles.sh /usr/local/bin/dotfiles-sync
```

Alternatively, you can add the scripts directory to your PATH by adding this line to your shell configuration file (e.g., `~/.bashrc` or `~/.zshrc`):

```bash
export PATH="$HOME/Documents/dotfiles/scripts:$PATH"
```

Then reload your shell configuration:

```bash
source ~/.bashrc  # for bash
# or
source ~/.zshrc   # for zsh
```

### Step 4: Verify installation

Run the following command to verify the script is working:

```bash
./sync_dotfiles.sh --help
```

You should see the help message with all available commands and options.

## Quick Start

Get started with the Dotfiles Sync Script using these basic commands:

### List configured applications

View all applications that are configured for synchronization:

```bash
./sync.sh list
```

This will display all configured application names, such as zed, ghostty, nvim, starship, and opencode.

### Preview changes with dry-run

Before making any changes, preview what would be synchronized:

```bash
./sync.sh push --dry-run
```

This shows exactly which files would be copied or updated without actually making any changes.

### Push a configuration to ~/.config

Push the configuration for a specific application from the repository to your home directory:

```bash
./sync.sh push zed
```

This will sync the zed editor configuration from the repository to `~/.config/zed`.

### Pull a configuration from ~/.config

Pull changes from your home directory back into the repository:

```bash
./sync.sh pull nvim
```

This will sync the neovim configuration from `~/.config/nvim` back to the repository.

### Sync all configurations

Push or pull all configured applications at once:

```bash
./sync.sh push --all
./sync.sh pull --all
```

## Configuration

The script uses a JSON configuration file (`sync-config.json`) to define which applications to sync and how to sync them. This section explains each configuration field in detail.

### Configuration File Structure

The configuration file consists of two main sections: `global` settings and `applications` array.

```json
{
  "global": {
    "backup_suffix": ".backup",
    "default_validate_json": true,
    "respect_gitignore": true
  },
  "applications": [
    {
      "name": "app_name",
      "type": "directory",
      "repo_path": "app",
      "config_path": "app",
      "recursive": true,
      "file_mappings": [
        {
          "repo_name": "settings.jsonc",
          "config_name": "settings.json",
          "validate": false
        }
      ],
      "exclude": [
        "*.backup"
      ],
      "include": [
        "*.jsonc"
      ]
    }
  ]
}
```

### Global Settings

The `global` section contains settings that apply to all applications:

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| `backup_suffix` | string | Suffix appended to backup files | `.backup` |
| `default_validate_json` | boolean | Enable JSON validation by default | `true` |
| `respect_gitignore` | boolean | Respect .gitignore when syncing | `true` |

### Application Entry Fields

Each application in the `applications` array requires the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the application |
| `type` | string | Yes | Either `"directory"` or `"file"` |
| `repo_path` | string | Yes | Path to the configuration in the repository (relative to repo root) |
| `config_path` | string | Yes | Path to the configuration in `~/.config` (relative to `~/.config`) |
| `recursive` | boolean | No | Enable recursive directory sync (for directory type) |
| `file_mappings` | array | No | Array of filename mappings between repo and config |
| `exclude` | array | No | Array of glob patterns to exclude |
| `include` | array | No | Array of glob patterns to include |

### Field Descriptions

**name**: A unique identifier for the application. This is used as the application identifier when running commands (e.g., `./sync.sh push nvim`).

**type**: Specifies whether the configuration is a single file (`"file"`) or a directory (`"directory"`). For directory types, the script can sync multiple files.

**repo_path**: The path to the configuration directory or file relative to the repository root. For example, if your repository is at `~/Documents/dotfiles` and your zed config is in `~/Documents/dotfiles/zed`, the repo_path would be `zed`.

**config_path**: The path to the configuration relative to `~/.config`. For example, if your zed config should go to `~/.config/zed`, the config_path would be `zed`.

**recursive**: Only applicable for directory-type applications. When set to `true`, the script will recursively sync all files in subdirectories. When `false` or omitted, only files in the immediate directory are synced.

**file_mappings**: An array of objects that map filenames from the repository to their corresponding names in `~/.config`. This is useful when the same configuration file has different names in different contexts. Each mapping can have:

| Mapping Field | Type | Description |
|---------------|------|-------------|
| `repo_name` | string | The filename in the repository |
| `config_name` | string | The corresponding filename in `~/.config` |
| `validate` | boolean | Override validation setting for this specific file |

**exclude**: An array of glob patterns for files that should be excluded from syncing. Patterns follow bash glob syntax (e.g., `*.json`, `*.backup`, `dir/`).

**include**: An array of glob patterns for files that should be included in syncing. If include patterns are specified, only files matching these patterns will be synced. If empty, all files are considered (subject to exclude patterns).

### Configuration Examples

**Example 1: Simple directory sync**

```json
{
  "name": "nvim",
  "type": "directory",
  "repo_path": "nvim",
  "config_path": "nvim",
  "recursive": true,
  "exclude": [
    "lazy-lock.json",
    "*.backup"
  ]
}
```

This configuration syncs the entire nvim directory recursively, excluding lock files and backup files.

**Example 2: File with renaming**

```json
{
  "name": "starship",
  "type": "file",
  "repo_path": "starship/starship.toml",
  "config_path": "starship.toml"
}
```

This configuration syncs a single file, mapping `starship/starship.toml` in the repository to `starship.toml` in `~/.config`.

**Example 3: Directory with file mappings**

```json
{
  "name": "zed",
  "type": "directory",
  "repo_path": "zed",
  "config_path": "zed",
  "recursive": true,
  "file_mappings": [
    {
      "repo_name": "settings.jsonc",
      "config_name": "settings.json"
    }
  ],
  "exclude": [
    "*.backup"
  ],
  "include": [
    "*.jsonc",
    "*.json",
    "themes/"
  ]
}
```

This configuration syncs the zed directory, but maps `settings.jsonc` in the repository to `settings.json` in `~/.config`. It only includes JSON files and the themes directory.

## Usage

This section provides a detailed command reference for the Dotfiles Sync Script.

### Command Syntax

```bash
./sync.sh [COMMAND] [APP] [OPTIONS]
```

### Commands

The script supports the following commands:

**push** - Sync from repository to ~/.config

Pushes configuration files from the repository to `~/.config`. The repository is considered the source of truth.

```bash
./sync.sh push zed              # Push zed config to ~/.config
./sync.sh push --all            # Push all configured apps
./sync.sh push nvim --dry-run   # Preview push without making changes
```

**pull** - Sync from ~/.config to repository

Pulls configuration files from `~/.config` to the repository. The `~/.config` directory is considered the source of truth.

```bash
./sync.sh pull nvim             # Pull nvim config from ~/.config
./sync.sh pull --all            # Pull all configured apps
./sync.sh pull ghostty --dry-run # Preview pull without making changes
```

**list** - List configured applications

Lists all applications that are configured in `sync-config.json`.

```bash
./sync.sh list
```

**validate** - Validate configurations

Validates all JSON and JSONC configuration files without syncing. This is useful for checking configuration syntax before pushing or pulling.

```bash
./sync.sh validate
```

### Options

**--dry-run**

Show what would be synchronized without making any changes. This is useful for previewing the effects of a sync operation.

```bash
./sync.sh push zed --dry-run
./sync.sh pull nvim --dry-run
```

**--force**

Overwrite destination files even if the destination is newer than the source. By default, the script skips syncing when the destination is newer to prevent accidental overwriting of changes.

```bash
./sync.sh push zed --force
```

**--verbose**

Enable verbose output (this is the default). Shows detailed information about each sync operation.

```bash
./sync.sh push zed --verbose
```

**--quiet**

Disable verbose output. Only shows essential information like errors and final sync counts.

```bash
./sync.sh push zed --quiet
```

**--help**

Display the help message with all available commands and options.

```bash
./sync.sh --help
```

### Application Names

The following application names are available (as defined in your sync-config.json):

- `zed` - Zed editor configuration
- `ghostty` - Ghostty terminal configuration
- `nvim` - Neovim configuration
- `starship` - Starship prompt configuration
- `opencode` - Opencode configuration
- `--all` - All applications (default if no app specified)

### Exit Codes

The script uses the following exit codes:

| Exit Code | Description |
|-----------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Configuration error |
| 4 | Sync failed |
| 5 | Validation failed |

## Examples

Here are several real-world examples demonstrating different use cases:

### Example 1: Initial setup - push all configs

After cloning your dotfiles repository on a new machine, push all configurations to `~/.config`:

```bash
./sync.sh push --all
```

Expected output:

```
Synced X files for zed
Synced X files for ghostty
Synced X files for nvim
Synced X files for starship
Synced X files for opencode
Total apps with failures: 0
```

This will create all necessary directories in `~/.config` and copy the configuration files.

### Example 2: Updating after editing in ~/.config

You've made changes to your neovim configuration directly in `~/.config/nvim` and want to save those changes to your repository:

```bash
./sync.sh pull nvim
```

This will copy your changes from `~/.config/nvim` back to the repository.

### Example 3: Testing changes with dry-run

Before making any changes, preview what would happen when pushing your zed configuration:

```bash
./sync.sh push zed --dry-run
```

Sample output:

```
[INFO] Previewing changes for 'zed' (push):

[DRY-RUN] Would copy: /home/alan/Documents/dotfiles/zed/settings.jsonc → /home/alan/.config/zed/settings.json
[DRY-RUN] Would copy: /home/alan/Documents/dotfiles/zed/themes/dark.toml → /home/alan/.config/zed/themes/dark.toml

Summary:
  Would copy: 2 new file(s)
  Would update: 0 existing file(s)
  Would backup: 0 file(s)
```

This shows exactly which files would be created or modified without actually making changes.

### Example 4: Force sync when files differ

You've been working on both the repository and `~/.config` versions of a file, and you want to overwrite the destination with the source version:

```bash
./sync.sh push starship --force
```

The `--force` flag will create a backup of the existing file and overwrite it with the source version.

### Example 5: Adding a new application

To add a new application (e.g., Alacritty terminal) to your sync configuration:

1. First, create the configuration directory in your repository:

```bash
mkdir -p ~/Documents/dotfiles/alacritty
```

2. Add your configuration files to this directory.

3. Edit `sync-config.json` to add the new application:

```json
{
  "name": "alacritty",
  "type": "directory",
  "repo_path": "alacritty",
  "config_path": "alacritty",
  "recursive": false,
  "exclude": [
    "*.backup"
  ]
}
```

4. Verify the new configuration:

```bash
./sync.sh list
```

You should now see "alacritty" in the list of configured applications.

5. Push the new configuration:

```bash
./sync.sh push alacritty
```

### Example 6: Using file mappings for renamed configs

If you need to rename a configuration file when syncing (e.g., `settings.jsonc` in repo becomes `settings.json` in config), configure file mappings:

```json
{
  "name": "myapp",
  "type": "directory",
  "repo_path": "myapp",
  "config_path": "myapp",
  "file_mappings": [
    {
      "repo_name": "settings.jsonc",
      "config_name": "settings.json"
    }
  ]
}
```

Now when you push, `settings.jsonc` in the repository will be synced to `settings.json` in `~/.config`.

### Example 7: Validating configurations before syncing

Before pushing configurations, validate all JSON files to catch any syntax errors:

```bash
./sync.sh validate
```

If validation passes, you can proceed with the sync. If there are errors, they'll be reported with the file path and line number.

## Troubleshooting

This section covers common issues you may encounter and their solutions:

### "jq is required but not installed"

**Problem:** The script fails with an error about jq not being found.

**Solution:** Install jq using your system's package manager:

```bash
# Ubuntu/Debian
sudo apt-get install jq

# Arch/CachyOS
sudo pacman -S jq

# macOS
brew install jq
```

### "Permission denied" error

**Problem:** Getting permission denied errors when trying to create directories or copy files.

**Solution:** Check the permissions on your `~/.config` directory and ensure you have write access:

```bash
ls -la ~/.config
```

If needed, fix permissions:

```bash
chmod 755 ~/.config
```

Also ensure the script is executable:

```bash
chmod +x sync_dotfiles.sh
```

### "File not found" or "No source files found"

**Problem:** The script reports no files found for an application.

**Solution:** Verify the paths in your `sync-config.json`:

1. Check that `repo_path` points to an existing directory/file in your repository
2. Check that `config_path` is correct for `~/.config`
3. Ensure the application name matches exactly (case-sensitive)

You can verify the paths manually:

```bash
ls ~/Documents/dotfiles/zed    # Check repo path
ls ~/.config/zed               # Check config path
```

### JSON validation errors

**Problem:** Validation fails for JSON or JSONC files.

**Solution:** 

1. Check the JSON syntax using jq directly:

```bash
jq empty ~/.config/zed/settings.json
```

2. For JSONC files (JSON with comments), ensure comments use valid syntax:

```json
{
  // This is a valid comment
  "setting": "value"
}
```

3. If validation is too strict, you can disable it for specific files in your `file_mappings`:

```json
"file_mappings": [
  {
    "repo_name": "settings.jsonc",
    "config_name": "settings.json",
    "validate": false
  }
]
```

Or disable JSON validation globally in `sync-config.json`:

```json
"global": {
  "default_validate_json": false
}
```

### "Destination is newer, skipping" message

**Problem:** The script skips syncing because the destination file is newer than the source.

**Solution:** This is expected behavior to prevent overwriting changes. If you intentionally want to overwrite the newer destination, use the `--force` flag:

```bash
./sync.sh push zed --force
```

### Configuration file errors

**Problem:** The script fails to load the configuration file.

**Solution:** Validate your JSON syntax:

```bash
jq empty sync-config.json
```

Common issues include:
- Missing commas between array elements or object properties
- Unquoted keys (JSON keys must be strings)
- Trailing commas (not allowed in JSON)
- Mismatched braces or brackets

### Git-related issues

**Problem:** The script doesn't respect .gitignore or shows warnings about git.

**Solution:** 

1. Ensure git is installed:

```bash
git --version
```

2. If you don't need .gitignore support, you can disable it in `sync-config.json`:

```json
"global": {
  "respect_gitignore": false
}
```

### Dry-run showing unexpected results

**Problem:** The dry-run output doesn't match what you expect.

**Solution:** 

1. Check your include/exclude patterns - make sure the files you want to sync are not excluded
2. Verify file_mappings are correct - the script uses mapped names for destination files
3. Check that recursive setting matches your directory structure

## Contributing

The Dotfiles Sync Script is designed to be extensible. Here's how you can contribute or extend the functionality:

### Adding New Applications

To add a new application to the sync configuration:

1. **Create the repository directory**: Place your configuration files in the appropriate directory within your dotfiles repository.

2. **Edit sync-config.json**: Add a new entry in the applications array with the appropriate configuration.

3. **Test the configuration**: Use dry-run to verify the configuration works as expected:

```bash
./sync.sh push newapp --dry-run
```

### Extending the Script

If you want to add new features or modify existing behavior:

1. **Understand the code structure**: The script is organized into logical sections:
   - Helper Functions (lines 33-121): Logging, colors, error handling
   - Dry-Run Mode Functions (lines 146-331): Preview functionality
   - Validation Functions (lines 498-677): JSON validation
   - Backup Functions (lines 682-822): Backup creation and restoration
   - Configuration Parser (lines 828-945): Reading config file
   - File Filtering Functions (lines 951-1159): Include/exclude logic
   - Path Resolution Functions (lines 1164-1312): Path handling
   - Sync Functions (lines 1318-1693): Core sync logic

2. **Follow existing patterns**: When adding new functionality, follow the existing code style and patterns used in the script.

3. **Test thoroughly**: Always test new features with `--dry-run` before running actual sync operations.

### Reporting Issues

If you encounter bugs or have feature requests:

1. Check the existing configuration for obvious issues
2. Run with `--verbose` for detailed output
3. Use `--dry-run` to understand what the script is doing
4. Verify your `sync-config.json` has valid JSON syntax

## License

This script is provided as-is for personal dotfile management. You are free to modify and adapt it for your own use.

---

For more information and updates, refer to the source code in `sync_dotfiles.sh` or run `./sync.sh --help`.