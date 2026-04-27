# Git History Safety

## What happened

A previous cleanup used a history-rewrite command that targeted all refs (`-- --all`) and then immediately removed recovery references (`refs/original`, reflog, gc prune).

That combination rewrote branch commit IDs and dropped prior commit graph entries, which made earlier feature commits (including the drawer implementation commits) unavailable in local history.

## Root cause

- Broad rewrite scope (`--all`) instead of limiting to the intended branch.
- No durable backup artifact before rewriting.
- Immediate cleanup (`reflog expire` + `git gc --prune=now`) removed easy recovery paths.

## Prevention policy

1. Never run branch-wide or repo-wide history rewrite without a backup bundle first.
2. Rewrite only the branch that needs cleanup.
3. Do not run reflog/gc cleanup until rewrite is validated and shared safely.
4. Use `--force-with-lease` for push after rewrite, never plain `--force`.

## Safe procedure (required)

Use the repository script:

```bash
scripts/git_safe_purge_paths.sh screenshot.png test_output.txt test_fail.txt
```

The script automatically:

- creates a full backup bundle under `backups/git-history/`
- creates a safety tag `safety/pre-rewrite-<timestamp>`
- rewrites only the current branch
- verifies specified paths are removed from current branch history

## Recovery

If rewrite goes wrong:

1. Restore from bundle:

```bash
git clone pre_rewrite_<timestamp>.bundle recovered-repo
```

2. Or reset to safety tag in original repo:

```bash
git reset --hard safety/pre-rewrite-<timestamp>
```

3. Coordinate force-push with the team before updating remote history.
