#!/usr/bin/env bash
set -euo pipefail

script_name=$(basename "$0")

usage() {
  cat <<EOF >&2
Usage: $script_name --message "<conventional commit>" [--cmd "<command>"]...

Options:
  --message "<commit message>"  Conventional commit message (required)
  --cmd "<command>"             Verification command to rerun before commit (repeatable)
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

run_shell_cmd() {
  local cmd="$1"
  echo "+ $cmd"
  bash -c "$cmd"
}

ensure_no_unstaged_changes() {
  if ! git diff --quiet --ignore-submodules --; then
    fatal "Unstaged changes present; stage or discard them before committing."
  fi

  if [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
    fatal "Untracked files present; add or remove them before committing."
  fi
}

ensure_staged_diff() {
  if git diff --cached --quiet --ignore-submodules --; then
    fatal "No staged changes to commit."
  fi
}

message=""
declare -a user_cmds=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --message)
      require_value "$1" "${2:-}"
      message="${2:-}"
      shift 2
      ;;
    --cmd)
      require_value "$1" "${2:-}"
      user_cmds+=("${2:-}")
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

[[ -n "$message" ]] || fatal "Missing --message"
printf '%s\n' "$message" | grep -Eq '^[a-z]+(\([^)]+\))?(!)?: .+' || fatal "Commit message must use conventional commit format."

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

ensure_staged_diff
ensure_no_unstaged_changes

for cmd in "${user_cmds[@]}"; do
  run_shell_cmd "$cmd"
done

ensure_staged_diff
ensure_no_unstaged_changes

git commit -m "$message"

printf 'COMMIT_SHA=%s\n' "$(git rev-parse HEAD)"
