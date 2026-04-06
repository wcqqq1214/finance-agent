# Verification Matrix

## Task-Level Scoped Checks (`scripts/run_scoped_checks.sh`)
- Inputs: `--base-sha <BASE_SHA>`, `--diff-target cached|worktree`, repeated `--cmd '<verification-command>'`.
- Determine touched paths from `git diff` versus base. Always run the caller's `--cmd` commands alongside deterministic flows below.

### Path-driven checks
- **Backend (non-`frontend/`) Python paths:** run `uv run ruff check <paths>` and `uv run ruff format --check <paths>`.
- **Frontend files under `frontend/`:**
  - `(cd frontend && pnpm lint)`
  - `(cd frontend && pnpm exec prettier --check .)`
  - `(cd frontend && pnpm type-check)` when `.ts`, `.tsx`, `package.json`, `tsconfig`, or ESLint/Prettier config files change.
- The script avoids rerunning the full suites when only a subset of files changes but always enforces linting/formatting for the affected scope.

## Final Gate (`scripts/run_final_gate.sh --base-sha <BASE_SHA>`)
- Derive touched files with `git diff --name-only <BASE_SHA>..HEAD`.
- **Backend gate (always):**
  - `uv run pytest tests/`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
- **Frontend gate (when `frontend/` touched):**
  - `cd frontend && pnpm lint`
  - `cd frontend && pnpm exec prettier --check .`
  - `cd frontend && pnpm type-check`
- Run every command sequentially; stop on the first failure and report the command that failed.

## ESLint & Prettier
- `pnpm lint`, `pnpm exec prettier --check .`, and `pnpm type-check` run from the `frontend` directory whenever frontend files change in either the task-level scoped checks or final gate.
- The workflow treats frontend CLI commands as the canonical enforcement mechanism—no alternative tooling is introduced in v1.
