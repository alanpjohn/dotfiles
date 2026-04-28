"""Tests for dotfiles.path_utils module."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dotfiles.config import AppConfig
from dotfiles.path_utils import resolve_repo_path, resolve_config_path, resolve_source_dir


class TestResolveRepoPath:
    """Tests for resolve_repo_path()."""

    def test_basic_resolution(self, tmp_repo_root: Path, sample_app: AppConfig):
        """Returns {repo_root}/{app.repo_path}."""
        result = resolve_repo_path(sample_app)
        assert result == (tmp_repo_root / "testapp").resolve()

    def test_with_relative_path(self, tmp_repo_root: Path, sample_app: AppConfig):
        """Appends relative path correctly."""
        result = resolve_repo_path(sample_app, "sub/file.txt")
        assert result == (tmp_repo_root / "testapp" / "sub" / "file.txt").resolve()

    def test_empty_relative(self, tmp_repo_root: Path, sample_app: AppConfig):
        """Empty relative path returns just the app repo dir."""
        result = resolve_repo_path(sample_app, "")
        assert result == (tmp_repo_root / "testapp").resolve()

    def test_nested_repo_path(self, tmp_repo_root: Path):
        """Handles app with nested repo_path like 'configs/nvim'."""
        app = AppConfig(
            name="nvim", type="directory",
            repo_path="configs/nvim", config_path="nvim",
        )
        result = resolve_repo_path(app, "init.lua")
        assert result == (tmp_repo_root / "configs" / "nvim" / "init.lua").resolve()


class TestResolveConfigPath:
    """Tests for resolve_config_path()."""

    def test_basic_resolution(self, tmp_repo_root: Path, sample_app: AppConfig):
        """Returns {XDG_CONFIG_HOME}/{app.config_path}."""
        result = resolve_config_path(sample_app)
        # Default XDG_CONFIG_HOME is ~/.config
        expected_base = Path(os.path.expanduser("~/.config"))
        assert result == (expected_base / "testapp").resolve()

    def test_with_relative_path(self, tmp_repo_root: Path, sample_app: AppConfig):
        """Appends relative path correctly."""
        result = resolve_config_path(sample_app, "settings.json")
        expected_base = Path(os.path.expanduser("~/.config"))
        assert result == (expected_base / "testapp" / "settings.json").resolve()

    def test_xdg_config_home_override(self, tmp_repo_root: Path, sample_app: AppConfig, monkeypatch):
        """Respects XDG_CONFIG_HOME environment variable."""
        custom_config = tmp_repo_root / "custom_config"
        custom_config.mkdir()
        monkeypatch.setenv("XDG_CONFIG_HOME", str(custom_config))
        result = resolve_config_path(sample_app)
        assert result == (custom_config / "testapp").resolve()


class TestResolveSourceDir:
    """Tests for resolve_source_dir()."""

    def test_push_returns_repo_path(self, tmp_repo_root: Path, sample_app: AppConfig):
        """Push direction returns repo path."""
        result = resolve_source_dir(sample_app, "push")
        assert result == (tmp_repo_root / "testapp").resolve()

    def test_pull_returns_config_path(self, tmp_repo_root: Path, sample_app: AppConfig):
        """Pull direction returns config path."""
        result = resolve_source_dir(sample_app, "pull")
        expected_base = Path(os.path.expanduser("~/.config"))
        assert result == (expected_base / "testapp").resolve()

    def test_invalid_direction_raises(self, tmp_repo_root: Path, sample_app: AppConfig):
        """Invalid direction raises ValueError."""
        with pytest.raises(ValueError, match="Invalid direction"):
            resolve_source_dir(sample_app, "invalid")
