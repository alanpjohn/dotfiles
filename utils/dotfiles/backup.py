"""Backup creation, restoration, and cleanup for sync operations."""

from __future__ import annotations

import shutil
from pathlib import Path

from dotfiles.config import AppConfig, discover_repo_root, get_global
from dotfiles.path_utils import resolve_repo_path, resolve_config_path
from dotfiles.logging_utils import verbose, dry_run_log, warning


def get_backup_path(filepath: Path, app_name: str, direction: str) -> Path:
    """Compute the backup path for a file/directory being overwritten.

    The file being backed up is the **destination** of the sync operation.
    - For push: dest is in ~/.config
    - For pull: dest is in the repo

    Backup path format: ``{repo_root}/{backup_dir}/{app_name}/{relative_path}{suffix}``

    Args:
        filepath: Absolute path to the destination file being backed up.
        app_name: Name of the application.
        direction: "push" or "pull".

    Returns:
        Absolute path where the backup should be stored.
    """
    repo_root = discover_repo_root()
    backup_dir = str(get_global("backup_directory", ".backups"))
    backup_suffix = str(get_global("backup_suffix", ".backup"))

    # Determine the source base directory for relative path computation
    if direction == "push":
        source_base = str(resolve_config_path(AppConfig(
            name=app_name, type="directory", repo_path="", config_path="",
        ), "")).rstrip("/")
    else:
        # Pull: destination is in the repo
        source_base = str(resolve_repo_path(AppConfig(
            name=app_name, type="directory", repo_path="", config_path="",
        ), "")).rstrip("/")

    # Compute relative path from the source base
    filepath_str = str(filepath)
    source_base_str = source_base
    # Prevent empty source_base causing issues
    if not source_base_str or source_base_str == ".":
        relative_path = str(Path(filepath_str).name)
    elif filepath_str.startswith(source_base_str + "/"):
        relative_path = filepath_str[len(source_base_str) + 1:]
    elif filepath_str.startswith(source_base_str):
        relative_path = filepath_str[len(source_base_str):].lstrip("/")
    else:
        # Fallback: use basename
        relative_path = str(Path(filepath_str).name)

    backup_path = repo_root / backup_dir / app_name / f"{relative_path}{backup_suffix}"
    return backup_path


def create_backup(
    filepath: Path,
    app_name: str,
    direction: str,
    dry_run: bool = False,
) -> bool:
    """Create a backup of a file or directory before overwriting.

    Args:
        filepath: Absolute path to the file/directory to back up (the destination).
        app_name: Application name.
        direction: "push" or "pull".
        dry_run: If True, only log what would happen.

    Returns:
        True on success, False on failure.
    """
    if not filepath.exists():
        return False

    backup_path = get_backup_path(filepath, app_name, direction)

    if dry_run:
        dry_run_log("Would create backup", str(filepath), str(backup_path))
        return True

    # Create parent directories for the backup
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing backup if present
    if backup_path.exists():
        if backup_path.is_dir():
            shutil.rmtree(backup_path)
        else:
            backup_path.unlink()

    try:
        if filepath.is_dir():
            shutil.copytree(filepath, backup_path, symlinks=False)
        else:
            shutil.copy2(filepath, backup_path)
        verbose(f"Creating backup: {filepath} \u2192 {backup_path}")
        return True
    except OSError as exc:
        warning(f"Failed to create backup for {filepath}: {exc}")
        return False


def restore_backup(
    filepath: Path,
    app_name: str,
    direction: str,
    dry_run: bool = False,
) -> bool:
    """Restore a file from its backup.

    Args:
        filepath: Original file path (destination that was overwritten).
        app_name: Application name.
        direction: "push" or "pull".
        dry_run: If True, only log what would happen.

    Returns:
        True on success, False if backup doesn't exist or fails.
    """
    backup_path = get_backup_path(filepath, app_name, direction)

    if not backup_path.exists():
        return False

    if dry_run:
        dry_run_log("Would restore backup", str(backup_path), str(filepath))
        return True

    # Remove current file if it exists
    if filepath.exists():
        if filepath.is_dir():
            shutil.rmtree(filepath)
        else:
            filepath.unlink()

    try:
        shutil.move(str(backup_path), str(filepath))
        verbose(f"Restored backup: {backup_path} \u2192 {filepath}")
        return True
    except OSError as exc:
        warning(f"Failed to restore backup for {filepath}: {exc}")
        return False


def remove_backup(
    filepath: Path,
    app_name: str,
    direction: str,
    dry_run: bool = False,
) -> bool:
    """Remove a backup file.

    Args:
        filepath: Original file path.
        app_name: Application name.
        direction: "push" or "pull".
        dry_run: If True, only log what would happen.

    Returns:
        True on success or if backup doesn't exist, False on failure.
    """
    backup_path = get_backup_path(filepath, app_name, direction)

    if not backup_path.exists():
        return True  # Nothing to remove

    if dry_run:
        dry_run_log("Would remove backup", str(backup_path))
        return True

    try:
        if backup_path.is_dir():
            shutil.rmtree(backup_path)
        else:
            backup_path.unlink()
        return True
    except OSError as exc:
        warning(f"Failed to remove backup {backup_path}: {exc}")
        return False
