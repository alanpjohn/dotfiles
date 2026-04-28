"""Tests for dotfiles.sync module."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from dotfiles.config import AppConfig, FileMapping
from dotfiles.sync import (
    _get_mapped_basename,
    sync_file,
    sync_app_push,
    sync_app_pull,
    sync_all,
    preview_changes,
)


# ---------------------------------------------------------------------------
# _get_mapped_basename
# ---------------------------------------------------------------------------

class TestGetMappedBasename:
    """Tests for _get_mapped_basename()."""

    def test_push_maps_repo_to_config(self, app_with_mappings):
        """Push: maps repo_name to config_name."""
        result = _get_mapped_basename(app_with_mappings, "settings.jsonc", "push")
        assert result == "settings.json"

    def test_pull_maps_config_to_repo(self, app_with_mappings):
        """Pull: maps config_name to repo_name."""
        result = _get_mapped_basename(app_with_mappings, "settings.json", "pull")
        assert result == "settings.jsonc"

    def test_no_match_returns_original(self, app_with_mappings):
        """Returns original basename when no mapping matches."""
        result = _get_mapped_basename(app_with_mappings, "unknown.txt", "push")
        assert result == "unknown.txt"

    def test_no_mappings_returns_original(self, sample_app):
        """Returns original when app has no mappings."""
        result = _get_mapped_basename(sample_app, "file.txt", "push")
        assert result == "file.txt"

    def test_wrong_direction_no_match(self, app_with_mappings):
        """Mapping doesn't apply in wrong direction."""
        # In push, config_name is not matched
        result = _get_mapped_basename(app_with_mappings, "settings.json", "push")
        assert result == "settings.json"  # No mapping found, returns original


# ---------------------------------------------------------------------------
# sync_file
# ---------------------------------------------------------------------------

class TestSyncFile:
    """Tests for sync_file()."""

    def test_dry_run_copy_new_file(self, tmp_path, sample_app, capture_logging):
        """Dry-run: reports 'Would copy' for new files."""
        src = tmp_path / "source.txt"
        src.write_text("content")
        dst = tmp_path / "dest" / "source.txt"
        result = sync_file(sample_app, src, dst, "push", dry_run=True)
        assert result is True
        assert any("Would copy" in str(d) for d in capture_logging["dry_run"])

    def test_dry_run_update_different_file(self, tmp_path, sample_app, capture_logging):
        """Dry-run: reports 'Would update' for different files."""
        src = tmp_path / "source.txt"
        src.write_text("new content")
        dst = tmp_path / "dest.txt"
        dst.parent.mkdir(exist_ok=True)
        dst.write_text("old content")
        result = sync_file(sample_app, src, dst, "push", dry_run=True)
        assert result is True
        assert any("Would update" in str(d) for d in capture_logging["dry_run"])

    def test_dry_run_identical_skipped(self, tmp_path, sample_app, capture_logging):
        """Dry-run: identical files produce no log (skipped)."""
        src = tmp_path / "source.txt"
        src.write_text("same content")
        dst = tmp_path / "dest.txt"
        dst.parent.mkdir(exist_ok=True)
        dst.write_text("same content")
        result = sync_file(sample_app, src, dst, "push", dry_run=True)
        assert result is True
        # No "Would copy" or "Would update" logged
        assert not any("Would copy" in str(d) for d in capture_logging["dry_run"])
        assert not any("Would update" in str(d) for d in capture_logging["dry_run"])

    def test_live_skip_newer_dest(self, tmp_path, sample_app, capture_logging):
        """Live: skips when dest is newer than source."""
        src = tmp_path / "source.txt"
        src.write_text("old content")
        dst = tmp_path / "dest.txt"
        dst.write_text("newer content")
        # Make dest explicitly newer by setting mtime
        import os
        src_time = 1000000
        dst_time = 2000000
        os.utime(str(src), (src_time, src_time))
        os.utime(str(dst), (dst_time, dst_time))
        result = sync_file(sample_app, src, dst, "push", dry_run=False)
        assert result is True
        # File should be skipped (dest newer), so dest content unchanged
        assert dst.read_text() == "newer content"

    def test_live_force_overwrites(self, tmp_path, sample_app, capture_logging):
        """Live: force=True overwrites regardless of mtime."""
        src = tmp_path / "source.txt"
        src.write_text("forced content")
        dst = tmp_path / "dest.txt"
        dst.write_text("old content")
        # Make dst newer
        time.sleep(0.05)
        src.write_text("forced content newer")
        result = sync_file(sample_app, src, dst, "push", dry_run=False, force=True)
        assert result is True
        assert dst.read_text() == "forced content newer"

    def test_source_missing_returns_false(self, tmp_path, sample_app, capture_logging):
        """Returns False when source doesn't exist."""
        src = tmp_path / "nonexistent.txt"
        dst = tmp_path / "dest.txt"
        result = sync_file(sample_app, src, dst, "push", dry_run=False)
        assert result is False
        assert any("does not exist" in str(e) for e in capture_logging["error"])

    def test_live_copies_file(self, tmp_path, sample_app):
        """Live: copies file to destination."""
        src = tmp_path / "source.txt"
        src.write_text("hello")
        dst = tmp_path / "output" / "dest.txt"
        result = sync_file(sample_app, src, dst, "push", dry_run=False)
        assert result is True
        assert dst.exists()
        assert dst.read_text() == "hello"


# ---------------------------------------------------------------------------
# sync_app_push / sync_app_pull
# ---------------------------------------------------------------------------

class TestSyncAppPush:
    """Tests for sync_app_push()."""

    def test_empty_source_returns_zero(self, tmp_repo_root, sample_app, mock_get_source_files, capture_logging):
        """Returns (0,0) when source has no files."""
        mock_get_source_files([])
        synced, failed = sync_app_push(sample_app, dry_run=True)
        assert synced == 0
        assert failed == 0

    def test_single_file_sync(self, tmp_repo_root, sample_app, mock_get_source_files, mock_sync_file, capture_logging):
        """Syncs single file correctly."""
        src_file = tmp_repo_root / "testapp" / "file.txt"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("content")
        mock_get_source_files([src_file])
        synced, failed = sync_app_push(sample_app, dry_run=True)
        assert synced == 1
        assert failed == 0

    def test_with_file_mapping(self, tmp_repo_root, app_with_mappings, mock_get_source_files, mock_sync_file, capture_logging):
        """File mapping applied during push."""
        src_file = tmp_repo_root / "zed" / "settings.jsonc"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("content")
        mock_get_source_files([src_file])
        synced, failed = sync_app_push(app_with_mappings, dry_run=True)
        assert synced == 1
        # Verify the sync_file was called with mapped destination
        assert len(mock_sync_file) == 1
        _, _, dst, _, _, _ = mock_sync_file[0]
        assert "settings.json" in str(dst)


class TestSyncAppPull:
    """Tests for sync_app_pull()."""

    def test_empty_source_returns_zero(self, tmp_repo_root, sample_app, mock_get_source_files, capture_logging):
        """Returns (0,0) when source has no files."""
        mock_get_source_files([])
        synced, failed = sync_app_pull(sample_app, dry_run=True)
        assert synced == 0
        assert failed == 0

    def test_single_file_sync(self, tmp_repo_root, sample_app, mock_get_source_files, mock_sync_file, capture_logging, monkeypatch):
        """Syncs single file correctly in pull direction."""
        # Create a file that looks like it's in the config dir
        fake_config_dir = tmp_repo_root / "fake_config" / "testapp"
        fake_config_dir.mkdir(parents=True, exist_ok=True)
        src_file = fake_config_dir / "config.toml"
        src_file.write_text("content")
        mock_get_source_files([src_file])
        # Mock resolve_config_path to return our fake config dir
        monkeypatch.setattr(
            "dotfiles.sync.resolve_config_path",
            lambda app, relative="": fake_config_dir / relative if relative else fake_config_dir,
        )
        synced, failed = sync_app_pull(sample_app, dry_run=True)
        assert synced == 1
        assert failed == 0


# ---------------------------------------------------------------------------
# sync_all
# ---------------------------------------------------------------------------

class TestSyncAll:
    """Tests for sync_all()."""

    def test_invalid_direction_raises(self):
        """Invalid direction raises ValueError."""
        with pytest.raises(ValueError, match="Invalid direction"):
            sync_all("invalid")

    def test_aggregates_no_failures(self, tmp_repo_root, mock_get_source_files, mock_sync_file, capture_logging):
        """Returns (0, 0) when all apps succeed."""
        mock_get_source_files([])
        _, failed = sync_all("push", dry_run=True)
        assert failed == 0

    def test_aggregates_with_failures(self, tmp_repo_root, monkeypatch, capture_logging):
        """Returns (0, N) when N apps have failures."""
        # Mock sync_app_push to return failure
        monkeypatch.setattr(
            "dotfiles.sync.sync_app_push",
            lambda app, dry_run=False, force=False: (0, 1),
        )
        _, failed = sync_all("push", dry_run=True)
        assert failed == 1
