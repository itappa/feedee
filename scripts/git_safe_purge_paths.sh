#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/git_safe_purge_paths.sh <path1> [path2 ...]"
  echo "Example: scripts/git_safe_purge_paths.sh screenshot.png test_output.txt"
  exit 1
fi

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "Error: git-filter-repo is required for safe history rewrite."
  echo "Install: brew install git-filter-repo"
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Error: working tree is not clean. Commit or stash changes first."
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

current_branch="$(git rev-parse --abbrev-ref HEAD)"
timestamp="$(date +%Y%m%d_%H%M%S)"
backup_dir="backups/git-history"
backup_bundle="${backup_dir}/pre_rewrite_${timestamp}.bundle"
backup_tag="safety/pre-rewrite-${timestamp}"

mkdir -p "$backup_dir"

echo "[1/4] Creating full backup bundle at ${backup_bundle}"
git bundle create "$backup_bundle" --all

echo "[2/4] Creating safety tag ${backup_tag}"
git tag "$backup_tag" HEAD

cmd=(git filter-repo --force --refs "refs/heads/${current_branch}" --invert-paths)
for p in "$@"; do
  cmd+=(--path "$p")
done

echo "[3/4] Rewriting only current branch: ${current_branch}"
"${cmd[@]}"

echo "[4/4] Verifying removed paths in rewritten branch"
remaining="$(git rev-list "refs/heads/${current_branch}" -- "$@" | head -n 1 || true)"
if [[ -n "$remaining" ]]; then
  echo "Warning: at least one path still appears in branch history. Inspect manually."
else
  echo "OK: specified paths are not present in current branch history."
fi

echo "Done."
echo "Backup bundle: ${backup_bundle}"
echo "Safety tag: ${backup_tag}"
echo "If this rewrite needs to be shared: git push --force-with-lease origin ${current_branch}"
echo "Avoid running reflog/gc cleanup until the team confirms migration."
