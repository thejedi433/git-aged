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


def test_get_depth():
    """_get_depth returns correct depth relative to root."""
    from git_aged.core import _get_depth
    root = Path("/some/root")
    repo1 = Path("/some/root/repo")
    repo2 = Path("/some/root/sub/repo")
    repo3 = Path("/some/root/sub/sub2/repo")
    assert _get_depth(repo1, root) == 1
    assert _get_depth(repo2, root) == 2
    assert _get_depth(repo3, root) == 3


def test_find_repos_with_max_depth(tmp_path):
    """find_repos respects max_depth limit."""
    # Create repos at different depths
    for depth, name in [(1, "shallow"), (2, "medium"), (3, "deep")]:
        if depth == 1:
            repo = tmp_path / name
        elif depth == 2:
            repo = tmp_path / "sub1" / name
            repo.parent.mkdir(parents=True, exist_ok=True)
        else:
            repo = tmp_path / "sub1" / "sub2" / name
            repo.parent.mkdir(parents=True, exist_ok=True)
        repo.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
        (repo / "f.txt").write_text("x")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        old_date = (datetime.now(timezone.utc) - timedelta(days=50)).strftime("%Y-%m-%dT%H:%M:%S")
        env = {"GIT_AUTHOR_DATE": old_date, "GIT_COMMITTER_DATE": old_date}
        subprocess.run(["git", "commit", "-m", "old"], cwd=repo, check=True, capture_output=True, env=env)

    # Without max_depth: all repos found
    repos = find_repos(tmp_path, min_days=30)
    assert len(repos) == 3

    # With max_depth=1: only shallow repo found
    repos = find_repos(tmp_path, min_days=30, max_depth=1)
    assert len(repos) == 1
    assert repos[0][0].name == "shallow"

    # With max_depth=2: shallow and medium repos found
    repos = find_repos(tmp_path, min_days=30, max_depth=2)
    assert len(repos) == 2
    names = {r[0].name for r in repos}
    assert names == {"shallow", "medium"}


def test_get_depth_unrelated_path():
    """_get_depth returns 0 when repo is not under root."""
    from git_aged.core import _get_depth
    root = Path("/some/root")
    unrelated = Path("/other/place/repo")
    assert _get_depth(unrelated, root) == 0
