# Auto Dev Workflow Skill Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Task C by adding `run_scoped_checks.sh`, `complete_task_commit.sh`, and `run_final_gate.sh` so that feature work is isolated, rerun verification is enforced, and merges back to `wcq` are gated.

**Architecture:** Three focused Bash scripts use shared git diff logic to decide what checks to run, rerun verification commands with the caller-supplied context, and gate merges with frontend awareness.

**Tech Stack:** `bash`, `git`, `pnpm`, `uv`, `ruff`, `pytest`

---

## Chunk 1: run_scoped_checks.sh

### Task 1: Build the scoped-checks script that derives diffs, classifies files, and runs the appropriate commands

**Files:**
- Create: `/home/wcqqq21/q-agents/.agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh`

- [ ] **Step 1: Wire up the script skeleton**

```bash
#!/usr/bin/env bash
set -euo pipefail
declare base_sha=""
declare diff_target="cached"
declare -a user_cmds=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-sha) base_sha="$2"; shift 2;;
    --diff-target) diff_target="$2"; shift 2;;
    --cmd) user_cmds+=("$2"); shift 2;;
    *) echo "Unknown argument $1"; exit 1;;
  esac
done

[ -n "$base_sha" ] || { echo "require --base-sha"; exit 1; }
```

- [ ] **Step 2: Gather touched files for the requested diff target**
  - Call either `git diff --name-only --diff-filter=ACMRTUXB "$base_sha" --` or `git diff --name-only --cached --diff-filter=ACMRTUXB "$base_sha" --` depending on `diff_target`.
  - Normalize the output via `mapfile -t touched_files < <(git diff ... | sort -u)`.

- [ ] **Step 3: Classify the touched files**
  - Build arrays `touched_python`, `touched_frontend`, `touched_ts_config` based on glob matching (use `[[ $file == frontend/* ]]`, etc).
  - Use `case $file in *.py|*.pyi)` for Python, `frontend/*` for frontend, `frontend/package.json`, `tsconfig*.json`, `eslint*.{cjs,mjs,json}`, `.prettierrc*`, `*.ts|*.tsx` for the TypeScript/config gate.

- [ ] **Step 4: Execute user-provided `--cmd` entries after diffs are classified**
  - Iterate `for cmd in "${user_cmds[@]}"; do echo "run: $cmd"; eval "$cmd"; done`.
  - Preserve exit codes by allowing any failure to bubble up (no `|| true`).

- [ ] **Step 5: Run Ruff and frontend checks**
  - Invoke `uv run ruff check "${python_args[@]}"` where `python_args` is `touched_python` or `.` if empty plus `--diff <paths>`.
  - Similarly run `uv run ruff format --check`.
  - If `touched_frontend` is non-empty, execute:
    ```bash
    (cd frontend && pnpm lint)
    (cd frontend && pnpm exec prettier --check .)
    ```
  - If TypeScript/config files were touched, also run `(cd frontend && pnpm type-check)`.

- [ ] **Step 6: Emit a structured summary**
  - Print touched categories, commands executed, and whether frontend gate ran so callers can assert behavior.

**Test:** Run `./.agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh --base-sha wcq --diff-target cached --cmd "uv run pytest tests/test_placeholder.py"` against a worktree with staged Python and frontend changes and verify Ruff runs only on changed files and that the frontend gate fires.

## Chunk 2: complete_task_commit.sh

### Task 2: Add the guarded commit script that reruns verification before committing

**Files:**
- Create: `/home/wcqqq21/q-agents/.agents/skills/auto-dev-workflow/scripts/complete_task_commit.sh`

- [ ] **Step 1: Parse `--message` and repeated `--cmd`**
  - Use the same `while` loop pattern from Chunk 1 but require `--message`.
  - Collect `user_cmds` and strip leading/trailing whitespace from the message.

- [ ] **Step 2: Enforce clean index expectations**
  - Run `git diff --cached --name-only` and exit with error `1` if output is empty.
  - Run `git status --porcelain` and exit with error `2` if any line begins with `??` or ` M` (unstaged change).

- [ ] **Step 3: Rerun verification commands**
  - For each command in `user_cmds`, echo it and evaluate it exactly once before committing.
  - Use `$cmd` string and allow natural exit code propagation.

- [ ] **Step 4: Create the conventional commit**
  - If the message does not already start with `feat(wf):` / `fix(wf):` etc., prefix with `feat(wf):`.
  - Execute `git commit -m "$message"`.

- [ ] **Step 5: Print a summary and latest commit id**
  - After committing, echo `"Completed commit $(git rev-parse HEAD) via rerun of: ..."` so automation can log the outcome.

**Test:** Stage a Python change, run the script with `--message "feat(wf): add guard"` and a failing `--cmd "uv run ruff check nonexistent.py"`; ensure it aborts before committing, then rerun with a passing command to verify the commit happens.

## Chunk 3: run_final_gate.sh

### Task 3: Implement the final gate that ensures backend + conditional frontend checks before merge

**Files:**
- Create: `/home/wcqqq21/q-agents/.agents/skills/auto-dev-workflow/scripts/run_final_gate.sh`

- [ ] **Step 1: Parse `--base-sha` and validate ancestry**
  - Use argument parsing pattern from Chunk 1, require `--base-sha`.
  - Call `git merge-base --is-ancestor "$base_sha" HEAD` and exit with an error if the check fails.

- [ ] **Step 2: Always run backend gates**
  - Run `uv run pytest tests/`, `uv run ruff check .`, and `uv run ruff format --check .` sequentially, logging each command before invocation.
  - Fail fast on any error.
  - Capture that backend gate succeeded for the summary at the end.

- [ ] **Step 3: Detect frontend changes**
  - Execute `mapfile -t changed < <(git diff --name-only "$base_sha" HEAD -- frontend)` and treat a non-empty list as a frontend trigger.

- [ ] **Step 4: Run frontend gate when triggered**
  - If frontend files changed, run:
    ```bash
    (cd frontend && pnpm lint)
    (cd frontend && pnpm exec prettier --check .)
    (cd frontend && pnpm type-check)
    ```
  - Record in the output which subset ran so automation can verify.

- [ ] **Step 5: Emit final status**
  - Print `FINAL_GATE=backend,frontend` or `FINAL_GATE=backend-only` plus the exit status so callers know exactly what succeeded.

**Test:** Create a feature branch with `frontend/src/app/page.tsx` changed, run `run_final_gate.sh --base-sha <wcq-base>`, and confirm backend commands run plus the frontend lint/prettier/type-check steps.

## Plan review guidance

- After documenting each chunk above, the plan-reviewer subagent would normally be dispatched per chunk. If no reviewer is available (as in the current session), the plan author should double-check each section against the spec.
- Once the reviewer approves a chunk, proceed to the next chunk until all scripts are covered.

## Execution handoff

- Plan complete and saved to `docs/superpowers/plans/2026-04-07-auto-dev-workflow-skill.md`. Ready to execute under $subagent-driven-development (if available) or $executing-plans if not.
