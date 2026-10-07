"""Tests for git-aged CLI."""

import subprocess
from pathlib import Path
from click.testing import CliRunner
from git_aged.cli import main


def test_cli_default_output(tmp_path):
    """CLI shows repos older than threshold."""
    runner = CliRunner()

    # Create a fresh repo
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    subprocess.run(["git", "init"], cwd=fresh, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=fresh, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=fresh, check=True, capture_output=True)
    (fresh / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=fresh, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=fresh, check=True, capture_output=True)

    result = runner.invoke(main, [str(tmp_path)])
    assert result.exit_code == 0
    assert "No repos older than 30 days" in result.output


def test_cli_json_output(tmp_path):
    """CLI outputs valid JSON with --json flag."""
    runner = CliRunner()

    result = runner.invoke(main, ["--json", str(tmp_path)])
    assert result.exit_code == 0
    assert "[]" in result.output or result.output.strip() == "[]"


def test_cli_custom_days(tmp_path):
    """CLI respects custom --days threshold."""
    runner = CliRunner()

    # Create an old repo (50 days)
    old = tmp_path / "old"
    old.mkdir()
    subprocess.run(["git", "init"], cwd=old, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=old, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=old, check=True, capture_output=True)
    (old / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=old, check=True, capture_output=True)
    from datetime import datetime, timezone, timedelta
    old_date = (datetime.now(timezone.utc) - timedelta(days=50)).strftime("%Y-%m-%dT%H:%M:%S")
    env = {"GIT_AUTHOR_DATE": old_date, "GIT_COMMITTER_DATE": old_date}
    subprocess.run(["git", "commit", "-m", "old"], cwd=old, check=True, capture_output=True, env=env)

    # Should not show with 60-day threshold
    result = runner.invoke(main, ["--days", "60", str(tmp_path)])
    assert result.exit_code == 0
    assert "No repos older than 60 days" in result.output

    # Should show with 30-day threshold
    result = runner.invoke(main, ["--days", "30", str(tmp_path)])
    assert result.exit_code == 0
    assert "old" in result.output
    assert "1 stale repo(s) found" in result.output


def test_cli_exclude_flag(tmp_path):
    """CLI --exclude flag filters out matching repos."""
    runner = CliRunner()

    # Create two old repos
    for name in ["repo-keep", "repo-skip"]:
        repo = tmp_path / name
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
        (repo / "f.txt").write_text("x")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        from datetime import datetime, timezone, timedelta
        old_date = (datetime.now(timezone.utc) - timedelta(days=50)).strftime("%Y-%m-%dT%H:%M:%S")
        env = {"GIT_AUTHOR_DATE": old_date, "GIT_COMMITTER_DATE": old_date}
        subprocess.run(["git", "commit", "-m", "old"], cwd=repo, check=True, capture_output=True, env=env)

    # Without exclude: both repos shown
    result = runner.invoke(main, ["--days", "30", str(tmp_path)])
    assert result.exit_code == 0
    assert "repo-keep" in result.output
    assert "repo-skip" in result.output
    assert "2 stale repo(s) found" in result.output

    # With exclude: only one repo shown
    result = runner.invoke(main, ["--days", "30", "--exclude", "repo-skip", str(tmp_path)])
    assert result.exit_code == 0
    assert "repo-keep" in result.output
    assert "repo-skip" not in result.output
    assert "1 stale repo(s) found" in result.output

    # Multiple exclude patterns
    result = runner.invoke(main, ["--days", "30", "-e", "repo-*", str(tmp_path)])
    assert result.exit_code == 0
    assert "No repos older than 30 days" in result.output


def test_cli_max_depth_flag(tmp_path):
    """CLI --max-depth flag limits search depth."""
    runner = CliRunner()

    # Create repos at different depths
    for depth, name in [(1, "shallow"), (2, "deep")]:
        if depth == 1:
            repo = tmp_path / name
        else:
            repo = tmp_path / "sub" / name
            repo.parent.mkdir(parents=True, exist_ok=True)
        repo.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
        (repo / "f.txt").write_text("x")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        from datetime import datetime, timezone, timedelta
        old_date = (datetime.now(timezone.utc) - timedelta(days=50)).strftime("%Y-%m-%dT%H:%M:%S")
        env = {"GIT_AUTHOR_DATE": old_date, "GIT_COMMITTER_DATE": old_date}
        subprocess.run(["git", "commit", "-m", "old"], cwd=repo, check=True, capture_output=True, env=env)

    # Without max_depth: both repos shown
    result = runner.invoke(main, ["--days", "30", str(tmp_path)])
    assert result.exit_code == 0
    assert "shallow" in result.output
    assert "deep" in result.output
    assert "2 stale repo(s) found" in result.output

    # With max_depth=1: only shallow repo shown
    result = runner.invoke(main, ["--days", "30", "--max-depth", "1", str(tmp_path)])
    assert result.exit_code == 0
    assert "shallow" in result.output
    assert "deep" not in result.output
    assert "1 stale repo(s) found" in result.output
