"""Core sync engine for dotfiles push/pull operations."""

from __future__ import annotations

import filecmp
import os
import shutil
from pathlib import Path

from dotfiles.config import AppConfig, list_apps, get_global
from dotfiles.filters import get_source_files, should_sync_file
from dotfiles.backup import create_backup
from dotfiles.path_utils import resolve_repo_path, resolve_config_path
from dotfiles.logging_utils import (
    info,
    success,
    error,
    warning,
    verbose,
    dry_run_log,
)


# ---------------------------------------------------------------------------
# File mappings
# ---------------------------------------------------------------------------


def _get_mapped_basename(app: AppConfig, source_basename: str, direction: str) -> str:
    """Apply file_mappings to get the destination basename.

    Mappings are matched on basename only (same as bash behavior).
    - For push: maps repo_name → config_name
    - For pull: maps config_name → repo_name

    If no mapping is found, returns the original basename unchanged.
    """
    for mapping in app.file_mappings:
        if direction == "push" and mapping.repo_name == source_basename:
            return mapping.config_name
        elif direction == "pull" and mapping.config_name == source_basename:
            return mapping.repo_name
    return source_basename


# ---------------------------------------------------------------------------
# sync_file
# ---------------------------------------------------------------------------


def sync_file(
    app: AppConfig,
    src: Path,
    dst: Path,
    direction: str,
    dry_run: bool = False,
    force: bool = False,
) -> bool:
    """Sync a single file or directory from source to destination.

    Args:
        app: Application configuration.
        src: Absolute path to the source file/directory.
        dst: Absolute path to the destination file/directory.
        direction: "push" or "pull".
        dry_run: If True, only log what would happen.
        force: If True, overwrite even if destination is newer.

    Returns:
        True on success, False on failure.
    """
    # Validate source exists
    if not src.exists():
        error(f"Source does not exist: {src}")
        return False

    # Create destination parent directory if needed
    if not dst.parent.exists():
        if dry_run:
            dry_run_log("Would create directory", str(dst.parent))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            verbose(f"Created directory: {dst.parent}")

    # --- DRY-RUN mode ---
    if dry_run:
        if dst.exists():
            if src.is_file() and dst.is_file():
                # Compare file contents
                if filecmp.cmp(str(src), str(dst), shallow=False):
                    # Files are identical - no action needed
                    return True
                # Files differ
                dry_run_log("Would update", str(src), str(dst))
                dry_run_log("Would create backup", str(dst), f"{dst}.backup")
            elif src.is_dir() and dst.is_dir():
                # Directories both exist - always report update
                dry_run_log("Would update", str(src), str(dst))
                dry_run_log("Would create backup", str(dst), f"{dst}.backup")
            else:
                # Type mismatch - would update
                dry_run_log("Would update", str(src), str(dst))
        else:
            dry_run_log("Would copy", str(src), str(dst))
        return True

    # --- LIVE mode ---
    # Handle existing destination
    if dst.exists() and not force:
        if src.is_file() and dst.is_file():
            # Compare modification times
            src_mtime = os.path.getmtime(str(src))
            dst_mtime = os.path.getmtime(str(dst))
            if dst_mtime > src_mtime:
                verbose(f"Destination is newer, skipping: {dst}")
                return True  # Skip, not a failure
            # Destination is older or same - backup then copy
            create_backup(dst, app.name, direction, dry_run=False)
        elif src.is_dir() and dst.is_dir():
            # Directory mtime comparison is unreliable - always backup then copy
            create_backup(dst, app.name, direction, dry_run=False)
        else:
            # Type mismatch - backup then copy
            create_backup(dst, app.name, direction, dry_run=False)

    elif dst.exists() and force:
        # Force mode: backup then overwrite regardless
        create_backup(dst, app.name, direction, dry_run=False)

    # Perform the copy
    try:
        verbose(f"Syncing: {src} → {dst}")
        if src.is_dir():
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        else:
            shutil.copy2(str(src), str(dst))
        return True
    except OSError as exc:
        error(f"Failed to copy: {src} → {dst}: {exc}")
        return False


# ---------------------------------------------------------------------------
# App-level sync
# ---------------------------------------------------------------------------


def sync_app_push(
    app: AppConfig,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[int, int]:
    """Sync one application from repo to ~/.config (push mode).

    Returns:
        Tuple of (synced_count, failed_count).
    """
    verbose(f"Starting push sync for app: {app.name}")

    # Get source files from repo
    respect_gitignore = bool(get_global("respect_gitignore", True))
    source_files = get_source_files(app, "push", respect_gitignore)

    if not source_files:
        info(f"No files to push for {app.name} (source doesn't exist in repo)")
        return (0, 0)

    synced = 0
    failed = 0

    for src_file in source_files:
        # Compute relative path from source base
        source_base = resolve_repo_path(app, "")
        try:
            relative = str(src_file.relative_to(source_base))
        except ValueError:
            relative = str(src_file.name)

        # Get mapped destination basename
        src_basename = str(src_file.name)
        dest_basename = _get_mapped_basename(app, src_basename, "push")

        # Replace the basename in the relative path if mapped
        if dest_basename != src_basename:
            relative_parts = Path(relative).parts
            if len(relative_parts) == 1:
                dest_relative = dest_basename
            else:
                dest_relative = str(Path(*relative_parts[:-1]) / dest_basename)
        else:
            dest_relative = relative

        # Resolve full paths
        repo_path = resolve_repo_path(app, relative)
        config_path = resolve_config_path(app, dest_relative)

        if not repo_path.exists():
            error(f"Source file not found: {repo_path}")
            failed += 1
            continue

        # Sync
        if sync_file(app, repo_path, config_path, "push", dry_run, force):
            synced += 1
        else:
            failed += 1

    verbose(f"Synced {synced} files for {app.name}")
    success(f"Synced {synced} files for {app.name}")

    return (synced, failed)


def sync_app_pull(
    app: AppConfig,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[int, int]:
    """Sync one application from ~/.config to repo (pull mode).

    Returns:
        Tuple of (synced_count, failed_count).
    """
    verbose(f"Starting pull sync for app: {app.name}")

    # Get source files from config
    respect_gitignore = bool(get_global("respect_gitignore", True))
    source_files = get_source_files(app, "pull", respect_gitignore)

    if not source_files:
        info(f"No files to pull for {app.name} (source doesn't exist in ~/.config)")
        return (0, 0)

    synced = 0
    failed = 0

    for src_file in source_files:
        # Compute relative path from source base
        source_base = resolve_config_path(app, "")
        try:
            relative = str(src_file.relative_to(source_base))
        except ValueError:
            relative = str(src_file.name)

        # Get mapped destination basename (reverse of push)
        src_basename = str(src_file.name)
        dest_basename = _get_mapped_basename(app, src_basename, "pull")

        # Replace the basename in the relative path if mapped
        if dest_basename != src_basename:
            relative_parts = Path(relative).parts
            if len(relative_parts) == 1:
                dest_relative = dest_basename
            else:
                dest_relative = str(Path(*relative_parts[:-1]) / dest_basename)
        else:
            dest_relative = relative

        # Resolve full paths
        config_path = resolve_config_path(app, relative)
        repo_path = resolve_repo_path(app, dest_relative)

        if not config_path.exists():
            error(f"Source file not found: {config_path}")
            failed += 1
            continue

        # Sync (reverse direction)
        if sync_file(app, config_path, repo_path, "pull", dry_run, force):
            synced += 1
        else:
            failed += 1

    verbose(f"Synced {synced} files for {app.name}")
    success(f"Synced {synced} files for {app.name}")

    return (synced, failed)


# ---------------------------------------------------------------------------
# sync_all
# ---------------------------------------------------------------------------


def sync_all(
    direction: str,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[int, int]:
    """Sync all configured applications.

    This function only aggregates results. The CLI layer handles
    progress bar rendering.

    Args:
        direction: "push" or "pull".
        dry_run: If True, preview only.
        force: Overwrite newer files.

    Returns:
        Tuple of (total_synced, total_failed_apps).
    """
    if direction not in ("push", "pull"):
        raise ValueError(f"Invalid direction: {direction!r}")

    verbose(f"Starting sync all in {direction} mode")

    apps = list_apps()
    if not apps:
        error("No applications found in config")
        return (0, 1)

    total_failed = 0

    for app in apps:
        if direction == "push":
            _, failed = sync_app_push(app, dry_run, force)
        else:
            _, failed = sync_app_pull(app, dry_run, force)

        if failed > 0:
            total_failed += 1

    msg = f"Total apps with failures: {total_failed}"
    if total_failed == 0:
        verbose(f"Completed sync all in {direction} mode")
        success(msg)
    else:
        warning(msg)

    return (0, total_failed)


# ---------------------------------------------------------------------------
# Preview changes
# ---------------------------------------------------------------------------


def preview_changes(app: AppConfig, direction: str) -> str:
    """Generate a bash-compatible dry-run summary for a single app.

    Returns:
        Formatted string with preview of changes, matching the bash output format:
        ```
        [INFO] Previewing changes for 'zed' (push):

        [DRY-RUN] Would copy: source -> dest
        [DRY-RUN] Would update: source -> dest
        [DRY-RUN] Would create backup: dest -> dest.backup

        Summary:
          Would copy: N new file(s)
          Would update: N existing file(s)
          Would backup: N file(s)
        ```
    """
    lines: list[str] = []
    lines.append(f"[INFO] Previewing changes for '{app.name}' ({direction}):")
    lines.append("")

    respect_gitignore = bool(get_global("respect_gitignore", True))
    source_files = get_source_files(app, direction, respect_gitignore)

    if not source_files:
        lines.append(f"  No files found for {app.name}")
        lines.append("")
        return "\n".join(lines)

    copy_count = 0
    update_count = 0
    backup_count = 0

    for src_file in source_files:
        # Compute destination
        source_base = (
            resolve_repo_path(app, "")
            if direction == "push"
            else resolve_config_path(app, "")
        )
        try:
            relative = str(src_file.relative_to(source_base))
        except ValueError:
            relative = str(src_file.name)

        src_basename = str(src_file.name)
        dest_basename = _get_mapped_basename(app, src_basename, direction)

        if dest_basename != src_basename:
            relative_parts = Path(relative).parts
            if len(relative_parts) == 1:
                dest_relative = dest_basename
            else:
                dest_relative = str(Path(*relative_parts[:-1]) / dest_basename)
        else:
            dest_relative = relative

        if direction == "push":
            src_full = resolve_repo_path(app, relative)
            dest_full = resolve_config_path(app, dest_relative)
        else:
            src_full = resolve_config_path(app, relative)
            dest_full = resolve_repo_path(app, dest_relative)

        if not src_full.exists():
            continue

        if dest_full.exists():
            if src_full.is_file() and dest_full.is_file():
                if not filecmp.cmp(str(src_full), str(dest_full), shallow=False):
                    lines.append(f"[DRY-RUN] Would update: {src_full} -> {dest_full}")
                    lines.append(f"[DRY-RUN] Would create backup: {dest_full} -> {dest_full}.backup")
                    update_count += 1
                    backup_count += 1
            elif src_full.is_dir() and dest_full.is_dir():
                lines.append(f"[DRY-RUN] Would update: {src_full} -> {dest_full}")
                lines.append(f"[DRY-RUN] Would create backup: {dest_full} -> {dest_full}.backup")
                update_count += 1
                backup_count += 1
        else:
            lines.append(f"[DRY-RUN] Would copy: {src_full} -> {dest_full}")
            copy_count += 1

            # Check if parent directory needs creation
            parent_dir = dest_full.parent
            if not parent_dir.exists():
                lines.append(f"[DRY-RUN] Would create directory: {parent_dir}")

    lines.append("")
    lines.append("Summary:")
    lines.append(f"  Would copy: {copy_count} new file(s)")
    lines.append(f"  Would update: {update_count} existing file(s)")
    lines.append(f"  Would backup: {backup_count} file(s)")
    lines.append("")

    return "\n".join(lines)
