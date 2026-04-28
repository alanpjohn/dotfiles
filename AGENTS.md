# AGENTS.md — Dotfiles Repository

## Repository Layout

```
~/Documents/dotfiles/           # Git repo root — must contain dotfiles.toml + .git/
├── dotfiles.toml               # Sync config (TOML). Read by Python CLI.
├── utils/                      # Python project (uv-managed)
│   ├── pyproject.toml          # hatchling build, pytest config
│   ├── dotfiles/               # Main package
│   │   ├── cli.py              # Typer entry point: dotfiles.cli:app
│   │   ├── config.py           # TOML loading, repo root discovery
│   │   ├── sync.py             # Core sync engine
│   │   ├── filters.py          # Glob matching, gitignore
│   │   ├── backup.py           # Backup create/restore
│   │   ├── path_utils.py       # Path resolution
│   │   ├── wallpaper.py        # Matugen integration
│   │   └── logging_utils.py    # Rich console output
│   └── tests/                  # 120+ mock-only unit tests
│       └── conftest.py         # Shared fixtures + autouse state reset
├── tmux/ zed/ ghostty/ nvim/   # Actual dotfile directories synced by the tool
│   opencode/ fish/ matugen/
└── .backups/                   # Backup directory (gitignored)
```

## Working in this Repo

### Always use `uv`, never `pip`

```bash
cd ~/Documents/dotfiles/utils
uv sync --extra dev              # Install deps + pytest
uv run pytest tests/ -v          # Run all tests
uv run dotfiles --help           # Run CLI in dev mode
uv run dotfiles push --dry-run   # Safe preview
```

### Critical: Config Discovery

The CLI **must** find `dotfiles.toml` at a repo root containing `.git/`. It walks upward from `utils/dotfiles/__file__` until both exist. If you create a temp repo for testing, set:

```bash
export DOTFILES_REPO_DIR=/path/to/repo
```

The repo must contain both `dotfiles.toml` (valid TOML) and `.git/` (directory).

### Tests are Mock-Only

- **No real filesystem**, **no git subprocess**, **no matugen** during tests
- `tmp_repo_root` fixture creates a fake repo with `.git/` + `dotfiles.toml`
- `capture_logging` fixture monkeypatches logging — but you **must also patch** `dotfiles.sync.*` and `dotfiles.backup.*` because those modules import logging functions directly
- `mock_get_source_files` patches both `dotfiles.filters.get_source_files` **and** `dotfiles.sync.get_source_files` (sync.py imports it directly)
- Module-level caches (`config._repo_root_cache`, `config._config_cache`, `filters._git_available`) are reset by an `autouse` fixture in `conftest.py`

### Test Gotchas

| Problem | Cause | Fix |
|---------|-------|-----|
| Config loads real repo config instead of test config | `DOTFILES_REPO_DIR` not set | Use `tmp_repo_root` fixture |
| Logging assertions fail in sync/backup tests | `sync.py`/`backup.py` import logging functions directly | Patch both `dotfiles.logging_utils.X` and `dotfiles.sync.X` |
| `get_source_files` mock doesn't affect sync | `sync.py` imports it directly | Patch `dotfiles.sync.get_source_files` too |
| `_verbose_enabled` test fails | Import-time value capture | Access via `dotfiles.logging_utils._verbose_enabled` module attribute |
| Wallpaper tests fail without matugen | Missing CLI dependency | Expected — tests skip with `@pytest.mark.skipif` |

### Adding a New Sync Application

1. Create the config directory in the repo root (e.g., `mkdir -p ~/Documents/dotfiles/myapp`)
2. Add entry to `dotfiles.toml` at repo root (NOT in `utils/`):
   ```toml
   [[applications]]
   name = "myapp"
   type = "directory"
   repo_path = "myapp"
   config_path = "myapp"
   recursive = true
   exclude = ["*.backup"]
   ```
3. Verify: `uv run dotfiles list --verbose`
4. Test dry-run: `uv run dotfiles push myapp --dry-run`

### Key Files to Read Before Changes

| Task | Read First |
|------|-----------|
| Add CLI command | `utils/dotfiles/cli.py` |
| Change sync behavior | `utils/dotfiles/sync.py` |
| Change config format | `utils/dotfiles/config.py` + `dotfiles.toml` |
| Change file filtering | `utils/dotfiles/filters.py` |
| Add tests | `utils/tests/conftest.py` |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Invalid arguments (Typer/Click default) |
| 3 | Config error (`ConfigError`) |
| 4 | Sync failure (partial) |
