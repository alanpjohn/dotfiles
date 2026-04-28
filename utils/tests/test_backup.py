"""Tests for dotfiles.backup module."""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.backup import (
    get_backup_path,
    create_backup,
    restore_backup,
    remove_backup,
)


# ---------------------------------------------------------------------------
# get_backup_path
# ---------------------------------------------------------------------------

class TestGetBackupPath:
    """Tests for get_backup_path()."""

    def test_push_direction(self, tmp_repo_root, sample_app):
        """Push: backup path uses config path as source base."""
        filepath = Path.home() / ".config" / "testapp" / "settings.json"
        result = get_backup_path(filepath, "testapp", "push")
        # Should be under repo_root/.backups/testapp/
        assert ".backups" in str(result)
        assert "testapp" in str(result)
        assert str(result).endswith(".backup")

    def test_pull_direction(self, tmp_repo_root, sample_app):
        """Pull: backup path uses repo path as source base."""
        filepath = tmp_repo_root / "testapp" / "config.toml"
        result = get_backup_path(filepath, "testapp", "pull")
        assert ".backups" in str(result)
        assert "testapp" in str(result)
        assert str(result).endswith(".backup")

    def test_nested_file_preserves_structure(self, tmp_repo_root, sample_app):
        """Nested file paths preserved in backup path."""
        filepath = Path.home() / ".config" / "testapp" / "lua" / "plugins" / "init.lua"
        result = get_backup_path(filepath, "testapp", "push")
        assert "lua" in str(result)
        assert "plugins" in str(result)
        assert "init.lua.backup" in str(result)

    def test_custom_suffix(self, tmp_path):
        """Custom backup_suffix from config is used."""
        repo = tmp_path / "suffix_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "dotfiles.toml").write_text(
            '[global]\nbackup_suffix = ".bak"\n'
            '[[applications]]\nname="a"\ntype="directory"\nrepo_path="a"\nconfig_path="a"\n'
        )
        import os
        old = os.environ.get("DOTFILES_REPO_DIR")
        try:
            os.environ["DOTFILES_REPO_DIR"] = str(repo)
            filepath = Path.home() / ".config" / "a" / "file.txt"
            result = get_backup_path(filepath, "a", "push")
            assert str(result).endswith(".bak")
        finally:
            if old is None:
                os.environ.pop("DOTFILES_REPO_DIR", None)
            else:
                os.environ["DOTFILES_REPO_DIR"] = old

    def test_fallback_basename(self, tmp_repo_root, sample_app):
        """Falls back to basename when path not under source base."""
        filepath = Path("/completely/different/path/file.txt")
        result = get_backup_path(filepath, "testapp", "push")
        assert "file.txt.backup" in str(result)


# ---------------------------------------------------------------------------
# create_backup
# ---------------------------------------------------------------------------

class TestCreateBackup:
    """Tests for create_backup()."""

    def test_dry_run_logs_only(self, tmp_path, capture_logging):
        """Dry-run logs but does not copy."""
        src = tmp_path / "source.txt"
        src.write_text("content")
        result = create_backup(src, "testapp", "push", dry_run=True)
        assert result is True
        assert len(capture_logging["dry_run"]) > 0
        # No backup file should exist
        backups = list(tmp_path.rglob("*.backup"))
        assert len(backups) == 0

    def test_live_copies_file(self, tmp_path, tmp_repo_root):
        """Copies file to backup location."""
        src = tmp_path / "source.txt"
        src.write_text("content")
        result = create_backup(src, "testapp", "push", dry_run=False)
        assert result is True

    def test_missing_file_returns_false(self, tmp_path, tmp_repo_root):
        """Returns False when source doesn't exist."""
        src = tmp_path / "nonexistent.txt"
        result = create_backup(src, "testapp", "push", dry_run=False)
        assert result is False

    def test_live_copies_directory(self, tmp_path, tmp_repo_root):
        """Copies directory recursively."""
        src_dir = tmp_path / "mydir"
        src_dir.mkdir()
        (src_dir / "file1.txt").write_text("content1")
        (src_dir / "file2.txt").write_text("content2")
        result = create_backup(src_dir, "testapp", "push", dry_run=False)
        assert result is True


# ---------------------------------------------------------------------------
# restore_backup
# ---------------------------------------------------------------------------

class TestRestoreBackup:
    """Tests for restore_backup()."""

    def test_no_backup_returns_false(self, tmp_path, tmp_repo_root):
        """Returns False when backup doesn't exist."""
        filepath = tmp_path / "no_backup.txt"
        result = restore_backup(filepath, "testapp", "push", dry_run=False)
        assert result is False

    def test_dry_run_logs_only(self, tmp_path, tmp_repo_root, capture_logging):
        """Dry-run logs but does not restore."""
        # Create a file and its backup
        filepath = tmp_path / "original.txt"
        filepath.write_text("original")
        create_backup(filepath, "testapp", "push", dry_run=False)
        # Overwrite original
        filepath.write_text("overwritten")
        result = restore_backup(filepath, "testapp", "push", dry_run=True)
        assert result is True
        assert len(capture_logging["dry_run"]) > 0


# ---------------------------------------------------------------------------
# remove_backup
# ---------------------------------------------------------------------------

class TestRemoveBackup:
    """Tests for remove_backup()."""

    def test_no_backup_returns_true(self, tmp_path, tmp_repo_root):
        """Returns True when backup doesn't exist (nothing to remove)."""
        filepath = tmp_path / "no_backup.txt"
        result = remove_backup(filepath, "testapp", "push", dry_run=False)
        assert result is True

    def test_dry_run_logs_only(self, tmp_path, tmp_repo_root, capture_logging):
        """Dry-run logs but does not remove."""
        filepath = tmp_path / "to_remove.txt"
        filepath.write_text("content")
        create_backup(filepath, "testapp", "push", dry_run=False)
        result = remove_backup(filepath, "testapp", "push", dry_run=True)
        assert result is True
        assert len(capture_logging["dry_run"]) > 0
