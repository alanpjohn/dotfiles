"""CLI entry point for the dotfiles tool."""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from dotfiles.config import ConfigError
from dotfiles.logging_utils import info, success, error, warning, verbose as log_verbose

app = typer.Typer(
    name="dotfiles",
    help="Dotfiles management CLI - sync configs between repo and ~/.config, manage wallpapers.",
    no_args_is_help=True,
)

wallpaper_app = typer.Typer(
    name="wallpaper",
    help="Manage wallpapers - list colors and sort by hue.",
    no_args_is_help=True,
)
app.add_typer(wallpaper_app)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    _version: Annotated[
        bool,
        typer.Option("--version", help="Show version and exit."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Enable verbose output (default)."),
    ] = True,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", help="Suppress verbose output."),
    ] = False,
) -> None:
    """Dotfiles management CLI."""
    if _version:
        try:
            version = importlib.metadata.version("dotfile-utils")
        except importlib.metadata.PackageNotFoundError:
            version = "0.2.0"
        typer.echo(f"dotfiles v{version}")
        raise typer.Exit(0)

    # Store verbosity settings in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose and not quiet
    ctx.obj["quiet"] = quiet


# ---------------------------------------------------------------------------
# push command
# ---------------------------------------------------------------------------

@app.command(name="push")
def push_cmd(
    ctx: typer.Context,
    app_name: Annotated[
        Optional[str],
        typer.Argument(help="Application name to sync (omit to sync all)."),
    ] = None,
    all_apps: Annotated[
        bool,
        typer.Option("--all", help="Sync all configured applications."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without syncing."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite destination even if newer."),
    ] = False,
) -> None:
    """Sync configuration files from repo to ~/.config."""
    from dotfiles.config import list_apps, get_app
    from dotfiles.sync import sync_app_push, sync_all
    from dotfiles.logging_utils import set_verbose

    set_verbose(ctx.obj.get("verbose", True))

    try:
        if app_name is not None and not all_apps:
            # Single app
            app = get_app(app_name)
            synced, failed = sync_app_push(app, dry_run=dry_run, force=force)
            if failed > 0:
                raise typer.Exit(4)
        else:
            # All apps
            _, failed = sync_all("push", dry_run=dry_run, force=force)
            if failed > 0:
                raise typer.Exit(4)
    except ConfigError as e:
        error(str(e))
        raise typer.Exit(3)


# ---------------------------------------------------------------------------
# pull command
# ---------------------------------------------------------------------------

@app.command(name="pull")
def pull_cmd(
    ctx: typer.Context,
    app_name: Annotated[
        Optional[str],
        typer.Argument(help="Application name to sync (omit to sync all)."),
    ] = None,
    all_apps: Annotated[
        bool,
        typer.Option("--all", help="Sync all configured applications."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without syncing."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite destination even if newer."),
    ] = False,
) -> None:
    """Sync configuration files from ~/.config to repo."""
    from dotfiles.config import list_apps, get_app
    from dotfiles.sync import sync_app_pull, sync_all
    from dotfiles.logging_utils import set_verbose

    set_verbose(ctx.obj.get("verbose", True))

    try:
        if app_name is not None and not all_apps:
            # Single app
            app = get_app(app_name)
            synced, failed = sync_app_pull(app, dry_run=dry_run, force=force)
            if failed > 0:
                raise typer.Exit(4)
        else:
            # All apps
            _, failed = sync_all("pull", dry_run=dry_run, force=force)
            if failed > 0:
                raise typer.Exit(4)
    except ConfigError as e:
        error(str(e))
        raise typer.Exit(3)


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------

@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    verbose_table: Annotated[
        bool,
        typer.Option("--verbose", help="Show detailed table."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List all configured applications."""
    from dotfiles.config import list_apps

    apps = list_apps()

    if json_output:
        import json

        result = []
        for a in apps:
            entry = {
                "name": a.name,
                "type": a.type,
                "repo_path": a.repo_path,
                "config_path": a.config_path,
                "recursive": a.recursive,
                "exclude": a.exclude,
                "include": a.include,
                "file_mappings": [
                    {"repo_name": m.repo_name, "config_name": m.config_name}
                    for m in a.file_mappings
                ],
            }
            result.append(entry)
        typer.echo(json.dumps(result, indent=2))
        return

    if verbose_table:
        from rich.table import Table
        from rich.console import Console

        console = Console()
        table = Table(title="Configured Applications")
        table.add_column("Name", style="bold cyan")
        table.add_column("Type")
        table.add_column("Repo Path")
        table.add_column("Config Path")
        table.add_column("Recursive")
        table.add_column("File Mappings")
        table.add_column("Exclude")
        table.add_column("Include")

        for a in apps:
            mappings = ", ".join(
                f"{m.repo_name}→{m.config_name}" for m in a.file_mappings
            ) or "—"
            table.add_row(
                a.name,
                a.type,
                a.repo_path,
                a.config_path,
                "✓" if a.recursive else "—",
                mappings,
                ", ".join(a.exclude) if a.exclude else "—",
                ", ".join(a.include) if a.include else "—",
            )
        console.print(table)
    else:
        for a in apps:
            typer.echo(a.name)


# ---------------------------------------------------------------------------
# help command (extended manual)
# ---------------------------------------------------------------------------

@app.command(name="help")
def help_cmd(
    ctx: typer.Context,
    _full: Annotated[
        bool,
        typer.Option("--full", help="Show the full README."),
    ] = False,
) -> None:
    """Show extended help and usage information."""
    typer.echo("dotfiles - Dotfiles Management CLI")
    typer.echo("")
    typer.echo("Commands:")
    typer.echo("  push [APP]    Sync repo -> ~/.config")
    typer.echo("  pull [APP]    Sync ~/.config -> repo")
    typer.echo("  list          List configured applications")
    typer.echo("  wallpaper     Wallpaper management (list, sort)")
    typer.echo("")
    typer.echo("Run 'dotfiles --help' for detailed command help.")
    typer.echo("Run 'dotfiles COMMAND --help' for command-specific options.")


# ---------------------------------------------------------------------------
# wallpaper list
# ---------------------------------------------------------------------------

@wallpaper_app.command(name="list")
def wallpaper_list(
    ctx: typer.Context,
    pictures_dir: Annotated[
        Path,
        typer.Option(
            "--pictures-dir",
            help="Directory containing wallpapers.",
            exists=True,
            file_okay=False,
            dir_okay=True,
        ),
    ] = Path.home() / "Pictures" / "Wallpapers",
    jobs: Annotated[
        int,
        typer.Option("--jobs", "-j", help="Number of parallel workers.", min=1),
    ] = 8,
) -> None:
    """List wallpapers with their Matugen source colors and hues."""
    from dotfiles.logging_utils import set_verbose
    from dotfiles.wallpaper import list_wallpapers

    set_verbose(ctx.obj.get("verbose", True))
    list_wallpapers(pictures_dir, max_workers=jobs)


# ---------------------------------------------------------------------------
# wallpaper sort
# ---------------------------------------------------------------------------

@wallpaper_app.command(name="sort")
def wallpaper_sort(
    ctx: typer.Context,
    pictures_dir: Annotated[
        Path,
        typer.Option(
            "--pictures-dir",
            help="Directory containing wallpapers.",
            exists=True,
            file_okay=False,
            dir_okay=True,
        ),
    ] = Path.home() / "Pictures" / "Wallpapers",
    jobs: Annotated[
        int,
        typer.Option("--jobs", "-j", help="Number of parallel workers.", min=1),
    ] = 8,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview sorting without making changes."),
    ] = False,
) -> None:
    """Sort wallpapers by hue into rainbow order."""
    from dotfiles.logging_utils import set_verbose
    from dotfiles.wallpaper import sort_wallpapers

    set_verbose(ctx.obj.get("verbose", True))
    sort_wallpapers(pictures_dir, max_workers=jobs, dry_run=dry_run)


if __name__ == "__main__":
    app()
