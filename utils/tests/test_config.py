"""Tests for dotfiles.config module."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dotfiles.config import (
    AppConfig,
    ConfigError,
    DotfilesConfig,
    FileMapping,
    GlobalConfig,
    discover_repo_root,
    get_app,
    get_global,
    list_apps,
    load_config,
)


# ---------------------------------------------------------------------------
# discover_repo_root
# ---------------------------------------------------------------------------

class TestDiscoverRepoRoot:
    """Tests for discover_repo_root()."""

    def test_finds_valid_repo_root(self, tmp_repo_root: Path):
        """Walk-up finds directory with dotfiles.toml + .git."""
        result = discover_repo_root()
        assert result == tmp_repo_root

    def test_env_var_override(self, tmp_path: Path):
        """DOTFILES_REPO_DIR env var is used directly."""
        repo = tmp_path / "env_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text(
            '[global]\n[[applications]]\nname="a"\ntype="directory"\nrepo_path="a"\nconfig_path="a"\n'
        )
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            result = discover_repo_root()
            assert result == repo
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_env_var_invalid_raises(self):
        """ConfigError when env var points to missing directory."""
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = "/nonexistent/path/that/does/not/exist"
            with pytest.raises(ConfigError, match="does not contain required files"):
                discover_repo_root()
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_caches_result(self, tmp_repo_root: Path):
        """Second call returns cached result."""
        first = discover_repo_root()
        second = discover_repo_root()
        assert first is second


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    """Tests for load_config()."""

    def test_valid_config_parses_apps(self, tmp_repo_root: Path):
        """Parses a valid TOML config with one app."""
        config = load_config()
        assert len(config.applications) == 1
        assert config.applications[0].name == "testapp"
        assert config.applications[0].type == "directory"

    def test_multiple_apps(self, tmp_path: Path):
        """Parses multiple applications."""
        repo = tmp_path / "multi_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text(
            '[global]\n'
            '[[applications]]\nname="app1"\ntype="directory"\nrepo_path="a"\nconfig_path="a"\n'
            '[[applications]]\nname="app2"\ntype="directory"\nrepo_path="b"\nconfig_path="b"\n'
        )
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            config = load_config()
            assert len(config.applications) == 2
            assert config.applications[0].name == "app1"
            assert config.applications[1].name == "app2"
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_default_values_applied(self, tmp_path: Path):
        """Defaults applied for optional fields."""
        repo = tmp_path / "defaults_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text(
            '[global]\n'
            '[[applications]]\nname="app"\ntype="directory"\nrepo_path="a"\nconfig_path="a"\n'
        )
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            config = load_config()
            app = config.applications[0]
            assert app.recursive is False
            assert app.file_mappings == []
            assert app.exclude == []
            assert app.include == []
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_file_mappings_subtable(self, tmp_path: Path):
        """Parses [[applications.file_mappings]] sub-table syntax."""
        repo = tmp_path / "mappings_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text(
            '[global]\n'
            '[[applications]]\nname="zed"\ntype="directory"\nrepo_path="zed"\nconfig_path="zed"\n'
            '[[applications.file_mappings]]\nrepo_name="settings.jsonc"\nconfig_name="settings.json"\n'
            '[[applications.file_mappings]]\nrepo_name="tasks.jsonc"\nconfig_name="tasks.json"\n'
        )
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            config = load_config()
            app = config.applications[0]
            assert len(app.file_mappings) == 2
            assert app.file_mappings[0].repo_name == "settings.jsonc"
            assert app.file_mappings[0].config_name == "settings.json"
            assert app.file_mappings[1].repo_name == "tasks.jsonc"
            assert app.file_mappings[1].config_name == "tasks.json"
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_identity_mapping_warning(self, tmp_path: Path, capture_logging):
        """Warning logged when repo_name == config_name."""
        repo = tmp_path / "identity_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text(
            '[global]\n'
            '[[applications]]\nname="tmux"\ntype="directory"\nrepo_path="tmux"\nconfig_path="tmux"\n'
            '[[applications.file_mappings]]\nrepo_name="tmux.conf"\nconfig_name="tmux.conf"\n'
        )
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            config = load_config()
            assert len(config.applications[0].file_mappings) == 1
            assert any("Identity file mapping" in w for w in capture_logging["warning"])
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_missing_required_field_raises(self, tmp_path: Path):
        """ConfigError when required fields missing."""
        repo = tmp_path / "bad_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text(
            '[global]\n'
            '[[applications]]\nname="app"\n'  # missing type, repo_path, config_path
        )
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            with pytest.raises(ConfigError, match="missing required fields"):
                load_config()
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_invalid_type_raises(self, tmp_path: Path):
        """ConfigError when type is not directory or file."""
        repo = tmp_path / "type_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text(
            '[global]\n'
            '[[applications]]\nname="app"\ntype="link"\nrepo_path="a"\nconfig_path="a"\n'
        )
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            with pytest.raises(ConfigError, match="invalid type"):
                load_config()
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_empty_applications_raises(self, tmp_path: Path):
        """ConfigError when no applications defined."""
        repo = tmp_path / "empty_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text("[global]\n")
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            with pytest.raises(ConfigError, match="No applications defined"):
                load_config()
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_malformed_toml_raises(self, tmp_path: Path):
        """ConfigError on invalid TOML syntax."""
        repo = tmp_path / "malformed_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text("this is not valid [[[toml")
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            with pytest.raises(ConfigError, match="Failed to parse"):
                load_config()
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_config_caching(self, tmp_repo_root: Path):
        """Second call returns cached result."""
        first = load_config()
        second = load_config()
        assert first is second

    def test_global_settings_parsed(self, tmp_path: Path):
        """Global settings correctly parsed."""
        repo = tmp_path / "global_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text(
            '[global]\n'
            'backup_directory = "my_backups"\n'
            'backup_suffix = ".bak"\n'
            'respect_gitignore = false\n'
            '\n'
            '[[applications]]\nname="a"\ntype="directory"\nrepo_path="a"\nconfig_path="a"\n'
        )
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            config = load_config()
            assert config.global_config.backup_directory == "my_backups"
            assert config.global_config.backup_suffix == ".bak"
            assert config.global_config.respect_gitignore is False
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

class TestQueryHelpers:
    """Tests for list_apps, get_app, get_global."""

    def test_list_apps_returns_all(self, tmp_repo_root: Path):
        """list_apps returns all configured applications."""
        apps = list_apps()
        assert len(apps) == 1
        assert apps[0].name == "testapp"

    def test_get_app_valid(self, tmp_repo_root: Path):
        """get_app returns correct AppConfig for valid name."""
        app = get_app("testapp")
        assert app.name == "testapp"
        assert app.type == "directory"

    def test_get_app_invalid_raises(self, tmp_repo_root: Path):
        """get_app raises ConfigError for nonexistent app."""
        with pytest.raises(ConfigError, match="not found"):
            get_app("nonexistent")

    def test_get_global_returns_setting(self, tmp_repo_root: Path):
        """get_global returns correct global setting."""
        assert get_global("backup_directory") == ".backups"
        assert get_global("backup_suffix") == ".backup"
        assert get_global("respect_gitignore") is True

    def test_get_global_default(self, tmp_repo_root: Path):
        """get_global returns default for missing key."""
        assert get_global("nonexistent_key", "default_val") == "default_val"
