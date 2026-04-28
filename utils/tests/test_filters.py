"""Tests for dotfiles.filters module."""

from __future__ import annotations

import os
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from dotfiles.config import AppConfig, FileMapping
from dotfiles.filters import (
    matches_glob,
    should_sync_file,
    is_gitignored,
    get_source_files,
)


# ---------------------------------------------------------------------------
# matches_glob (pure logic, no mocking needed)
# ---------------------------------------------------------------------------

class TestMatchesGlob:
    """Tests for matches_glob() — bash-compatible glob matching."""

    def test_star_ext_matches_basename(self):
        """*.jsonc matches foo.jsonc."""
        assert matches_glob("foo.jsonc", "*.jsonc") is True

    def test_star_ext_matches_subdir_basename(self):
        """*.jsonc matches sub/foo.jsonc (secondary case)."""
        assert matches_glob("sub/foo.jsonc", "*.jsonc") is True

    def test_star_ext_matches_deep_path(self):
        """*.jsonc matches sub/deep/foo.jsonc (fnmatch * matches /)."""
        assert matches_glob("sub/deep/foo.jsonc", "*.jsonc") is True

    def test_dir_pattern_matches_component(self):
        """themes/ matches paths with themes as a component."""
        assert matches_glob("themes/dark.toml", "themes/") is True
        assert matches_glob("zed/themes/dark.toml", "themes/") is True

    def test_dir_pattern_no_match(self):
        """themes/ does not match unrelated paths."""
        assert matches_glob("configs/settings.json", "themes/") is False

    def test_wildcard_basename(self):
        """*backup* matches basename containing 'backup'."""
        assert matches_glob("settings.backup", "*backup*") is True
        assert matches_glob("sub/settings.backup", "*backup*") is True

    def test_no_match(self):
        """Unrelated patterns return False."""
        assert matches_glob("foo.json", "*.toml") is False
        assert matches_glob("foo.json", "bar") is False

    def test_exact_basename_match(self):
        """Exact filename match."""
        assert matches_glob("lazy-lock.json", "lazy-lock.json") is True

    def test_path_object_input(self):
        """Accepts Path objects."""
        assert matches_glob(Path("foo.jsonc"), "*.jsonc") is True


# ---------------------------------------------------------------------------
# should_sync_file
# ---------------------------------------------------------------------------

class TestShouldSyncFile:
    """Tests for should_sync_file()."""

    def test_include_whitelist_passes_matching(self, sample_app, tmp_repo_root, mock_git_available):
        """Include patterns: matching basename passes."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
            include=["*.jsonc"],
        )
        assert should_sync_file(app, "foo.jsonc", "push", respect_gitignore=False) is True

    def test_include_whitelist_blocks_nonmatching(self, sample_app, tmp_repo_root, mock_git_available):
        """Include patterns: non-matching basename blocked."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
            include=["*.jsonc"],
        )
        assert should_sync_file(app, "foo.toml", "push", respect_gitignore=False) is False

    def test_exclude_blocks_matching(self, sample_app, tmp_repo_root, mock_git_available):
        """Exclude patterns: matching basename blocked."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
            exclude=["*.backup"],
        )
        assert should_sync_file(app, "settings.backup", "push", respect_gitignore=False) is False

    def test_exclude_passes_nonmatching(self, sample_app, tmp_repo_root, mock_git_available):
        """Exclude patterns: non-matching basename passes."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
            exclude=["*.backup"],
        )
        assert should_sync_file(app, "settings.json", "push", respect_gitignore=False) is True

    def test_include_then_exclude(self, sample_app, tmp_repo_root, mock_git_available):
        """Include passes, then exclude filters."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
            include=["*.json", "*.jsonc"],
            exclude=["settings.json"],
        )
        assert should_sync_file(app, "tasks.json", "push", respect_gitignore=False) is True
        assert should_sync_file(app, "settings.json", "push", respect_gitignore=False) is False

    def test_gitignored_returns_false(self, sample_app, tmp_repo_root, mock_git_available, monkeypatch):
        """Gitignored file returns False."""
        monkeypatch.setattr("dotfiles.filters.is_gitignored", lambda path: True)
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
        )
        filepath = str(tmp_repo_root / "test" / "ignored.txt")
        assert should_sync_file(app, filepath, "push", respect_gitignore=True) is False

    def test_not_gitignored_returns_true(self, sample_app, tmp_repo_root, mock_git_available, monkeypatch):
        """Non-gitignored file returns True."""
        mock = lambda cmd, **kw: CompletedProcess(args=cmd, returncode=1)
        monkeypatch.setattr("subprocess.run", mock)
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
        )
        filepath = str(tmp_repo_root / "test" / "notignored.txt")
        assert should_sync_file(app, filepath, "push", respect_gitignore=True) is True

    def test_git_unavailable_skips_check(self, sample_app, tmp_repo_root, mock_git_unavailable):
        """When git unavailable, gitignore check skipped (returns True)."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
        )
        assert should_sync_file(app, "/some/path/file.txt", "push", respect_gitignore=True) is True

    def test_respect_gitignore_false_skips(self, sample_app, tmp_repo_root, mock_git_available):
        """respect_gitignore=False skips git check entirely."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
        )
        assert should_sync_file(app, "/any/path.txt", "push", respect_gitignore=False) is True

    def test_no_patterns_passes_all(self, sample_app, tmp_repo_root, mock_git_available):
        """No include/exclude patterns passes everything."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
        )
        assert should_sync_file(app, "anything.txt", "push", respect_gitignore=False) is True


# ---------------------------------------------------------------------------
# is_gitignored
# ---------------------------------------------------------------------------

class TestIsGitignored:
    """Tests for is_gitignored()."""

    def test_git_unavailable_returns_false(self, mock_git_unavailable):
        """Returns False when git is not available."""
        assert is_gitignored("some/file.txt") is False

    def test_outside_repo_returns_false(self, tmp_repo_root, mock_git_available):
        """Path outside repo returns False silently."""
        assert is_gitignored("/outside/repo/file.txt") is False

    def test_git_error_returns_false(self, tmp_repo_root, mock_git_available, monkeypatch, capture_logging):
        """Git exit code >=128 returns False with warning."""
        def mock_run(cmd, **kwargs):
            if "check-ignore" in cmd:
                return CompletedProcess(args=cmd, returncode=128, stdout="", stderr="fatal")
            return CompletedProcess(args=cmd, returncode=0)
        monkeypatch.setattr("subprocess.run", mock_run)
        result = is_gitignored(str(tmp_repo_root / "test.txt"))
        assert result is False


# ---------------------------------------------------------------------------
# get_source_files
# ---------------------------------------------------------------------------

class TestGetSourceFiles:
    """Tests for get_source_files()."""

    def test_directory_type_enumerates_files(self, tmp_repo_root, sample_app, mock_git_available):
        """Lists files from directory."""
        # Create actual files in the repo
        app_dir = tmp_repo_root / "testapp"
        app_dir.mkdir(exist_ok=True)
        (app_dir / "file1.txt").write_text("content")
        (app_dir / "file2.txt").write_text("content")
        result = get_source_files(sample_app, "push", respect_gitignore=False)
        names = [f.name for f in result]
        assert "file1.txt" in names
        assert "file2.txt" in names

    def test_prunes_excluded_dirs(self, tmp_repo_root, mock_git_available):
        """Directories matching exclude with / suffix are skipped."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
            exclude=["themes/"],
        )
        app_dir = tmp_repo_root / "test"
        app_dir.mkdir(exist_ok=True)
        (app_dir / "good.txt").write_text("content")
        themes = app_dir / "themes"
        themes.mkdir()
        (themes / "dark.toml").write_text("content")
        result = get_source_files(app, "push", respect_gitignore=False)
        names = [f.name for f in result]
        assert "good.txt" in names
        assert "dark.toml" not in names

    def test_file_type_returns_single(self, tmp_repo_root, mock_git_available):
        """Single file returned for type=file."""
        app = AppConfig(
            name="test", type="file", repo_path="testfile", config_path="testfile",
        )
        testfile = tmp_repo_root / "testfile"
        testfile.write_text("content")
        result = get_source_files(app, "push", respect_gitignore=False)
        assert len(result) == 1
        assert result[0].name == "testfile"

    def test_missing_source_returns_empty(self, tmp_repo_root, sample_app, mock_git_available):
        """Returns empty list when source dir doesn't exist."""
        result = get_source_files(sample_app, "push", respect_gitignore=False)
        assert result == []

    def test_recursive_enumerates_subdirs(self, tmp_repo_root, mock_git_available):
        """Recursive mode lists files in subdirectories."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
            recursive=True,
        )
        app_dir = tmp_repo_root / "test"
        app_dir.mkdir(exist_ok=True)
        (app_dir / "root.txt").write_text("content")
        sub = app_dir / "sub"
        sub.mkdir()
        (sub / "nested.txt").write_text("content")
        result = get_source_files(app, "push", respect_gitignore=False)
        names = [f.name for f in result]
        assert "root.txt" in names
        assert "nested.txt" in names

    def test_non_recursive_skips_subdirs(self, tmp_repo_root, mock_git_available):
        """Non-recursive mode skips subdirectory files."""
        app = AppConfig(
            name="test", type="directory", repo_path="test", config_path="test",
            recursive=False,
        )
        app_dir = tmp_repo_root / "test"
        app_dir.mkdir(exist_ok=True)
        (app_dir / "root.txt").write_text("content")
        sub = app_dir / "sub"
        sub.mkdir()
        (sub / "nested.txt").write_text("content")
        result = get_source_files(app, "push", respect_gitignore=False)
        names = [f.name for f in result]
        assert "root.txt" in names
        assert "nested.txt" not in names
