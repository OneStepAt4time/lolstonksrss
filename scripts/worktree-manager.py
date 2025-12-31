#!/usr/bin/env python3
"""
CLI per gestione worktrees - usato da agenti e manualmente.

Questo script fornisce un'interfaccia comando per gestire git worktrees
per sviluppo parallelo con agenti Claude Code.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import click  # noqa: E402

from src.worktree_manager import WorktreeManager  # noqa: E402


@click.group()
@click.option(
    "--repo-root",
    type=click.Path(exists=True, path_type=Path),
    help="Path to git repository root (auto-detected if not specified)",
)
@click.pass_context
def cli(ctx, repo_root):
    """
    Worktree Management CLI for LoL Stonks RSS.

    Manage git worktrees for parallel development with Claude Code agents.
    """
    ctx.ensure_object(dict)
    try:
        ctx.obj["manager"] = WorktreeManager(repo_root=repo_root)
    except Exception as e:
        click.echo(f"Error initializing WorktreeManager: {e}", err=True)
        raise click.Abort() from e


@cli.command()
@click.argument("branch")
@click.option(
    "--path",
    type=click.Path(path_type=Path),
    help="Custom path for worktree (default: ../lolstonksrss-branch-name)",
)
@click.option(
    "--existing-branch",
    is_flag=True,
    help="Checkout existing branch instead of creating new one",
)
@click.pass_context
def create(ctx, branch, path, existing_branch):
    """
    Create a new worktree for a branch.

    Example: worktree-manager.py create feature/oauth2
    """
    wm = ctx.obj["manager"]

    try:
        info = wm.create_worktree(
            branch_name=branch,
            worktree_path=path,
            create_branch=not existing_branch,
        )

        click.echo(click.style("✓ Worktree created successfully!", fg="green", bold=True))
        click.echo(f"  Branch:  {info.branch}")
        click.echo(f"  Path:    {info.path}")
        click.echo(f"  Port:    {info.port}")
        click.echo(f"  DB:      data/articles-{info.db_suffix}.db")
        click.echo(f"  Commit:  {info.commit}")

    except Exception as e:
        click.echo(f"Error creating worktree: {e}", err=True)
        raise click.Abort() from e


@cli.command()
@click.pass_context
def list(ctx):
    """List all active worktrees."""
    wm = ctx.obj["manager"]

    try:
        worktrees = wm.list_worktrees()

        if not worktrees:
            click.echo("No worktrees found.")
            return

        click.echo(click.style("Active Worktrees:", fg="blue", bold=True))
        for wt in worktrees:
            port_info = f"port {wt.port}" if wt.port else "no port"
            click.echo(f"  • {wt.branch}")
            click.echo(f"    Path: {wt.path}")
            click.echo(f"    {port_info}")
            click.echo(f"    DB: data/articles-{wt.db_suffix}.db")
            click.echo(f"    Commit: {wt.commit}")
            click.echo()

        # Show capacity
        capacity = wm.get_available_capacity()
        if capacity > 0:
            click.echo(f"Available capacity: {capacity} more worktrees")
        else:
            click.echo(click.style("Warning: No available ports!", fg="yellow", bold=True))

    except Exception as e:
        click.echo(f"Error listing worktrees: {e}", err=True)
        raise click.Abort() from e


@cli.command()
@click.argument("branch")
@click.option(
    "--force",
    is_flag=True,
    help="Force removal even if worktree has uncommitted changes",
)
@click.pass_context
def cleanup(ctx, branch, force):
    """
    Remove a worktree and free its resources.

    Example: worktree-manager.py cleanup feature/oauth2
    """
    wm = ctx.obj["manager"]

    try:
        # Check if worktree exists
        worktree_info = None
        for wt in wm.list_worktrees():
            if wt.branch == branch:
                worktree_info = wt
                break

        if not worktree_info:
            click.echo(f"No worktree found for branch '{branch}'")
            raise click.Abort()

        # Warn if force not set and worktree might have changes
        if not force:
            click.echo(
                click.style(
                    f"Warning: This will remove the worktree at {worktree_info.path}",
                    fg="yellow",
                )
            )
            if not click.confirm("Continue?"):
                raise click.Abort()

        wm.cleanup_worktree(branch, force=force)
        click.echo(click.style(f"✓ Clean up worktree: {branch}", fg="green"))

    except Exception as e:
        click.echo(f"Error cleaning up worktree: {e}", err=True)
        raise click.Abort() from e


@cli.command()
@click.option(
    "--count",
    type=int,
    default=7,
    help="Number of worktrees to create (default: 7)",
)
@click.option(
    "--prefix",
    default="feature",
    help="Branch name prefix (default: feature)",
)
@click.pass_context
def create_multi(ctx, count, prefix):
    """
    Create multiple worktrees for parallel development.

    Example: worktree-manager.py create-multi --count 5
    """
    wm = ctx.obj["manager"]

    # Check capacity
    capacity = wm.get_available_capacity()
    if capacity < count:
        click.echo(
            click.style(
                f"Error: Only {capacity} worktrees available, requested {count}",
                fg="red",
            ),
            err=True,
        )
        raise click.Abort()

    click.echo(f"Creating {count} worktrees for parallel development...")

    created = []
    for i in range(1, count + 1):
        branch_name = f"{prefix}/agent-{i}-task"
        try:
            info = wm.create_worktree(branch_name)
            created.append(info)
            click.echo(
                click.style(
                    f"  ✓ [{i}/{count}] {branch_name} (port {info.port})",
                    fg="green",
                )
            )
        except Exception as e:
            click.echo(
                click.style(f"  ✗ [{i}/{count}] Failed to create {branch_name}: {e}", fg="red"),
                err=True,
            )
            # Clean up any created worktrees on failure
            for info in created:
                try:
                    wm.cleanup_worktree(info.branch, force=True)
                except Exception:
                    pass
            raise click.Abort() from None

    click.echo()
    click.echo(
        click.style(f"✓ Created {len(created)} worktrees successfully!", fg="green", bold=True)
    )
    click.echo("\nWorktree details:")
    for info in created:
        click.echo(f"  • {info.branch}: {info.path} (port {info.port})")


@cli.command()
@click.option(
    "--keep-main",
    is_flag=True,
    help="Keep main/master worktree if present",
)
@click.pass_context
def cleanup_all(ctx, keep_main):
    """Remove all worktrees and free all resources."""
    wm = ctx.obj["manager"]

    try:
        worktrees = wm.list_worktrees()

        if not worktrees:
            click.echo("No worktrees to clean up.")
            return

        # Filter out main/master if --keep-main
        to_cleanup = [wt for wt in worktrees if not (keep_main and wt.branch in ("main", "master"))]

        if not to_cleanup:
            click.echo("No worktrees to clean up (main/master preserved).")
            return

        click.echo(f"Cleaning up {len(to_cleanup)} worktree(s)...")

        for wt in to_cleanup:
            try:
                wm.cleanup_worktree(wt.branch, force=True)
                click.echo(click.style(f"  ✓ Cleaned up: {wt.branch}", fg="green"))
            except Exception as e:
                click.echo(
                    click.style(f"  ✗ Failed to cleanup {wt.branch}: {e}", fg="red"),
                    err=True,
                )

        # Prune stale metadata
        wm.prune()
        click.echo(click.style("✓ Pruned stale worktree metadata", fg="green"))

    except Exception as e:
        click.echo(f"Error during cleanup: {e}", err=True)
        raise click.Abort() from e


@cli.command()
@click.pass_context
def prune(ctx):
    """Clean up stale worktree metadata."""
    wm = ctx.obj["manager"]

    try:
        wm.prune()
        click.echo(click.style("✓ Pruned stale worktree metadata", fg="green"))
    except Exception as e:
        click.echo(f"Error pruning: {e}", err=True)
        raise click.Abort() from e


@cli.command()
@click.argument("branch")
@click.pass_context
def allocate(ctx, branch):
    """
    Allocate a port for a branch (without creating worktree).

    Example: worktree-manager.py allocate feature/test
    """
    wm = ctx.obj["manager"]

    try:
        port = wm.allocate_port(branch)
        click.echo(f"Allocated port {port} for branch '{branch}'")
    except Exception as e:
        click.echo(f"Error allocating port: {e}", err=True)
        raise click.Abort() from e


@cli.command()
@click.argument("branch")
@click.pass_context
def release(ctx, branch):
    """
    Release a port allocation for a branch.

    Example: worktree-manager.py release feature/test
    """
    wm = ctx.obj["manager"]

    try:
        wm.release_port(branch)
        click.echo(f"Released port for branch '{branch}'")
    except Exception as e:
        click.echo(f"Error releasing port: {e}", err=True)
        raise click.Abort() from e


@cli.command()
@click.pass_context
def status(ctx):
    """Show worktree system status."""
    wm = ctx.obj["manager"]

    try:
        worktrees = wm.list_worktrees()
        capacity = wm.get_available_capacity()

        click.echo(click.style("Worktree System Status", fg="blue", bold=True))
        click.echo()
        click.echo(f"Active worktrees: {len(worktrees)}")
        click.echo(f"Available capacity: {capacity}")
        click.echo(f"Port range: {wm.port_range_start}-{wm.port_range_end}")
        click.echo()

        if worktrees:
            click.echo(click.style("Port allocations:", fg="blue"))
            registry = wm._read_registry()
            for branch, port in sorted(registry.items()):
                click.echo(f"  {branch}: port {port}")

    except Exception as e:
        click.echo(f"Error getting status: {e}", err=True)
        raise click.Abort() from e


if __name__ == "__main__":
    cli()
