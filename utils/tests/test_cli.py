"""Tests for dotfiles.cli module (Typer CLI commands)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotfiles.cli import app

runner = CliRunner()


class TestHelpAndVersion:
    """Tests for help and version flags."""

    def test_auto_help_flag(self, tmp_repo_root):
        """--help shows command list."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "push" in result.output.lower()
        assert "pull" in result.output.lower()
        assert "list" in result.output.lower()

    def test_custom_help_command(self, tmp_repo_root):
        """help subcommand prints extended manual."""
        result = runner.invoke(app, ["help"])
        assert result.exit_code == 0
        assert "dotfiles" in result.output.lower()

    def test_version_flag(self, tmp_repo_root):
        """--version shows version string."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "dotfiles v" in result.output


class TestPushCommand:
    """Tests for push command."""

    def test_push_dry_run_all(self, tmp_repo_root, monkeypatch):
        """push --dry-run calls sync_all with correct params."""
        calls = []
        monkeypatch.setattr(
            "dotfiles.sync.sync_all",
            lambda direction, dry_run=False, force=False: calls.append((direction, dry_run, force)) or (0, 0),
        )
        result = runner.invoke(app, ["push", "--dry-run"])
        assert result.exit_code == 0
        assert len(calls) == 1
        assert calls[0] == ("push", True, False)

    def test_push_single_app(self, tmp_repo_root, monkeypatch):
        """push <app> calls sync_app_push."""
        calls = []
        monkeypatch.setattr(
            "dotfiles.sync.sync_app_push",
            lambda app, dry_run=False, force=False: calls.append((app.name, dry_run, force)) or (1, 0),
        )
        result = runner.invoke(app, ["push", "testapp"])
        assert result.exit_code == 0
        assert len(calls) == 1
        assert calls[0][0] == "testapp"

    def test_push_config_error_exit_code(self, tmp_repo_root, monkeypatch):
        """ConfigError exits with code 3."""
        from dotfiles.config import ConfigError
        monkeypatch.setattr(
            "dotfiles.sync.sync_all",
            lambda *a, **kw: (_ for _ in ()).throw(ConfigError("bad config")),
        )
        result = runner.invoke(app, ["push"])
        assert result.exit_code == 3

    def test_push_sync_failure_exit_code(self, tmp_repo_root, monkeypatch):
        """Sync failure exits with code 4."""
        monkeypatch.setattr(
            "dotfiles.sync.sync_all",
            lambda *a, **kw: (0, 1),
        )
        result = runner.invoke(app, ["push"])
        assert result.exit_code == 4


class TestPullCommand:
    """Tests for pull command."""

    def test_pull_dry_run_all(self, tmp_repo_root, monkeypatch):
        """pull --dry-run calls sync_all with correct params."""
        calls = []
        monkeypatch.setattr(
            "dotfiles.sync.sync_all",
            lambda direction, dry_run=False, force=False: calls.append((direction, dry_run, force)) or (0, 0),
        )
        result = runner.invoke(app, ["pull", "--dry-run"])
        assert result.exit_code == 0
        assert len(calls) == 1
        assert calls[0] == ("pull", True, False)

    def test_pull_single_app(self, tmp_repo_root, monkeypatch):
        """pull <app> calls sync_app_pull."""
        calls = []
        monkeypatch.setattr(
            "dotfiles.sync.sync_app_pull",
            lambda app, dry_run=False, force=False: calls.append((app.name, dry_run, force)) or (1, 0),
        )
        result = runner.invoke(app, ["pull", "testapp"])
        assert result.exit_code == 0
        assert len(calls) == 1
        assert calls[0][0] == "testapp"


class TestListCommand:
    """Tests for list command."""

    def test_list_default(self, tmp_repo_root):
        """list (no flags) prints app names."""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "testapp" in result.output

    def test_list_json(self, tmp_repo_root):
        """list --json outputs valid JSON."""
        import json
        result = runner.invoke(app, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "testapp"
