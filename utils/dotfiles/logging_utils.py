"""Colored logging utilities using Rich."""

from __future__ import annotations

import os
import sys
from typing import Any

from rich.console import Console
from rich.theme import Theme

# Respect NO_COLOR env var
_use_color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

_theme = Theme(
    {
        "info": "bold blue",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "dry_run": "dim",
        "verbose": "blue",
    }
)

_console = Console(theme=_theme, force_terminal=_use_color, stderr=False)
_err_console = Console(theme=_theme, force_terminal=_use_color, stderr=True)

_verbose_enabled: bool = True


def set_verbose(enabled: bool) -> None:
    """Enable or disable verbose output globally."""
    global _verbose_enabled
    _verbose_enabled = enabled


def info(msg: str, *args: Any, **kwargs: Any) -> None:
    """Log an informational message (always shown)."""
    _console.print("[info][INFO][/info] " + str(msg), *args, **kwargs)


def success(msg: str, *args: Any, **kwargs: Any) -> None:
    """Log a success message (always shown)."""
    _console.print("[success][OK][/success] " + str(msg), *args, **kwargs)


def error(msg: str, *args: Any, **kwargs: Any) -> None:
    """Log an error message to stderr (always shown)."""
    _err_console.print("[error][ERROR][/error] " + str(msg), *args, **kwargs)


def warning(msg: str, *args: Any, **kwargs: Any) -> None:
    """Log a warning message (always shown)."""
    _console.print("[warning][WARN][/warning] " + str(msg), *args, **kwargs)


def verbose(msg: str, *args: Any, **kwargs: Any) -> None:
    """Log a verbose message (only shown when verbose mode is on)."""
    if _verbose_enabled:
        _console.print("[verbose]  " + str(msg) + "[/verbose]", *args, **kwargs)


def dry_run_log(action: str, src: str, dst: str = "") -> None:
    """Log a dry-run preview action."""
    if dst:
        _console.print(f"[dry_run][DRY-RUN] {action}: {src} \u2192 {dst}[/dry_run]")
    else:
        _console.print(f"[dry_run][DRY-RUN] {action}: {src}[/dry_run]")


def console() -> Console:
    """Return the main Rich console for direct use."""
    return _console
