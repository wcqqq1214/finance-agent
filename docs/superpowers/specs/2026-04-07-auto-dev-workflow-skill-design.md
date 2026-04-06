---
title: Auto Dev Workflow Skill Task C Design
date: 2026-04-07
---

# Auto Dev Workflow Skill – Task C

## Overview

This skill captures the repository-local automation expectations for Task C of the auto-dev-workflow initiative. It defines three guardrail scripts under `.agents/skills/auto-dev-workflow/scripts/` that isolate feature work, rerun verification, and gate merges. All scripts run with `set -euo pipefail`, emit clear reasoning on success/failure, and are safe to execute from the repository root. This design document specifies the responsibilities, interfaces, and failure modes so that the subsequent implementation can be validated against a single source of truth.

## Scripts

### `run_scoped_checks.sh`

- **Purpose**: Derive affected files from either the cached index or a lightweight worktree diff and gate command execution, Ruff, and frontend tooling to that subset.
- **Arguments**:
  - `--base-sha <sha>` designates the baseline commit for diffing.
  - `--diff-target <cached|worktree>` selects whether to compare the staged index (`cached`) or the working tree against the base.
  - Repeated `--cmd <verification-command>` options specify additional commands to run in order; they execute in the order they were provided.
- **Behavior**:
  1. Run `git diff --name-only --diff-filter=ACMRTUXB <base> --` or `git diff --name-only --cached --diff-filter=ACMRTUXB <base> --` depending on `--diff-target` to collect touched paths.
  2. Partition touched files into:
     - Python paths (`*.py`, `*.pyi`) to trigger two Ruff commands scoped to the changed files.
     - Frontend paths (any under `frontend/`) and configuration files that matter to frontend tooling.
     - Files that match `*.ts`, `*.tsx`, `frontend/package.json`, `tsconfig*.json`, `eslint*.{cjs,mjs,json}`, or `.prettierrc*` to determine whether the TypeScript gate is needed.
  3. Run the provided `--cmd` arguments after the diff classification.
  4. Always execute `uv run ruff check` and `uv run ruff format --check` with `--select-files` or equivalent to limit to the staged/working files gathered in step 1 (or the entire repo if the list is empty).
  5. If frontend paths were touched, run `cd frontend && pnpm lint` and `cd frontend && pnpm exec prettier --check .`.
  6. If any TypeScript or config file changed, additionally run `cd frontend && pnpm type-check`.
  7. Emit a summary mapping which subset triggered which command so downstream automation can inspect the exit code and the list of files it acted upon.

### `complete_task_commit.sh`

- **Purpose**: Ensure every task commit is made from a clean index and rerun specified verification commands before the commit is created.
- **Arguments**:
  - `--message <conventional-commit>` (mandatory) supplies the commit message body; the script should prepend `feat(wf):` or another agreed prefix if it’s not already there.
  - Repeated `--cmd <verification-command>` arguments define commands to rerun before creating the commit.
- **Behavior**:
  1. Refuse to run if `git diff --cached --name-only` is empty.
  2. Refuse to run if `git status --porcelain` reports any unstaged changes.
  3. Execute the provided `--cmd` entries in order (the same commands the caller intends to rely on). Any failure aborts before committing.
  4. If all commands succeed, perform `git commit -m "<message>"`.
  5. Print which commands were rerun and the final commit hash for verification.

### `run_final_gate.sh`

- **Purpose**: Provide the final safety net before merging a feature branch back into `wcq`.
- **Arguments**:
  - `--base-sha <sha>` points to the deterministic base commit that the feature branch was forked from.
- **Behavior**:
  1. Verify that `<base-sha>` exists in the current history (e.g., `git merge-base --is-ancestor`), aborting if it is not an ancestor of `HEAD`.
  2. Run the backend gate commands:
     - `uv run pytest tests/`
     - `uv run ruff check .`
     - `uv run ruff format --check .`
  3. Determine if frontend files were touched by running `git diff --name-only <base-sha> HEAD` and checking for any entries under `frontend/`.
  4. If frontend files changed, run:
     - `cd frontend && pnpm lint`
     - `cd frontend && pnpm exec prettier --check .`
     - `cd frontend && pnpm type-check`
  5. Output a machine-readable summary (e.g., JSON or key=value pairs) that states which gate succeeded and whether the frontend gate executed.

## Diff detection and classification

All scripts will centralize diff collection so that other logic can reuse the same list of touched files. The diff pipeline will:
1. Use the supplied `--base-sha` as the left-hand side of every comparison.
2. Respect `--diff-target`: when `worktree` is provided, compare `HEAD` and the working tree; when `cached` is supplied, compare `HEAD` and the staged index.
3. Normalize file paths and ignore deletions to keep the touched-file set readable.
4. Provide helper functions (e.g., `run_scoped_checks` might export `touched_python`, `touched_frontend`, `touched_ts_config`) so downstream rules can decide whether to run additional commands.

## Command reruns and user-provided `--cmd`

The `--cmd` arguments exist so a caller (root AGENT or sub-agent) can ensure a task’s intended verification commands run inside the workflow. Scripts must:
- Echo each command before running it.
- Run them exactly in the order provided.
- Fail fast if any command fails, without masking the earlier exit code.
- Provide exit-status-aware logging so callers can tell whether `pnpm lint` ran because a frontend file was touched or because the command was explicitly supplied.

## Error handling

- Every script sets `set -euo pipefail` and traps `ERR` to emit contextual failure messages.
- When refusing to run (e.g., clean index violation), print a clear rationale and choose a non-zero exit code (1 for guardrail failures, 2 for git state issues).
- When `--base-sha` is missing from history, fail early rather than proceeding with stale data.
- When `--cmd` reruns fail, propagate the command’s exit code rather than masking it.

## Testing and verification

- Unit-test the diff classification logic by mocking `git diff` outputs (e.g., ensure frontend detection turns on for `frontend/src/app` changes and `package.json` modifications).
- Smoke-test each script locally:
  1. Create a temporary branch/worktree and stage simple changes.
 2. Run `run_scoped_checks.sh` with `--diff-target cached` and verify only touched files are reported and the correct frontend/ruff commands run.
  3. Run `complete_task_commit.sh` with a staged change and a failing `--cmd` to confirm it refuses to commit.
  4. Run `run_final_gate.sh` with `--base-sha` pointing at `wcq` and a dummy frontend change to ensure frontend gates run.
- Validate that `pnpm lint`, `pnpm exec prettier --check .`, and `pnpm type-check` run from within `frontend/` only when triggered.

## Activation and escape rules

- These scripts live under `.agents/skills/auto-dev-workflow/scripts/` and are invoked via the `auto-dev-workflow` skill articulated in the root `AGENTS.md`.
- The design assumes the caller uses the `wcq` branch (or another feature branch) and that every new feature is developed in its own worktree, with merges gated via `run_final_gate.sh`.
- Avoid running these scripts from dirty repositories; each script already enforces clean-tree requirements before proceeding.

## Next steps

- After this design document is reviewed and considered stable, we will:
  1. Dispatch the spec-document-reviewer subagent (if available) to validate the text.
  2. Ask the user to review the committed spec before proceeding.
  3. Use the `writing-plans` skill to turn this spec into an executable plan for script implementation.
