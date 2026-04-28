"""Configuration loading and validation for dotfiles."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FileMapping:
    """Maps a filename in the repo to a filename in ~/.config."""

    repo_name: str
    config_name: str


@dataclass
class AppConfig:
    """Configuration for a single application to sync."""

    name: str
    type: str  # "directory" or "file"
    repo_path: str
    config_path: str
    recursive: bool = False
    file_mappings: list[FileMapping] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)


@dataclass
class GlobalConfig:
    """Global configuration settings."""

    backup_directory: str = ".backups"
    backup_suffix: str = ".backup"
    respect_gitignore: bool = True


@dataclass
class DotfilesConfig:
    """Full configuration (global + applications)."""

    global_config: GlobalConfig
    applications: list[AppConfig]


# ---------------------------------------------------------------------------
# Repository root discovery
# ---------------------------------------------------------------------------

_repo_root_cache: Path | None = None
_config_cache: DotfilesConfig | None = None


def discover_repo_root() -> Path:
    """Walk upward from this file's location until both dotfiles.toml and .git are found.

    The algorithm walks up from the package directory (dotfiles/) until a
    directory contains both ``dotfiles.toml`` and ``.git``.

    If the environment variable ``DOTFILES_REPO_DIR`` is set, it is used
    directly but validated to contain both markers.

    Raises :exc:`ConfigError` if the repo root cannot be located.
    """
    global _repo_root_cache
    if _repo_root_cache is not None:
        return _repo_root_cache

    # Env var override
    env_dir = os.environ.get("DOTFILES_REPO_DIR")
    if env_dir:
        env_path = Path(env_dir).resolve()
        _validate_repo_root(env_path)
        _repo_root_cache = env_path
        return env_path

    # Walk upward from the package directory
    current = Path(__file__).resolve().parent
    while True:
        if _is_repo_root(current):
            _repo_root_cache = current
            return current
        parent = current.parent
        if parent == current:
            raise ConfigError(
                "Cannot locate dotfiles repository.\n"
                "Run from within the repo or set DOTFILES_REPO_DIR environment variable."
            )
        current = parent


def _is_repo_root(path: Path) -> bool:
    """Check if path contains both dotfiles.toml and .git."""
    return (path / "dotfiles.toml").is_file() and (path / ".git").is_dir()


def _validate_repo_root(path: Path) -> None:
    """Validate that the given path contains required markers."""
    if not _is_repo_root(path):
        missing = []
        if not (path / "dotfiles.toml").is_file():
            missing.append("dotfiles.toml")
        if not (path / ".git").is_dir():
            missing.append(".git/")
        raise ConfigError(
            f"DOTFILES_REPO_DIR={path} does not contain required files: {', '.join(missing)}"
        )


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

def load_config() -> DotfilesConfig:
    """Load and validate configuration from dotfiles.toml.

    Returns the full parsed configuration. Results are cached.

    Raises :exc:`ConfigError` on any validation failure.
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    repo_root = discover_repo_root()
    config_path = repo_root / "dotfiles.toml"

    if not config_path.is_file():
        raise ConfigError(
            f"Configuration file not found: {config_path}\n"
            "Create a dotfiles.toml file in the repository root."
        )

    try:
        raw = config_path.read_bytes()
        data: dict[str, Any] = tomllib.loads(raw.decode("utf-8"))  # type: ignore[assignment]
    except Exception as exc:
        raise ConfigError(f"Failed to parse {config_path}: {exc}") from exc

    # Parse global settings
    global_raw: dict[str, Any] = data.get("global", {})
    global_config = GlobalConfig(
        backup_directory=global_raw.get("backup_directory", ".backups"),
        backup_suffix=global_raw.get("backup_suffix", ".backup"),
        respect_gitignore=global_raw.get("respect_gitignore", True),
    )

    # Parse applications
    apps_raw: list[dict[str, Any]] = data.get("applications", [])
    if not apps_raw:
        raise ConfigError("No applications defined in dotfiles.toml.")

    applications: list[AppConfig] = []
    for entry in apps_raw:
        # Required fields
        name = entry.get("name")
        app_type = entry.get("type")
        repo_path = entry.get("repo_path")
        config_path = entry.get("config_path")

        if not all([name, app_type, repo_path, config_path]):
            raise ConfigError(
                f"Application entry missing required fields (name, type, repo_path, config_path): {entry}"
            )

        if app_type not in ("directory", "file"):
            raise ConfigError(
                f"Application '{name}' has invalid type '{app_type}'. Must be 'directory' or 'file'."
            )

        # File mappings
        file_mappings: list[FileMapping] = []
        mappings_raw: list[dict[str, str]] = entry.get("file_mappings", [])
        for m in mappings_raw:
            repo_name = m.get("repo_name", "")
            config_name = m.get("config_name", "")
            if repo_name and config_name:
                if repo_name == config_name:
                    from dotfiles.logging_utils import warning
                    warning(
                        f"Identity file mapping detected for '{name}': "
                        f"repo_name='{repo_name}' == config_name='{config_name}'"
                    )
                file_mappings.append(FileMapping(repo_name=repo_name, config_name=config_name))

        applications.append(
            AppConfig(
                name=name,
                type=app_type,
                repo_path=repo_path,
                config_path=config_path,
                recursive=entry.get("recursive", False),
                file_mappings=file_mappings,
                exclude=entry.get("exclude", []),
                include=entry.get("include", []),
            )
        )

    config = DotfilesConfig(global_config=global_config, applications=applications)
    _config_cache = config
    return config


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def list_apps() -> list[AppConfig]:
    """Return all configured applications."""
    return load_config().applications


def get_app(name: str) -> AppConfig:
    """Return a single application config by name.

    Raises :exc:`ConfigError` if the app is not found.
    """
    config = load_config()
    for app in config.applications:
        if app.name == name:
            return app
    raise ConfigError(
        f"Application '{name}' not found in config. "
        f"Available: {', '.join(a.name for a in config.applications)}"
    )


def get_global(key: str, default: Any = None) -> Any:
    """Return a global setting value, with an optional default."""
    config = load_config()
    return getattr(config.global_config, key, default)


def get_repo_root() -> Path:
    """Return the repository root directory."""
    return discover_repo_root()
