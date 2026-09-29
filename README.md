# git-aged

Find stale git repositories by last commit date.

## Install

```bash
uv tool install .
```

## Usage

```bash
# Find repos older than 30 days (default)
git-aged /path/to/search

# Custom threshold
git-aged --days 90 ~/projects

# JSON output
git-aged --json ~/projects
```

## Example Output

```
  245d  /home/user/projects/old-project
  180d  /home/user/projects/abandoned-tool
   92d  /home/user/projects/experimental

3 stale repo(s) found.
```
