"""Core logic for finding stale git repositories."""

import subprocess
from datetime import datetime, timezone
from pathlib import Path


def get_last_commit_days(repo_path: Path) -> int:
    """Return days since last commit, or -1 if no commits."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return -1

        timestamp = int(result.stdout.strip())
        commit_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - commit_time).days
    except (ValueError, subprocess.TimeoutExpired):
        return -1


def find_repos(root: Path, min_days: int) -> list[tuple[Path, int]]:
    """Find all git repos under root with age >= min_days."""
    repos = []
    for git_dir in root.rglob(".git"):
        if git_dir.is_dir():
            repo_path = git_dir.parent
            days = get_last_commit_days(repo_path)
            if days >= min_days:
                repos.append((repo_path, days))

    return sorted(repos, key=lambda x: x[1], reverse=True)
