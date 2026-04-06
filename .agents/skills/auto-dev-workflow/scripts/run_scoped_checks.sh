#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF >&2
Usage: $(basename "$0") --base-sha <sha> [--diff-target cached|worktree] [--cmd "<command>"]...

Options:
  --base-sha <sha>              Recorded feature-branch base SHA for workflow validation (required)
  --diff-target cached|worktree Inspect staged changes or the working tree. Default: cached
  --cmd "<command>"             Additional verification command to run (repeatable)
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

run_array_cmd() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  "$@"
}

run_shell_cmd() {
  local cmd="$1"
  printf '+ %s\n' "$cmd"
  bash -c "$cmd"
}

run_frontend_cmd() {
  local cmd="$1"
  printf '+ (cd frontend && %s)\n' "$cmd"
  (
    cd frontend
    bash -c "$cmd"
  )
}

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

base_sha=""
diff_target="cached"
declare -a user_cmds=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-sha)
      require_value "$1" "${2:-}"
      base_sha="${2:-}"
      shift 2
      ;;
    --diff-target)
      require_value "$1" "${2:-}"
      diff_target="${2:-}"
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

[[ -n "$base_sha" ]] || fatal "Missing --base-sha"
[[ "$diff_target" == "cached" || "$diff_target" == "worktree" ]] || fatal "--diff-target must be cached or worktree."
git rev-parse --verify "${base_sha}^{commit}" >/dev/null 2>&1 || fatal "Unknown base SHA: $base_sha"
git merge-base --is-ancestor "$base_sha" HEAD >/dev/null 2>&1 || fatal "Base SHA $base_sha is not an ancestor of HEAD."

declare -a touched_paths=()
if [[ "$diff_target" == "cached" ]]; then
  mapfile -t touched_paths < <(git diff --cached --name-only --diff-filter=ACMRTUXB "$base_sha" --)
else
  mapfile -t touched_paths < <(
    {
      git diff --name-only --diff-filter=ACMRTUXB "$base_sha" --
      git ls-files --others --exclude-standard
    } | awk 'NF && !seen[$0]++'
  )
fi

declare -a python_paths=()
frontend_touched=false
typecheck_needed=false

for path in "${touched_paths[@]}"; do
  [[ -n "$path" ]] || continue

  case "$path" in
    frontend/*)
      frontend_touched=true
      ;;
    *.py|*.pyi)
      python_paths+=("$path")
      ;;
  esac

  case "$path" in
    frontend/*.ts|frontend/*.tsx|frontend/**/*.ts|frontend/**/*.tsx|frontend/package.json|frontend/pnpm-lock.yaml|frontend/tsconfig*.json|frontend/next-env.d.ts|frontend/eslint.config.*|frontend/.eslintrc*|frontend/prettier.config.*|frontend/.prettierrc*)
      typecheck_needed=true
      ;;
  esac
done

if [[ ${#python_paths[@]} -gt 0 ]]; then
  echo "Running Ruff on ${#python_paths[@]} Python path(s)."
  run_array_cmd uv run ruff check "${python_paths[@]}"
  run_array_cmd uv run ruff format --check "${python_paths[@]}"
else
  echo "No backend Python paths changed; skipping Ruff path checks."
fi

for cmd in "${user_cmds[@]}"; do
  run_shell_cmd "$cmd"
done

if [[ "$frontend_touched" == true ]]; then
  echo "Frontend changes detected; running lint and Prettier."
  run_frontend_cmd "pnpm lint"
  run_frontend_cmd "pnpm exec prettier --check ."

  if [[ "$typecheck_needed" == true ]]; then
    run_frontend_cmd "pnpm type-check"
  else
    echo "Frontend type-check gate not triggered."
  fi
else
  echo "No frontend changes detected; skipping frontend gates."
fi

printf 'BASE_SHA=%s\n' "$base_sha"
printf 'DIFF_TARGET=%s\n' "$diff_target"
printf 'TOUCHED_FILES=%s\n' "${#touched_paths[@]}"
printf 'PYTHON_GUARD=%s\n' "$([[ ${#python_paths[@]} -gt 0 ]] && echo yes || echo no)"
printf 'FRONTEND_GUARD=%s\n' "$([[ "$frontend_touched" == true ]] && echo yes || echo no)"
printf 'TYPECHECK=%s\n' "$([[ "$typecheck_needed" == true ]] && echo yes || echo no)"
printf 'CMD_COUNT=%s\n' "${#user_cmds[@]}"
