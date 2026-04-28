"""Wallpaper management: list colors and sort by hue (refactored from sort_rainbow.py)."""

from __future__ import annotations

import colorsys
import concurrent.futures
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from dotfiles.logging_utils import info, success, warning, error, verbose, console as get_console

EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}
_INDEXED_PATTERN = re.compile(r"^\d{8}_\d{6}_\d{3}\..+$")


def _check_matugen() -> bool:
    """Check if matugen is available (lazy, called per command)."""
    try:
        subprocess.run(
            ["matugen", "--version"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return True
    except (FileNotFoundError, OSError):
        return False


def _extract_source_color(image_path: Path) -> str | None:
    """Run matugen on an image and return the source_color hex, or None on failure."""
    try:
        result = subprocess.run(
            [
                "matugen",
                "image",
                str(image_path),
                "--dry-run",
                "--json",
                "hex",
                "--source-color-index",
                "0",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            warning(f"matugen failed on {image_path.name}: {result.stderr.strip()}")
            return None
        data = json.loads(result.stdout)
        return data["colors"]["source_color"]["default"]["color"]
    except (json.JSONDecodeError, KeyError) as exc:
        warning(f"Failed to parse color for {image_path.name}: {exc}")
        return None
    except subprocess.TimeoutExpired:
        warning(f"matugen timed out on {image_path.name}")
        return None


def _hex_to_hue(hex_color: str) -> float:
    """Convert a hex color string like '#3f6c9f' to HSL hue (0.0-1.0)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (
        int(hex_color[0:2], 16) / 255.0,
        int(hex_color[2:4], 16) / 255.0,
        int(hex_color[4:6], 16) / 255.0,
    )
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------


def list_wallpapers(pictures_dir: Path, max_workers: int = 8) -> None:
    """List all wallpapers with their Matugen source colors and hue angles.

    Also identifies files that don't follow the indexed naming pattern
    (YYYYMMDD_HHMMSS_NNN.ext) — these are "unindexed" wallpapers.
    """
    if not _check_matugen():
        error("matugen is required for wallpaper commands but not found on PATH.")
        raise SystemExit(1)

    images = sorted(
        p
        for p in pictures_dir.iterdir()
        if p.is_file() and p.suffix.lower() in EXTENSIONS
    )

    if not images:
        info(f"No image files found in {pictures_dir}")
        return

    info(f"Found {len(images)} images in {pictures_dir}")

    results: list[tuple[float, str, Path]] = []
    unindexed: list[Path] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(_extract_source_color, p): p for p in images}
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            color = future.result()
            if color is None:
                continue
            hue = _hex_to_hue(color)
            results.append((hue, color, path))

            # Check if file follows indexed naming pattern
            if not _INDEXED_PATTERN.match(path.name):
                unindexed.append(path)

    if not results:
        info("No colors extracted - nothing to display.")
        return

    # Sort by hue
    results.sort(key=lambda x: (x[0], x[2].name))

    # Display as rich table
    console = get_console()
    from rich.table import Table

    table = Table(title="Wallpaper Colors")
    table.add_column("Filename", style="bold")
    table.add_column("Source Color", style="bold")
    table.add_column("Hue", justify="right")
    table.add_column("Indexed", justify="center")

    for hue, color, path in results:
        is_indexed = "✓" if _INDEXED_PATTERN.match(path.name) else "✗"
        style = "dim" if not _INDEXED_PATTERN.match(path.name) else None
        table.add_row(
            path.name,
            color,
            f"{hue * 360:.0f}°",
            is_indexed,
            style=style,  # type: ignore[arg-type]
        )

    console.print(table)

    if unindexed:
        warning(f"{len(unindexed)} file(s) outside indexed naming pattern:")
        for p in sorted(unindexed, key=lambda x: x.name):
            info(f"  {p.name}")


# ---------------------------------------------------------------------------
# sort command
# ---------------------------------------------------------------------------


def sort_wallpapers(
    pictures_dir: Path,
    max_workers: int = 8,
    dry_run: bool = False,
) -> None:
    """Sort wallpapers by source color hue into rainbow order.

    Outputs timestamped copies and cleans up output from previous runs.
    Only deletes files matching the indexed naming pattern.
    """
    if not _check_matugen():
        error("matugen is required for wallpaper commands but not found on PATH.")
        raise SystemExit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    images = sorted(
        p
        for p in pictures_dir.iterdir()
        if p.is_file() and p.suffix.lower() in EXTENSIONS
    )

    if not images:
        error(f"No image files found in {pictures_dir}")
        raise SystemExit(1)

    info(f"Found {len(images)} images")

    results: list[tuple[float, Path]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(_extract_source_color, p): p for p in images}
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            color = future.result()
            if color is None:
                continue
            hue = _hex_to_hue(color)
            results.append((hue, path))
            verbose(f"  {path.name} -> {color} (hue: {hue * 360:.0f}°)")

    if not results:
        error("No colors extracted - nothing to do.")
        raise SystemExit(1)

    # Sort by hue, then filename
    results.sort(key=lambda x: (x[0], x[1].name))

    current_prefix = f"{timestamp}_"

    if dry_run:
        info(f"[DRY-RUN] Would sort {len(results)} wallpapers:")
        for i, (hue, src) in enumerate(results, start=1):
            new_name = f"{current_prefix}{i:03d}{src.suffix}"
            verbose(f"  [{hue * 360:3.0f}°] {src.name} -> {new_name}")

        # Show what would be deleted
        to_delete = []
        for f in pictures_dir.iterdir():
            if f.is_file() and f.suffix.lower() in EXTENSIONS:
                fname = f.name
                if _INDEXED_PATTERN.match(fname) and not fname.startswith(current_prefix):
                    to_delete.append(f)

        if to_delete:
            info(f"[DRY-RUN] Would delete {len(to_delete)} old output file(s):")
            for f in sorted(to_delete, key=lambda x: x.name):
                verbose(f"  {f.name}")

        warning("Remember to configure your Desktop Manager Settings to use the sorted wallpaper directory.")
        return

    # Create output directory
    pictures_dir.mkdir(parents=True, exist_ok=True)

    # Copy sorted wallpapers with new names
    for i, (hue, src_path) in enumerate(results, start=1):
        new_name = f"{current_prefix}{i:03d}{src_path.suffix}"
        dst = pictures_dir / new_name
        shutil.copy2(str(src_path), str(dst))
        verbose(f"  [{hue * 360:3.0f}°] {src_path.name} -> {new_name}")

    # Clean up old output files (only those matching indexed pattern)
    deleted = 0
    for f in pictures_dir.iterdir():
        if f.is_file() and f.suffix.lower() in EXTENSIONS:
            fname = f.name
            if _INDEXED_PATTERN.match(fname) and not fname.startswith(current_prefix):
                f.unlink()
                deleted += 1

    if deleted:
        info(f"  (cleaned up {deleted} file(s) from previous run)")

    success(f"Done - {len(results)} wallpapers in {pictures_dir}")
    warning("Remember to configure your Desktop Manager Settings to use the sorted wallpaper directory.")
