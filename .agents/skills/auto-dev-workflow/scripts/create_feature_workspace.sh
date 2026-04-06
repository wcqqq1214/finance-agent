#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF' >&2
Usage: $0 --kind feat|fix --slug <normalized-topic>

Creates a feature/fix branch in .worktrees/ from wcq, ensuring a clean state.
Outputs BRANCH_NAME, WORKTREE_DIRNAME, WORKTREE_PATH, and BASE_SHA.
EOF
  exit 1
}

fatal() {
  echo "$1" >&2
  exit 1
}

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    fatal "Missing value for $flag"
  fi
}

ensure_clean_wc() {
  if [[ -n "$(git status --porcelain)" ]]; then
    fatal "Workspace contains uncommitted changes; clean before creating a worktree."
  fi
}

ensure_on_wcq() {
  local current
  current=$(git symbolic-ref --short HEAD)
  if [[ "$current" != "wcq" ]]; then
    fatal "Expected to be on wcq, but currently on $current."
  fi
}

normalize_slug() {
  local raw normalized
  raw="$1"
  normalized=$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')
  normalized=$(printf '%s' "$normalized" | sed 's/[^a-z0-9-]/-/g')
  normalized=$(printf '%s' "$normalized" | tr -s '-')
  normalized=${normalized##-}
  normalized=${normalized%%-}
  normalized=${normalized:0:40}
  if [[ -z "$normalized" ]]; then
    fatal 'Slug must include at least one alphanumeric character (after normalization).'
  fi
  printf '%s' "$normalized"
}

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

kind=""
slug=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --kind)
      require_value "$1" "${2:-}"
      kind="$2"
      shift 2
      ;;
    --slug)
      require_value "$1" "${2:-}"
      slug="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      fatal "Unknown argument: $1"
      ;;
  esac
done

if [[ -z "$kind" || -z "$slug" ]]; then
  usage
fi

if [[ "$kind" != "feat" && "$kind" != "fix" ]]; then
  fatal "--kind must be feat or fix (got '$kind')."
fi

ensure_clean_wc
ensure_on_wcq

base_sha=$(git rev-parse wcq)
normalized_slug=$(normalize_slug "$slug")
date_stamp=$(date +%Y%m%d)
base_branch_name="$kind/$date_stamp-$normalized_slug"
branch_name="$base_branch_name"
worktree_dirname=${branch_name//\//-}
worktrees_root="$repo_root/.worktrees"
mkdir -p "$worktrees_root"
worktree_path="$worktrees_root/$worktree_dirname"
suffix=2

while git show-ref --verify --quiet "refs/heads/$branch_name" || [[ -e "$worktree_path" ]]; do
  branch_name="$base_branch_name-$suffix"
  worktree_dirname=${branch_name//\//-}
  worktree_path="$worktrees_root/$worktree_dirname"
  suffix=$((suffix + 1))
done

git worktree add -b "$branch_name" "$worktree_path" wcq

printf 'BRANCH_NAME=%s\n' "$branch_name"
printf 'WORKTREE_DIRNAME=%s\n' "$worktree_dirname"
printf 'WORKTREE_PATH=%s\n' "$worktree_path"
printf 'BASE_SHA=%s\n' "$base_sha"
