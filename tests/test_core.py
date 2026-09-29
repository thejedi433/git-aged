"""Tests for git-aged."""

import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from git_aged.core import get_last_commit_days, find_repos


def test_get_last_commit_days_fresh_repo(tmp_path):
    """A repo with a recent commit returns 0 or 1 day."""
    repo = tmp_path / "fresh"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    (repo / "file.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    days = get_last_commit_days(repo)
    assert days == 0


def test_get_last_commit_days_old_commit(tmp_path):
    """An old commit returns the correct age in days."""
    repo = tmp_path / "old"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    (repo / "file.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)

    # Commit with date 100 days ago
    old_date = (datetime.now(timezone.utc) - timedelta(days=100)).strftime("%Y-%m-%dT%H:%M:%S")
    env = {
        "GIT_AUTHOR_DATE": old_date,
        "GIT_COMMITTER_DATE": old_date,
    }
    subprocess.run(["git", "commit", "-m", "old"], cwd=repo, check=True, capture_output=True, env=env)

    days = get_last_commit_days(repo)
    assert 99 <= days <= 101


def test_get_last_commit_days_no_commits(tmp_path):
    """A repo with no commits returns -1."""
    repo = tmp_path / "empty"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

    days = get_last_commit_days(repo)
    assert days == -1


def test_find_repos_filters_by_age(tmp_path):
    """find_repos only returns repos older than min_days."""
    # Fresh repo
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    subprocess.run(["git", "init"], cwd=fresh, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=fresh, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=fresh, check=True, capture_output=True)
    (fresh / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=fresh, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=fresh, check=True, capture_output=True)

    # Old repo
    old = tmp_path / "old"
    old.mkdir()
    subprocess.run(["git", "init"], cwd=old, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=old, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=old, check=True, capture_output=True)
    (old / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=old, check=True, capture_output=True)
    old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S")
    env = {"GIT_AUTHOR_DATE": old_date, "GIT_COMMITTER_DATE": old_date}
    subprocess.run(["git", "commit", "-m", "old"], cwd=old, check=True, capture_output=True, env=env)

    repos = find_repos(tmp_path, min_days=30)
    assert len(repos) == 1
    assert repos[0][0].name == "old"
    assert repos[0][1] >= 59


def test_find_repos_empty_root(tmp_path):
    """No repos returns empty list."""
    repos = find_repos(tmp_path, min_days=0)
    assert repos == []
