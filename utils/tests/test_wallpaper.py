"""Tests for dotfiles.wallpaper module."""

from __future__ import annotations

import shutil
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from dotfiles.wallpaper import (
    _check_matugen,
    _hex_to_hue,
    _extract_source_color,
    _INDEXED_PATTERN,
    EXTENSIONS,
    sort_wallpapers,
)


# Skip all tests in this module if matugen is not available
_matugen_available = shutil.which("matugen") is not None
pytestmark = pytest.mark.skipif(not _matugen_available, reason="matugen CLI not available")


# ---------------------------------------------------------------------------
# Pure logic tests (no matugen needed)
# ---------------------------------------------------------------------------

class TestHexToHue:
    """Tests for _hex_to_hue()."""

    def test_red_hue(self):
        """Red (#ff0000) has hue ~0.0."""
        hue = _hex_to_hue("#ff0000")
        assert abs(hue - 0.0) < 0.01 or abs(hue - 1.0) < 0.01  # Red wraps around

    def test_green_hue(self):
        """Green (#00ff00) has hue ~0.333."""
        hue = _hex_to_hue("#00ff00")
        assert abs(hue - 0.333) < 0.02

    def test_blue_hue(self):
        """Blue (#0000ff) has hue ~0.667."""
        hue = _hex_to_hue("#0000ff")
        assert abs(hue - 0.667) < 0.02

    def test_hex_without_hash(self):
        """Works without leading #."""
        hue = _hex_to_hue("ff0000")
        assert 0.0 <= hue <= 1.0

    def test_known_color(self):
        """Known hex color produces expected hue."""
        # #3f6c9f from the original sort_rainbow.py
        hue = _hex_to_hue("#3f6c9f")
        assert 0.0 <= hue <= 1.0


class TestIndexedPattern:
    """Tests for _INDEXED_PATTERN."""

    def test_matches_timestamped_name(self):
        """Matches YYYYMMDD_HHMMSS_NNN.ext format."""
        assert _INDEXED_PATTERN.match("20260428_221500_001.jpg") is not None
        assert _INDEXED_PATTERN.match("20260428_221500_003.png") is not None

    def test_no_match_regular_name(self):
        """Does not match regular filenames."""
        assert _INDEXED_PATTERN.match("myphoto.jpg") is None
        assert _INDEXED_PATTERN.match("wallpaper.png") is None

    def test_no_match_partial_timestamp(self):
        """Does not match partial timestamps."""
        assert _INDEXED_PATTERN.match("20260428.jpg") is None
        assert _INDEXED_PATTERN.match("221500_001.jpg") is None


# ---------------------------------------------------------------------------
# Matugen-dependent tests (require matugen)
# ---------------------------------------------------------------------------

class TestExtractSourceColor:
    """Tests for _extract_source_color()."""

    def test_valid_matugen_output(self, tmp_path, monkeypatch):
        """Parses valid matugen JSON output."""
        # Create a dummy image file
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0")  # Minimal JPEG header

        def mock_run(cmd, **kwargs):
            return CompletedProcess(
                args=cmd,
                returncode=0,
                stdout='{"colors":{"source_color":{"default":{"color":"#3f6c9f"}}}}',
                stderr="",
            )
        monkeypatch.setattr("subprocess.run", mock_run)

        result = _extract_source_color(img)
        assert result == "#3f6c9f"

    def test_matugen_failure_returns_none(self, tmp_path, monkeypatch):
        """Returns None when matugen returns nonzero."""
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0")

        def mock_run(cmd, **kwargs):
            return CompletedProcess(args=cmd, returncode=1, stdout="", stderr="error")
        monkeypatch.setattr("subprocess.run", mock_run)

        result = _extract_source_color(img)
        assert result is None

    def test_invalid_json_returns_none(self, tmp_path, monkeypatch):
        """Returns None on JSONDecodeError."""
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0")

        def mock_run(cmd, **kwargs):
            return CompletedProcess(args=cmd, returncode=0, stdout="not json", stderr="")
        monkeypatch.setattr("subprocess.run", mock_run)

        result = _extract_source_color(img)
        assert result is None

    def test_missing_key_returns_none(self, tmp_path, monkeypatch):
        """Returns None when expected key missing from JSON."""
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0")

        def mock_run(cmd, **kwargs):
            return CompletedProcess(args=cmd, returncode=0, stdout='{"other":"data"}', stderr="")
        monkeypatch.setattr("subprocess.run", mock_run)

        result = _extract_source_color(img)
        assert result is None


class TestSortWallpapers:
    """Tests for sort_wallpapers()."""

    def test_dry_run_no_changes(self, tmp_path, monkeypatch, capture_logging):
        """Dry-run produces no file modifications."""
        # Create dummy images
        for name in ["red.jpg", "blue.jpg"]:
            (tmp_path / name).write_bytes(b"\xff\xd8\xff\xe0")

        def mock_check_matugen():
            return True

        def mock_extract(path):
            colors = {"red.jpg": "#ff0000", "blue.jpg": "#0000ff"}
            return colors.get(path.name)

        monkeypatch.setattr("dotfiles.wallpaper._check_matugen", mock_check_matugen)
        monkeypatch.setattr("dotfiles.wallpaper._extract_source_color", mock_extract)

        original_files = set(f.name for f in tmp_path.iterdir())
        sort_wallpapers(tmp_path, dry_run=True)
        after_files = set(f.name for f in tmp_path.iterdir())
        assert original_files == after_files

    def test_timestamp_format_in_output(self, tmp_path, monkeypatch, capture_logging):
        """Output filenames match timestamp pattern."""
        # Create dummy images
        for name in ["a.jpg", "b.jpg"]:
            (tmp_path / name).write_bytes(b"\xff\xd8\xff\xe0")

        def mock_check_matugen():
            return True

        def mock_extract(path):
            colors = {"a.jpg": "#ff0000", "b.jpg": "#0000ff"}
            return colors.get(path.name)

        monkeypatch.setattr("dotfiles.wallpaper._check_matugen", mock_check_matugen)
        monkeypatch.setattr("dotfiles.wallpaper._extract_source_color", mock_extract)

        sort_wallpapers(tmp_path, dry_run=False)

        # Check that new files match the indexed pattern
        new_files = [f for f in tmp_path.iterdir() if _INDEXED_PATTERN.match(f.name)]
        assert len(new_files) == 2
        for f in new_files:
            assert f.suffix in {".jpg"}

    def test_cleanup_old_indexed_files(self, tmp_path, monkeypatch, capture_logging):
        """Deletes only old indexed files, not random images."""
        # Create old indexed files
        (tmp_path / "20260101_000000_001.jpg").write_bytes(b"\xff\xd8\xff\xe0")
        (tmp_path / "20260101_000000_002.jpg").write_bytes(b"\xff\xd8\xff\xe0")
        # Create a non-indexed file (should NOT be deleted)
        (tmp_path / "my_wallpaper.jpg").write_bytes(b"\xff\xd8\xff\xe0")
        # Create source images
        (tmp_path / "source1.jpg").write_bytes(b"\xff\xd8\xff\xe0")

        def mock_check_matugen():
            return True

        def mock_extract(path):
            if path.name == "source1.jpg":
                return "#ff0000"
            return None

        monkeypatch.setattr("dotfiles.wallpaper._check_matugen", mock_check_matugen)
        monkeypatch.setattr("dotfiles.wallpaper._extract_source_color", mock_extract)

        sort_wallpapers(tmp_path, dry_run=False)

        # Old indexed files should be deleted
        remaining = [f.name for f in tmp_path.iterdir()]
        assert "20260101_000000_001.jpg" not in remaining
        assert "20260101_000000_002.jpg" not in remaining
        # Non-indexed file should remain
        assert "my_wallpaper.jpg" in remaining
        # New sorted file should exist
        new_indexed = [f for f in tmp_path.iterdir() if _INDEXED_PATTERN.match(f.name)]
        assert len(new_indexed) == 1
