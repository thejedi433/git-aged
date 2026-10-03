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


def test_is_excluded_matches_pattern():
    """_is_excluded returns True for matching patterns."""
    from git_aged.core import _is_excluded
    repo = Path("/some/path/test-repo")
    assert _is_excluded(repo, ["test-*"]) is True
    assert _is_excluded(repo, ["*-repo"]) is True
    assert _is_excluded(repo, ["test-repo"]) is True
    assert _is_excluded(repo, ["other-*"]) is False
    assert _is_excluded(repo, []) is False


def test_find_repos_with_exclude_patterns(tmp_path):
    """find_repos excludes repos matching patterns."""
    # Create two old repos
    for name in ["old-keep", "old-exclude"]:
        repo = tmp_path / name
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
        (repo / "f.txt").write_text("x")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        old_date = (datetime.now(timezone.utc) - timedelta(days=50)).strftime("%Y-%m-%dT%H:%M:%S")
        env = {"GIT_AUTHOR_DATE": old_date, "GIT_COMMITTER_DATE": old_date}
        subprocess.run(["git", "commit", "-m", "old"], cwd=repo, check=True, capture_output=True, env=env)

    # Without exclude: both repos found
    repos = find_repos(tmp_path, min_days=30)
    assert len(repos) == 2

    # With exclude: only one repo found
    repos = find_repos(tmp_path, min_days=30, exclude_patterns=["old-exclude"])
    assert len(repos) == 1
    assert repos[0][0].name == "old-keep"

    # Multiple patterns
    repos = find_repos(tmp_path, min_days=30, exclude_patterns=["old-*"])
    assert len(repos) == 0


def test_get_last_commit_days_handles_bad_output(tmp_path):
    """get_last_commit_days returns -1 when git output is not a valid integer."""
    from unittest.mock import patch, MagicMock
    from git_aged.core import get_last_commit_days

    repo = tmp_path / "bad"
    repo.mkdir()

    # Mock subprocess to return non-integer output
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "not-a-number\n"
    with patch("git_aged.core.subprocess.run", return_value=mock_result):
        days = get_last_commit_days(repo)
        assert days == -1
