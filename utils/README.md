# Dotfiles CLI

A unified CLI tool for managing dotfiles sync and wallpaper organization. Migrated from the legacy bash sync script (`scripts/sync_dotfiles.sh`) to a modern Python/Typer CLI.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
cd ~/Documents/dotfiles/utils
uv tool install --editable .
```

This makes the `dotfiles` command available on your PATH.

## Quick Start

```bash
# Show help
dotfiles --help

# List configured applications
dotfiles list

# Preview what would be synced (dry-run)
dotfiles push --dry-run

# Push all configs to ~/.config
dotfiles push

# Push a specific app
dotfiles push nvim

# Pull changes from ~/.config back to repo
dotfiles pull fish

# Show extended manual
dotfiles help
```

## Command Reference

### `dotfiles push [APP]`

Sync configuration files from the repository to `~/.config`.

- `APP`: Optional application name. If omitted, syncs all applications.
- `--all`: Explicit flag for syncing all (same as omitting APP).
- `--dry-run`: Preview changes without making any modifications.
- `--force`: Overwrite destination even if destination is newer.

```bash
dotfiles push            # Push all apps
dotfiles push nvim       # Push only nvim
dotfiles push --dry-run  # Preview all pushes
dotfiles push zed --force
```

### `dotfiles pull [APP]`

Sync configuration files from `~/.config` back to the repository.

Same options as `push`: `--all`, `--dry-run`, `--force`.

```bash
dotfiles pull nvim       # Pull nvim config from ~/.config
dotfiles pull --dry-run  # Preview all pulls
```

### `dotfiles list`

List all configured applications.

- Default: Plain names, one per line (bash-compatible).
- `--verbose`: Rich table with detailed information.
- `--json`: JSON array for machine parsing.

```bash
dotfiles list
dotfiles list --verbose
dotfiles list --json
```

### `dotfiles wallpaper list`

List wallpapers with their Matugen source colors and hue angles.
Also identifies files outside the indexed naming pattern.

```bash
dotfiles wallpaper list
dotfiles wallpaper list --pictures-dir ~/Pictures/OtherWallpapers
dotfiles wallpaper list --jobs 4
```

### `dotfiles wallpaper sort`

Sort wallpapers by source color hue into rainbow order.
Outputs timestamped copies and cleans up output from previous runs.

A warning about Desktop Manager Settings configuration is shown after sorting.

```bash
dotfiles wallpaper sort
dotfiles wallpaper sort --dry-run
dotfiles wallpaper sort --jobs 16
```

### `dotfiles help`

Show extended manual (summary of this README).

```bash
dotfiles help
dotfiles help --full  # Show entire README in terminal
```

### Global Options

- `--version`: Show version and exit.
- `--verbose`: Enable verbose output (default).
- `--quiet`: Suppress verbose output.
- `--install-completion`: Install shell completion for bash/zsh/fish.

## Configuration

The CLI reads configuration from `dotfiles.toml` at the repository root.
This file was converted from the legacy `scripts/sync-config.json`.

### Global Settings

```toml
[global]
backup_directory = ".backups"
backup_suffix = ".backup"
respect_gitignore = true
```

### Application Entries

Each application is defined as a `[[applications]]` table:

```toml
[[applications]]
name = "nvim"
type = "directory"       # "directory" or "file"
repo_path = "nvim"       # Path relative to repo root
config_path = "nvim"     # Path relative to ~/.config
recursive = true         # Sync subdirectories
exclude = ["lazy-lock.json", "tags", "spell/"]

[[applications]]
name = "zed"
type = "directory"
repo_path = "zed"
config_path = "zed"
recursive = true
include = ["*.jsonc", "*.json", "tasks.json"]
exclude = ["*.backup", "settings.json", "themes/"]

[[applications.file_mappings]]
repo_name = "settings.jsonc"
config_name = "settings.json"

[[applications.file_mappings]]
repo_name = "tasks.jsonc"
config_name = "tasks.json"
```

### Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the application |
| `type` | string | Yes | `"directory"` or `"file"` |
| `repo_path` | string | Yes | Path in the repository |
| `config_path` | string | Yes | Path in `~/.config` |
| `recursive` | boolean | No | Enable recursive directory sync (default: false) |
| `file_mappings` | array of tables | No | Map filenames between repo and config (matched on basename only) |
| `exclude` | array of strings | No | Glob patterns to exclude |
| `include` | array of strings | No | Glob patterns to include (whitelist mode) |

### Pattern Matching

- `*.ext`: Matches basename only (e.g., `*.jsonc` matches `foo.jsonc`)
- `dir/`: Trailing slash marks a directory pattern (excludes the entire directory)
- `*text*`: Matches basename containing `text`

Include/exclude patterns are matched against the **source file's basename**.

## File Mappings

File mappings allow renaming files between the repository and `~/.config`.
Mappings are matched on **basename only** — nested files in subdirectories
preserve their directory structure with only the leaf filename potentially renamed.

For push: `repo_name` → `config_name`
For pull: `config_name` → `repo_name`

## Backups

Before overwriting any existing file, the CLI creates a backup. Backups are stored
in `.backups/<app_name>/<relative_path>.backup` within the repository.

The backup directory and suffix are configurable in `[global]` settings.

## Shell Completion

```bash
dotfiles --install-completion bash
dotfiles --install-completion zsh
dotfiles --install-completion fish
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Configuration error (missing file, invalid format) |
| 4 | Sync failure (partial - some files failed) |

## Config Discovery

The CLI discovers the repository root by walking upward from its package location
until a directory containing both `dotfiles.toml` and `.git` is found.
You can override this with the `DOTFILES_REPO_DIR` environment variable.

## Migration from Bash Script

The legacy bash sync tool (`scripts/sync_dotfiles.sh`) has been deprecated in
favor of this Python CLI. The configuration format has been migrated from
`sync-config.json` to `dotfiles.toml` (TOML).

### Key Differences

- Config is now TOML instead of JSON
- The CLI name is `dotfiles` instead of `sync.sh`
- `--all` flag is now an explicit option (but omitting the APP argument also syncs all)
- Dry-run output format is semantically equivalent but may differ in exact formatting
- Backups use the same directory structure (`.backups/`)

### Legacy Backups

Legacy backups from the bash script in `.backups/` are compatible with the new CLI.
If you no longer need them, they can be safely removed.

## Development

### Running Tests

The project includes a comprehensive unit test suite (120+ tests) using pytest:

```bash
cd ~/Documents/dotfiles/utils
uv run pytest tests/ -v
```

All tests use mocked dependencies — no real filesystem, git, or matugen calls are made during testing. The test suite covers:

- **Config parsing & validation** (`test_config.py`) — TOML parsing, discovery, caching, error cases
- **Path resolution** (`test_path_utils.py`) — repo/config path resolution, XDG_CONFIG_HOME handling
- **File filtering** (`test_filters.py`) — glob matching, include/exclude, gitignore logic
- **Backup operations** (`test_backup.py`) — path computation, create/restore/remove
- **Sync engine** (`test_sync.py`) — file mappings, dry-run/live modes, force flag
- **Wallpaper management** (`test_wallpaper.py`) — hue computation, matugen mocking, cleanup
- **CLI commands** (`test_cli.py`) — Typer CLI runner, exit codes, command wiring
- **Logging** (`test_logging_utils.py`) — verbose suppression

### Project Structure

```
utils/
├── pyproject.toml                  # Project config, dependencies, pytest settings
├── dotfiles/                       # Main Python package
│   ├── __init__.py                 # Version string
│   ├── cli.py                      # Typer CLI app (all commands)
│   ├── config.py                   # TOML config loading, validation, discovery
│   ├── sync.py                     # Core sync engine (push/pull/preview)
│   ├── filters.py                  # Glob matching, gitignore, source enumeration
│   ├── backup.py                   # Backup create/restore/remove
│   ├── path_utils.py               # Path resolution helpers
│   ├── wallpaper.py                # Wallpaper list/sort (matugen integration)
│   └── logging_utils.py            # Rich-based colored output
├── tests/                          # Test suite
│   ├── conftest.py                 # Shared fixtures, state reset, mock helpers
│   ├── test_config.py
│   ├── test_path_utils.py
│   ├── test_filters.py
│   ├── test_backup.py
│   ├── test_sync.py
│   ├── test_wallpaper.py
│   ├── test_logging_utils.py
│   └── test_cli.py
├── uv.lock                         # Dependency lockfile
└── README.md                       # This file
```

### Architecture

The CLI is built on a layered architecture:

```
cli.py (Typer commands)
  ├── push/pull/list/help   → sync.py
  ├── wallpaper list/sort   → wallpaper.py
  └── global callback       → logging_utils.py

sync.py (core engine)
  ├── sync_file()           → backup.py, logging_utils.py
  ├── sync_app_push/pull()  → filters.py, path_utils.py
  └── sync_all()            → config.py

filters.py (file selection)
  ├── matches_glob()        (pure logic)
  ├── is_gitignored()       → subprocess (git)
  ├── should_sync_file()    → matches_glob, is_gitignored
  └── get_source_files()    → path_utils.py, should_sync_file

config.py (configuration)
  ├── discover_repo_root()  (walk-up algorithm)
  ├── load_config()         → tomllib
  └── AppConfig dataclass
```

### Key Design Decisions

- **Typer** for CLI framework — type-hint based, built on Click, provides auto-generated help and shell completion
- **Rich** for output — colored terminal output with tables, progress bars, and TTY detection
- **TOML config** — human-readable format with comments, consistent with `pyproject.toml`
- **Config discovery** — walks upward from package location until `dotfiles.toml` + `.git` found
- **Mock-only tests** — all tests use mocked filesystem/external deps; no integration tests needed for personal-use CLI

## Troubleshooting

### "Cannot locate dotfiles repository"
Run from within the repository or set `DOTFILES_REPO_DIR`.

### "matugen is required"
The `wallpaper` commands require [matugen](https://github.com/InioX/matugen).
Install it if you want to use wallpaper features.

### Config validation errors
Run `dotfiles list --verbose` to see all configured apps. Check your TOML syntax.
