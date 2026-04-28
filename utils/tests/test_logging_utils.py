"""Tests for dotfiles.logging_utils module."""

from __future__ import annotations

import pytest

import dotfiles.logging_utils as log_utils
from dotfiles.logging_utils import set_verbose


class TestVerboseSuppression:
    """Tests for verbose output gating."""

    def test_verbose_enabled_by_default(self):
        """Verbose is enabled by default (after reset)."""
        assert log_utils._verbose_enabled is True

    def test_set_verbose_false_disables(self):
        """set_verbose(False) disables verbose output."""
        set_verbose(False)
        assert log_utils._verbose_enabled is False

    def test_set_verbose_true_enables(self):
        """set_verbose(True) enables verbose output."""
        set_verbose(False)
        set_verbose(True)
        assert log_utils._verbose_enabled is True
