# Auto Dev Workflow Skill Design

**Problem**

The repository already documents a preferred Superpowers workflow, but it does not enforce the operational constraints the team actually wants during day-to-day development. New feature work can still start from the main workspace, task boundaries are not consistently committed, and successful work is not automatically folded back into the local `wcq` branch. The workflow also does not yet encode frontend lint/format gates such as `eslint` and `prettier`.

**Goal**

Create a repository-local workflow skill that takes over feature and bugfix implementation work through explicit repository instructions, forces execution inside an isolated `worktree + branch`, commits after each small task, and automatically `squash merge`s back into local `wcq` after all checks pass.

**Design**

## Scope

- Add a repository-local skill under `.agents/skills/auto-dev-workflow/`.
- Make the skill the default workflow for development requests through root `AGENTS.md` rules unless the user explicitly says `skip-workflow`.
- Reuse the existing Superpowers phases (`brainstorming`, `writing-plans`, `using-git-worktrees`, `subagent-driven-development`, `requesting-code-review`, `verification-before-completion`) instead of re-implementing them in prose.
- Require `test-driven-development` for implementation work and `systematic-debugging` before bugfix implementation.
- Add deterministic shell scripts for the parts that must be enforced rather than merely suggested:
  - worktree/branch creation
  - task-level commit creation
  - scoped checks
  - final gate
  - local squash merge back to `wcq`
- Extend the final verification matrix to include frontend `eslint` and `prettier`.

## Non-Goals

- Do not add automatic remote pushes.
- Do not support direct development on `wcq` or `master`.
- Do not introduce a second first-class runtime for `gstack` in v1; only document a future adapter seam.
- Do not modify the existing global Superpowers skills in `node_modules`.

## Activation Model

The repository cannot rely on one ambiguous auto-discovery path. v1 uses a two-part activation model:

1. The canonical implementation lives in the repository at `.agents/skills/auto-dev-workflow/`.
2. Root `AGENTS.md` explicitly instructs agents to read and follow that skill for implementation requests unless the user says `skip-workflow`.

`agents/openai.yaml` remains useful for UIs that surface repository-local skills, but correct behavior must not depend on UI-specific auto-loading.

## User-Facing Behavior

1. When the user asks for a new feature, bugfix, or behavior change, the workflow skill activates automatically.
2. The skill does not activate for code questions, code review requests, brainstorming-only requests, or explicit planning requests that do not ask for implementation.
3. If the user says `skip-workflow`, the skill exits immediately and normal handling resumes.
4. The skill refuses to start if the main workspace is not on `wcq` or if the main workspace has uncommitted changes.
5. After preflight, the skill creates a dedicated `.worktrees/<branch-name>` worktree and a matching feature branch from the current `wcq` commit.
6. The workflow writes the approved design and implementation plan inside that feature worktree under `docs/superpowers/specs/` and `docs/superpowers/plans/`, so the docs and implementation live on the same branch.
7. During implementation, every completed plan task is verified and then committed automatically on the feature branch.
8. After the final gate passes, the feature branch is squash-merged into local `wcq`, then the feature branch and worktree are removed.
9. If any task review, verification step, branch drift check, or merge step fails, the workflow stops and reports the blocking condition instead of guessing.

## Triggering and Escape Hatch

- Skill name: `auto-dev-workflow`
- Trigger classes:
  - feature implementation
  - bugfix implementation
  - behavior-changing code change
  - new script/tooling implementation
- Explicit non-triggers:
  - architecture discussion only
  - code explanation only
  - code review only
  - repository exploration only
- Escape hatch:
  - exact phrase `skip-workflow`
- Precedence:
  - explicit user request to skip wins
  - otherwise root `AGENTS.md` routes implementation work through the local skill

## Repository Layout

```text
.agents/
  skills/
    auto-dev-workflow/
      SKILL.md
      agents/
        openai.yaml
      references/
        workflow-contract.md
        verification-matrix.md
        gstack-adapter.md
      scripts/
        create_feature_workspace.sh
        complete_task_commit.sh
        run_scoped_checks.sh
        run_final_gate.sh
        squash_merge_to_wcq.sh
```

### File Responsibilities

- `SKILL.md`
  - entrypoint and orchestration rules
  - trigger description
  - stop conditions
  - required sub-skills
- `agents/openai.yaml`
  - UI metadata only
- `references/workflow-contract.md`
  - branch policy
  - worktree policy
  - merge/cleanup policy
  - `skip-workflow` behavior
- `references/verification-matrix.md`
  - task-level scoped checks
  - final gate commands
  - backend and frontend command matrix
- `references/gstack-adapter.md`
  - future mapping notes only
- `scripts/create_feature_workspace.sh`
  - validate clean `wcq`
  - derive feature branch name
  - create worktree + branch
  - print resulting paths/branch names and base SHA
- `scripts/complete_task_commit.sh`
  - validate staged diff exists
  - refuse unstaged changes
  - rerun required task-level commands passed in by caller
  - create conventional commit for the finished task
- `scripts/run_scoped_checks.sh`
  - choose backend/frontend lint-format commands from changed paths
  - run caller-provided task verification commands
  - run backend and frontend subsets without over-running the full suite
- `scripts/run_final_gate.sh`
  - run final backend and frontend checks
  - include `ruff`, `eslint`, `prettier`, type-check, and target test suite commands
- `scripts/squash_merge_to_wcq.sh`
  - confirm `wcq` has not advanced since branch creation
  - squash merge
  - rerun final gate on merged `wcq`
  - delete feature branch
  - remove worktree

## Workflow State Machine

1. `preflight`
   - confirm current workspace is root repo
   - confirm current branch is `wcq`
   - confirm working tree is clean
   - capture local `refs/heads/wcq` SHA
2. `workspace setup`
   - run `create_feature_workspace.sh`
3. `design`
   - switch work to the feature worktree
   - run `brainstorming`
   - write spec in the feature worktree
   - run spec review loop
4. `planning`
   - run `writing-plans`
   - write plan in the feature worktree
   - run plan review loop
5. `task execution loop`
   - execute one planned task at a time
   - for bugfix tasks, complete `systematic-debugging` before code changes
   - use `test-driven-development` before production code changes
   - run scoped checks
   - request spec compliance review
   - request code quality review
   - run `complete_task_commit.sh`
6. `final gate`
   - run `run_final_gate.sh`
7. `merge`
   - run `squash_merge_to_wcq.sh`
8. `cleanup`
   - branch/worktree cleanup is part of successful merge

## Verification Matrix

### Task-Level Scoped Checks

`run_scoped_checks.sh` receives:

- a diff base SHA
- the current git target (`--cached` or worktree diff)
- zero or more explicit task verification commands from the plan

The script then adds deterministic path-based checks:

- Python path touched outside `frontend/`:
  - `uv run ruff check <python-paths>`
  - `uv run ruff format --check <python-paths>`
- Frontend path touched under `frontend/`:
  - `(cd frontend && pnpm lint)`
  - `(cd frontend && pnpm exec prettier --check .)`
  - `(cd frontend && pnpm type-check)` when any `.ts`, `.tsx`, `package.json`, `tsconfig`, or ESLint/Prettier config file changes

The caller-supplied task verification commands remain the source of truth for task-specific tests. v1 does not attempt to infer pytest targets from source files alone.

### Final Gate

- Backend:
  - `uv run pytest tests/`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
- Frontend, when `frontend/` is touched:
  - `(cd frontend && pnpm lint)`
  - `(cd frontend && pnpm exec prettier --check .)`
  - `(cd frontend && pnpm type-check)`

Frontend semantics still come from `frontend/AGENTS.md`; the workflow only enforces the existing command-line gates.

## Commit Strategy

- During execution:
  - one commit per completed plan task
  - conventional commits
  - these commits exist only on the feature branch and are validated there before squash
- At integration:
  - squash merge into local `wcq`
  - one final feature commit on `wcq`

## Error Handling and Stop Conditions

The workflow must stop and report instead of improvising when:

- main workspace is dirty
- current branch is not `wcq`
- worktree creation fails
- scoped checks fail
- any spec review or code review reports blocking issues
- final gate fails
- `wcq` advanced after the feature branch was created
- squash merge conflicts

## Testing Strategy

- Script-level smoke tests for:
  - refusing dirty workspace
  - creating worktree and branch from `wcq`
  - refusing merge when `wcq` drifts
- Skill validation:
  - `quick_validate.py` against the skill directory
- Forward checks:
  - use subagents against the local skill to verify the workflow instructions are discoverable and coherent

## Risks

- Auto-trigger descriptions that are too broad may catch non-implementation requests.
- Scoped frontend checks can overrun into full-project checks if CLI support is inconsistent.
- Auto-merge must remain local-only to avoid surprising remote side effects.
- The workflow depends on clear task boundaries in generated plans; weak plans will weaken task-level auto-commit quality.

## Naming Rules

- Branch naming:
  - `feat/<yyyymmdd>-<slug>`
  - `fix/<yyyymmdd>-<slug>`
- Worktree directory naming:
  - replace `/` with `-` from the branch name
  - example: `feat/20260407-auto-workflow` maps to `.worktrees/feat-20260407-auto-workflow`
- Slug rules:
  - lowercase ASCII
  - hyphen-separated
  - max 40 characters after normalization
- Collision handling:
  - append `-2`, `-3`, ... until both the branch name and `.worktrees/<name>` path are free

## Script Interfaces

### `create_feature_workspace.sh`

Inputs:
- `--kind feat|fix`
- `--slug <normalized-topic>`

Outputs:
- stdout lines:
  - `BRANCH_NAME=...`
  - `WORKTREE_DIRNAME=...`
  - `WORKTREE_PATH=...`
  - `BASE_SHA=...`
- exit `0` on success, non-zero on refusal/error

### `run_scoped_checks.sh`

Inputs:
- `--base-sha <sha>`
- `--diff-target cached|worktree`
- repeated `--cmd '<verification-command>'`

Behavior:
- derives changed paths from git diff against the provided target
- runs added lint/format/type commands from path rules
- runs each provided `--cmd` as part of the scoped gate

### `complete_task_commit.sh`

Inputs:
- `--message <conventional-commit-message>`
- repeated `--cmd '<verification-command>'`

Behavior:
- refuses empty staged diff
- reruns the provided verification commands before committing, removing ambiguity about whether checks already passed

### `run_final_gate.sh`

Inputs:
- `--base-sha <sha>`

Behavior:
- runs full backend gate
- derives frontend impact internally from `git diff --name-only <base_sha>..HEAD`
- runs frontend `eslint`, `prettier`, and `type-check` only when frontend content changed in that diff

### `squash_merge_to_wcq.sh`

Inputs:
- `--branch <feature-branch>`
- `--base-sha <captured-wcq-sha>`
- `--worktree <path>`

Behavior:
- drift means local `git rev-parse wcq` no longer equals captured `base_sha`
- remotes are ignored in v1 because the workflow does not push
- runs the fixed `run_final_gate.sh --base-sha <base_sha>` script instead of evaluating a caller-provided command string

## Review Severity Rules

- Spec reviewer:
  - any `❌ Issues Found` item is blocking
- Code reviewer:
  - `Critical` and `Important` issues are blocking
  - `Minor` issues are advisory

## Development Discipline Rules

- All implementation tasks follow `test-driven-development`.
- All bugfix tasks complete `systematic-debugging` root-cause investigation before implementation starts.
- `complete_task_commit.sh` commits only when the staged diff is the full intended task result and no unstaged changes remain.

## Integration Points

- Modify `AGENTS.md` to route implementation work to the local workflow skill.
- Respect `frontend/AGENTS.md` as the canonical frontend behavior ruleset while using existing frontend CLI commands.
- Use the local validation helper at `/home/wcqqq21/.codex/skills/.system/skill-creator/scripts/quick_validate.py` during implementation verification.

## Acceptance Criteria

1. A new repository-local skill exists at `.agents/skills/auto-dev-workflow/`.
2. Development requests trigger the workflow by default, and `skip-workflow` bypasses it.
3. The workflow refuses to run from a dirty main workspace or from a branch other than `wcq`.
4. The workflow creates an isolated worktree and feature branch before implementation.
5. The workflow includes task-level auto-commit behavior.
6. The workflow includes final local squash merge back to `wcq`.
7. The workflow’s final gate includes backend `ruff` and frontend `eslint` plus `prettier`.
8. The skill folder passes basic validation with `quick_validate.py`.
