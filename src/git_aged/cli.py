"""git-aged: Find stale git repositories."""

import click
from pathlib import Path
from .core import find_repos


@click.command()
@click.argument("root", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--days", "-d", default=30, help="Minimum stale threshold in days (default: 30)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--exclude", "-e", multiple=True, help="Exclude repos matching glob pattern (repeatable)")
@click.option("--max-depth", "-m", type=int, default=None, help="Maximum search depth (default: unlimited)")
def main(root: str, days: int, as_json: bool, exclude: tuple[str, ...], max_depth: int | None) -> None:
    """Find git repos with no commits for at least DAYS days."""
    exclude_patterns = list(exclude) if exclude else None
    repos = find_repos(Path(root).resolve(), days, exclude_patterns, max_depth)

    if as_json:
        import json
        data = [{"path": str(p), "days_ago": d} for p, d in repos]
        click.echo(json.dumps(data, indent=2))
    else:
        if not repos:
            click.echo(f"No repos older than {days} days found.")
            return
        for path, d in repos:
            click.echo(f"{d:>5}d  {path}")
        click.echo(f"\n{len(repos)} stale repo(s) found.")
