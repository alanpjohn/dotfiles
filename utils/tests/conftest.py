"""Shared test fixtures and helpers for the dotfiles test suite."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Global state reset (autouse, runs before AND after EVERY test)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_module_state():
    """Reset all module-level caches between tests."""
    import dotfiles.config as cfg
    import dotfiles.filters as flt
    import dotfiles.logging_utils as log

    cfg._repo_root_cache = None
    cfg._config_cache = None
    flt._git_available = None
    log._verbose_enabled = True
    yield
    cfg._repo_root_cache = None
    cfg._config_cache = None
    flt._git_available = None
    log._verbose_enabled = True


# ---------------------------------------------------------------------------
# Temp repo root fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_repo_root(tmp_path: Path):
    """Create a temporary directory that looks like a dotfiles repo root.

    Contains: dotfiles.toml (minimal valid config) and .git/ subdirectory.
    Sets DOTFILES_REPO_DIR to point to it.

    Returns the path to the temporary repo root.
    """
    repo = tmp_path / "dotfiles_repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    # Write minimal valid config with one test app
    (repo / "dotfiles.toml").write_text(
        '[global]\n'
        'backup_directory = ".backups"\n'
        'backup_suffix = ".backup"\n'
        'respect_gitignore = true\n'
        '\n'
        '[[applications]]\n'
        'name = "testapp"\n'
        'type = "directory"\n'
        'repo_path = "testapp"\n'
        'config_path = "testapp"\n'
    )

    old_env = os.environ.get("DOTFILES_REPO_DIR")
    os.environ["DOTFILES_REPO_DIR"] = str(repo)
    yield repo
    if old_env is None:
        os.environ.pop("DOTFILES_REPO_DIR", None)
    else:
        os.environ["DOTFILES_REPO_DIR"] = old_env


@pytest.fixture
def tmp_repo_root_custom(tmp_path: Path):
    """Factory fixture: create a temp repo root with custom TOML content.

    Usage:
        def test_something(tmp_repo_root_custom):
            repo = tmp_repo_root_custom(toml_content="...")
    """
    def _create(toml_content: str) -> Path:
        repo = tmp_path / "custom_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text(toml_content)

        old_env = os.environ.get("DOTFILES_REPO_DIR")
        os.environ["DOTFILES_REPO_DIR"] = str(repo)
        # Note: caller must handle env cleanup if needed
        return repo
    return _create


# ---------------------------------------------------------------------------
# AppConfig fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_app():
    """A basic directory-type AppConfig for testing."""
    from dotfiles.config import AppConfig
    return AppConfig(
        name="testapp",
        type="directory",
        repo_path="testapp",
        config_path="testapp",
        recursive=False,
        file_mappings=[],
        exclude=[],
        include=[],
    )


@pytest.fixture
def app_with_mappings():
    """An AppConfig with file_mappings (like zed)."""
    from dotfiles.config import AppConfig, FileMapping
    return AppConfig(
        name="zed",
        type="directory",
        repo_path="zed",
        config_path="zed",
        recursive=True,
        file_mappings=[
            FileMapping(repo_name="settings.jsonc", config_name="settings.json"),
            FileMapping(repo_name="tasks.jsonc", config_name="tasks.json"),
        ],
        exclude=["*.backup", "themes/"],
        include=["*.jsonc", "*.json"],
    )


# ---------------------------------------------------------------------------
# Git mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_git_available(monkeypatch):
    """Mock git as available."""
    monkeypatch.setattr("dotfiles.filters._git_available", True)
    monkeypatch.setattr("dotfiles.filters._check_git", lambda: True)


@pytest.fixture
def mock_git_unavailable(monkeypatch):
    """Mock git as unavailable."""
    monkeypatch.setattr("dotfiles.filters._git_available", False)
    monkeypatch.setattr("dotfiles.filters._check_git", lambda: False)


class GitCheckIgnoreMock:
    """Configurable mock for subprocess.run that simulates git check-ignore.

    Usage:
        mock = GitCheckIgnoreMock(ignored=True)
        monkeypatch.setattr("subprocess.run", mock)
    """

    def __init__(self, ignored: bool = False, error: bool = False):
        self.ignored = ignored
        self.error = error
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, cmd: Any, **kwargs: Any) -> CompletedProcess:
        self.calls.append((cmd if isinstance(cmd, tuple) else (cmd,), kwargs))
        if isinstance(cmd, (list, tuple)) and len(cmd) >= 2 and cmd[0] == "git" and "check-ignore" in cmd:
            if self.error:
                return CompletedProcess(args=cmd, returncode=128, stdout="", stderr="fatal error")
            rc = 0 if self.ignored else 1
            return CompletedProcess(args=cmd, returncode=rc, stdout="", stderr="")
        # Default: success for other commands (like git --version)
        return CompletedProcess(args=cmd if isinstance(cmd, (list, tuple)) else [str(cmd)], returncode=0)


@pytest.fixture
def mock_git_check_ignore():
    """Factory fixture for mocking git check-ignore.

    Returns GitCheckIgnoreMock class for instantiation in tests.
    """
    return GitCheckIgnoreMock


# ---------------------------------------------------------------------------
# Logging capture
# ---------------------------------------------------------------------------

@pytest.fixture
def capture_logging(monkeypatch):
    """Capture all logging_utils output for verification.

    Returns a dict with keys: info, success, error, warning, verbose, dry_run.
    Each value is a list of captured messages.
    """
    captured: dict[str, list] = {
        "info": [],
        "success": [],
        "error": [],
        "warning": [],
        "verbose": [],
        "dry_run": [],
    }

    def _info(msg: str, *a: Any, **kw: Any) -> None:
        captured["info"].append(str(msg))

    def _success(msg: str, *a: Any, **kw: Any) -> None:
        captured["success"].append(str(msg))

    def _error(msg: str, *a: Any, **kw: Any) -> None:
        captured["error"].append(str(msg))

    def _warning(msg: str, *a: Any, **kw: Any) -> None:
        captured["warning"].append(str(msg))

    def _verbose(msg: str, *a: Any, **kw: Any) -> None:
        captured["verbose"].append(str(msg))

    def _dry_run(action: str, src: str, dst: str = "") -> None:
        captured["dry_run"].append((action, src, dst))

    monkeypatch.setattr("dotfiles.logging_utils.info", _info)
    monkeypatch.setattr("dotfiles.logging_utils.success", _success)
    monkeypatch.setattr("dotfiles.logging_utils.error", _error)
    monkeypatch.setattr("dotfiles.logging_utils.warning", _warning)
    monkeypatch.setattr("dotfiles.logging_utils.verbose", _verbose)
    monkeypatch.setattr("dotfiles.logging_utils.dry_run_log", _dry_run)
    # Also patch in modules that import these functions directly
    monkeypatch.setattr("dotfiles.sync.info", _info)
    monkeypatch.setattr("dotfiles.sync.success", _success)
    monkeypatch.setattr("dotfiles.sync.error", _error)
    monkeypatch.setattr("dotfiles.sync.warning", _warning)
    monkeypatch.setattr("dotfiles.sync.verbose", _verbose)
    monkeypatch.setattr("dotfiles.sync.dry_run_log", _dry_run)
    monkeypatch.setattr("dotfiles.backup.verbose", _verbose)
    monkeypatch.setattr("dotfiles.backup.dry_run_log", _dry_run)
    monkeypatch.setattr("dotfiles.backup.warning", _warning)
    return captured


# ---------------------------------------------------------------------------
# Sync mock helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_sync_file(monkeypatch):
    """Mock sync.sync_file to return a configurable result.

    Usage:
        calls = mock_sync_file(return_value=True)
        # After test: calls contains [(app, src, dst, direction, dry_run, force), ...]
    """
    recorded_calls: list[tuple] = []

    def _mock_sync_file(app, src, dst, direction, dry_run=False, force=False):
        recorded_calls.append((app, src, dst, direction, dry_run, force))
        return True

    monkeypatch.setattr("dotfiles.sync.sync_file", _mock_sync_file)
    return recorded_calls


@pytest.fixture
def mock_get_source_files(monkeypatch):
    """Mock filters.get_source_files to return a controlled list.

    Usage:
        mock_get_source_files([Path("/fake/file1"), Path("/fake/file2")])
    """
    def _setup(file_list: list):
        mock_fn = lambda app, direction, respect_gitignore=True: file_list
        monkeypatch.setattr("dotfiles.filters.get_source_files", mock_fn)
        monkeypatch.setattr("dotfiles.sync.get_source_files", mock_fn)
    return _setup
