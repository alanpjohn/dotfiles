"""Path resolution helpers for the dotfiles sync tool."""

from __future__ import annotations

import os
from pathlib import Path

from dotfiles.config import AppConfig, discover_repo_root


def resolve_repo_path(app: AppConfig, relative: str = "") -> Path:
    """Resolve absolute path in repository for the given app and relative path.

    Args:
        app: Application configuration.
        relative: Relative path within the app's repo directory (can be empty).

    Returns:
        Absolute path like /home/user/dotfiles/zed/settings.jsonc

    Example:
        >>> resolve_repo_path(zd_app, "settings.jsonc")
        Path("/home/user/dotfiles/zed/settings.jsonc")
    """
    repo_root = discover_repo_root()
    result = repo_root / app.repo_path
    if relative:
        result = result / relative
    return result.resolve()


def resolve_config_path(app: AppConfig, relative: str = "") -> Path:
    """Resolve absolute path in ~/.config for the given app and relative path.

    Args:
        app: Application configuration.
        relative: Relative path within the app's config directory (can be empty).

    Returns:
        Absolute path like /home/user/.config/zed/settings.json

    Example:
        >>> resolve_config_path(zd_app, "settings.json")
        Path("/home/user/.config/zed/settings.json")
    """
    config_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    result = Path(config_dir) / app.config_path
    if relative:
        result = result / relative
    return result.resolve()


def resolve_source_dir(app: AppConfig, direction: str) -> Path:
    """Return the source base directory for a sync operation.

    For push: source is in the repository.
    For pull: source is in ~/.config.

    Args:
        app: Application configuration.
        direction: Either "push" or "pull".

    Returns:
        Absolute path to the source directory.
    """
    if direction == "push":
        return resolve_repo_path(app)
    elif direction == "pull":
        return resolve_config_path(app)
    else:
        raise ValueError(f"Invalid direction: {direction!r}. Must be 'push' or 'pull'.")
