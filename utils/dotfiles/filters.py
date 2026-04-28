"""File filtering: glob matching, include/exclude, gitignore checking."""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

from dotfiles.config import AppConfig, discover_repo_root
from dotfiles.path_utils import resolve_source_dir
from dotfiles.logging_utils import warning, info


# Cached git availability
_git_available: bool | None = None


def _check_git() -> bool:
    """Check if git is available (cached)."""
    global _git_available
    if _git_available is None:
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            _git_available = True
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            _git_available = False
    return _git_available


# ---------------------------------------------------------------------------
# Glob matching
# ---------------------------------------------------------------------------


def matches_glob(path: str | Path, pattern: str) -> bool:
    """Test if a file path matches a glob pattern using bash semantics.

    Matching rules:
    - ``*.ext``: matches basename only (e.g. ``*.jsonc`` matches ``foo.jsonc``
      but NOT ``sub/foo.jsonc`` ... wait, actually in the bash script
      it DOES match subdirectory files via the secondary ``*/pattern`` case.
      The bash script checks both ``${pattern}`` AND ``*/${pattern}``.
      So ``*.jsonc`` matches ``foo.jsonc`` AND ``sub/foo.jsonc`` but not
      ``sub/deep/foo.jsonc``.

    - ``dir/`` (trailing slash): matches if ``dir`` appears as a path component
      anywhere in the path (directory exclusion).

    - ``*text*``: matches basename containing ``text``.

    Args:
        path: File path to test (relative to source directory).
        pattern: Glob pattern from the config.

    Returns:
        True if the path matches the pattern.
    """
    path_str = str(path)

    # Directory patterns (ending with /)
    if pattern.endswith("/"):
        dir_name = pattern.rstrip("/")
        parts = Path(path_str).parts
        return dir_name in parts

    basename = Path(path_str).name

    # Try pattern directly against basename
    if fnmatch.fnmatch(basename, pattern):
        return True

    # Also try basename-only against the full path (matching bash secondary case)
    if fnmatch.fnmatch(path_str, f"*/{pattern}"):
        return True

    return False


# ---------------------------------------------------------------------------
# Gitignore
# ---------------------------------------------------------------------------


def is_gitignored(relative_path: str) -> bool:
    """Check if a file is ignored by git.

    Runs ``git check-ignore`` from the repo root with the relative path.
    Gracefully degrades if git is not available or the path is outside the repo.

    Args:
        relative_path: Path relative to the repo root.

    Returns:
        True if the file is gitignored, False if not, outside repo, or git unavailable.
    """
    if not _check_git():
        return False

    repo_root = discover_repo_root()

    # If the path is outside the repo, git can't check it - silently skip
    path_obj = Path(relative_path)
    try:
        repo_rel = path_obj.resolve().relative_to(repo_root.resolve())
        check_path = str(repo_rel)
    except ValueError:
        # Path is outside the repo root, not gitignored
        return False

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", "-q", check_path],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True  # File is gitignored
        elif result.returncode == 1:
            return False  # File is NOT gitignored
        else:
            # Exit code >= 128: git error
            warning(f"git check-ignore error (code {result.returncode}) for: {check_path}")
            return False
    except (subprocess.TimeoutExpired, OSError) as exc:
        warning(f"git check-ignore failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Sync decision
# ---------------------------------------------------------------------------

def should_sync_file(
    app: AppConfig,
    filepath: str | Path,
    direction: str,
    respect_gitignore: bool = True,
) -> bool:
    """Determine if a file should be synced based on config rules.

    1. If ``respect_gitignore`` is true AND file is gitignored → skip
    2. If app has ``include`` patterns AND file basename doesn't match any → skip
    3. If file basename matches any ``exclude`` pattern → skip
    4. Otherwise → include

    Patterns are matched against the **source file's basename** (matching bash).

    Args:
        app: Application configuration.
        filepath: Path to the source file (absolute or relative to source dir).
        direction: "push" or "pull" (for gitignore context).
        respect_gitignore: Whether to check .gitignore.

    Returns:
        True if the file should be synced.
    """
    path_str = str(filepath)

    # 1. Gitignore check
    if respect_gitignore:
        # For push, files are in the repo - they shouldn't be gitignored
        # For pull, files are in ~/.config - gitignore doesn't apply but
        # the bash script checks anyway
        repo_root = discover_repo_root()
        try:
            relative = str(Path(path_str).relative_to(repo_root))
        except ValueError:
            relative = path_str
        if is_gitignored(relative):
            return False

    # 2. Include patterns (whitelist)
    if app.include:
        if not any(matches_glob(path_str, p) for p in app.include):
            return False

    # 3. Exclude patterns (blacklist)
    if app.exclude:
        if any(matches_glob(path_str, p) for p in app.exclude):
            return False

    # 4. Include
    return True


# ---------------------------------------------------------------------------
# Source file enumeration
# ---------------------------------------------------------------------------


def get_source_files(
    app: AppConfig,
    direction: str,
    respect_gitignore: bool = True,
) -> list[Path]:
    """Get the list of source files to sync for an app.

    Handles both ``"directory"`` and ``"file"`` type apps.

    For directory type:
    - Uses ``rglob("*")`` for recursive, ``glob("*")`` for non-recursive
    - Pre-prunes directories matching exclude patterns ending with ``/``
    - Post-filters each file through ``should_sync_file``

    Args:
        app: Application configuration.
        direction: "push" or "pull".
        respect_gitignore: Whether to check .gitignore.

    Returns:
        Sorted list of absolute Paths to source files.
    """
    source_dir = resolve_source_dir(app, direction)

    # If source directory doesn't exist, return empty list (graceful)
    if not source_dir.exists():
        info(f"No files to {direction} for {app.name} (source doesn't exist)")
        return []

    # File type: return the single file if it exists
    if app.type == "file":
        if source_dir.is_file():
            if should_sync_file(app, source_dir, direction, respect_gitignore):
                return [source_dir]
        return []

    # Directory type: enumerate files
    # Collect directory names to pre-prune (exclude patterns ending with /)
    prune_dirs: set[str] = set()
    for pattern in app.exclude:
        if pattern.endswith("/"):
            prune_dirs.add(pattern.rstrip("/"))

    # Enumerate files
    files: list[Path] = []
    glob_iter = source_dir.rglob("*") if app.recursive else source_dir.glob("*")

    for entry in glob_iter:
        # Skip symlinks to dirs? No, just filter non-files
        if not entry.is_file():
            continue

        # Pre-prune: skip if any parent directory is in the prune list
        parts = set(entry.relative_to(source_dir).parts[:-1])  # all dir parts
        if parts & prune_dirs:
            continue

        files.append(entry)

    # Post-filter each file
    result: list[Path] = []
    for f in files:
        if should_sync_file(app, f, direction, respect_gitignore):
            result.append(f)

    return sorted(result)
