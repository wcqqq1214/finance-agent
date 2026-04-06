# Auto Dev Workflow Skill Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repository-local workflow skill that forces isolated feature work in a worktree/branch, auto-commits each task, and locally squash-merges back into `wcq` after backend and frontend checks pass.

**Architecture:** Build a thin orchestration skill that is explicitly invoked by root `AGENTS.md`, not by ambiguous skill auto-discovery alone. Keep the workflow logic in one entrypoint skill, put policy in references, and delegate deterministic enforcement to shell scripts for workspace creation, scoped checks, task commits, and final merge gates.

**Tech Stack:** Repository-local Codex skill files, Bash, Git worktrees, Python/uv, pnpm, Ruff, ESLint, Prettier

---

## Chunk 1: Skill Skeleton and Repo Wiring

### Task 1: Create the repository-local skill scaffold

**Files:**
- Create: `.agents/skills/auto-dev-workflow/SKILL.md`
- Create: `.agents/skills/auto-dev-workflow/agents/openai.yaml`
- Create: `.agents/skills/auto-dev-workflow/references/workflow-contract.md`
- Create: `.agents/skills/auto-dev-workflow/references/verification-matrix.md`
- Create: `.agents/skills/auto-dev-workflow/references/gstack-adapter.md`

- [ ] **Step 1: Initialize the skill directory with the skill creator script**

Run: `uv run python /home/wcqqq21/.codex/skills/.system/skill-creator/scripts/init_skill.py auto-dev-workflow --path .agents/skills --resources scripts,references --interface display_name="Auto Dev Workflow" --interface short_description="Repository workflow for isolated feature development with task commits and local squash merge" --interface default_prompt="Use this workflow for feature work unless skip-workflow is present."`
Expected: The `auto-dev-workflow` skill folder exists with the required template files.

- [ ] **Step 2: Validate the generated scaffold exists and is the only new skill directory**

Run: `find .agents/skills/auto-dev-workflow -maxdepth 3 -type f | sort`
Expected: Template files and resource directories are present.

- [ ] **Step 3: Write the skill metadata and policy references**

Add content that encodes:
- root-`AGENTS.md`-driven activation for development work
- `skip-workflow` escape hatch
- `wcq` clean-workspace preflight
- local-only squash merge behavior
- backend + frontend verification matrix including `eslint` and `prettier`
- script interfaces and blocking/advisory review rules
- required use of `test-driven-development` and `systematic-debugging`

- [ ] **Step 4: Run skill validation**

Run: `uv run python /home/wcqqq21/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/auto-dev-workflow`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/auto-dev-workflow
git commit -m "feat(skill): add auto dev workflow scaffold"
```

### Task 2: Wire the repository to the new workflow skill

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Add a repository rule pointing development work to the local workflow skill**

Update the repository instructions so feature and bugfix work uses the local `auto-dev-workflow` skill by default unless `skip-workflow` is present.

- [ ] **Step 2: Verify the rule is concise and does not contradict existing Superpowers guidance**

Run: `rg -n "auto-dev-workflow|skip-workflow|worktree" AGENTS.md`
Expected: The new rule is present and consistent with the root workflow section.

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs(agents): route development work through auto workflow skill"
```

## Chunk 2: Deterministic Workflow Scripts

### Task 3: Implement workspace creation and final merge scripts

**Files:**
- Create: `.agents/skills/auto-dev-workflow/scripts/create_feature_workspace.sh`
- Create: `.agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh`

- [ ] **Step 1: Write failing script smoke tests or command-level reproductions**

Document and manually verify:
- dirty workspace refusal
- non-`wcq` branch refusal
- successful worktree creation under `.worktrees/`
- refusal to merge when `wcq` drifts

- [ ] **Step 2: Implement `create_feature_workspace.sh`**

Required behavior:
- refuse dirty workspace
- refuse branch other than `wcq`
- capture base SHA
- create `feat/<yyyymmdd>-<slug>` or `fix/<yyyymmdd>-<slug>` branch inside `.worktrees/`
- map branch names to worktree dir names by replacing `/` with `-`
- append `-2`, `-3`, ... on collisions
- print machine-readable outputs for downstream steps

- [ ] **Step 3: Implement `squash_merge_to_wcq.sh`**

Required behavior:
- compare current local `wcq` HEAD with recorded base SHA
- abort on drift
- squash merge feature branch into local `wcq`
- call the fixed `run_final_gate.sh --base-sha <base_sha>` script
- delete feature branch and remove worktree on success

- [ ] **Step 4: Verify the scripts on the current repo**

Run representative dry/safe invocations using temporary branch slugs.
Expected: worktree creation succeeds from clean `wcq`; merge script refuses unsafe states.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/auto-dev-workflow/scripts/create_feature_workspace.sh .agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh
git commit -m "feat(skill): add workspace and merge workflow scripts"
```

### Task 4: Implement scoped check and task-commit scripts

**Files:**
- Create: `.agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh`
- Create: `.agents/skills/auto-dev-workflow/scripts/complete_task_commit.sh`
- Create: `.agents/skills/auto-dev-workflow/scripts/run_final_gate.sh`

- [ ] **Step 1: Write command-level failing cases**

Verify intended failures for:
- no staged diff in task commit script
- unstaged changes present during task commit
- unsupported path set in scoped checks
- frontend-touched changes without frontend tooling checks in final gate

- [ ] **Step 2: Implement `run_scoped_checks.sh`**

Required behavior:
- accept repeated explicit `--cmd` verification commands from the plan task
- derive changed paths from git diff against a caller-provided base/target
- run backend lint/format checks for Python changes
- run frontend checks for `frontend/` changes
- include `pnpm exec prettier --check .` for frontend path sets
- run `pnpm type-check` when TS/config/tooling files affecting frontend typing changed

- [ ] **Step 3: Implement `complete_task_commit.sh`**

Required behavior:
- refuse empty staged state
- refuse unstaged changes
- require a task label / commit message input
- rerun the provided verification commands immediately before commit
- create a conventional commit after successful checks

- [ ] **Step 4: Implement `run_final_gate.sh`**

Required behavior:
- take `--base-sha <sha>`
- run `uv run pytest tests/`
- run `uv run ruff check .`
- run `uv run ruff format --check .`
- internally derive whether `frontend/` changed from `git diff --name-only <base_sha>..HEAD`
- when `frontend/` changed, run:
  - `pnpm lint`
  - `pnpm exec prettier --check .`
  - `pnpm type-check`

- [ ] **Step 5: Verify the scripts**

Run the scripts against representative Python-only and frontend-touched path sets.
Expected: Correct command selection and clear failures when commands fail.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh .agents/skills/auto-dev-workflow/scripts/complete_task_commit.sh .agents/skills/auto-dev-workflow/scripts/run_final_gate.sh
git commit -m "feat(skill): add verification and task commit scripts"
```

## Chunk 3: Workflow Orchestration and Validation

### Task 5: Finish SKILL.md orchestration against the new scripts

**Files:**
- Modify: `.agents/skills/auto-dev-workflow/SKILL.md`
- Modify: `.agents/skills/auto-dev-workflow/references/workflow-contract.md`
- Modify: `.agents/skills/auto-dev-workflow/references/verification-matrix.md`
- Modify: `.agents/skills/auto-dev-workflow/references/gstack-adapter.md`

- [ ] **Step 1: Update the entrypoint skill to reference the concrete scripts**

The skill must explicitly tell the agent:
- when to trigger
- when to stop
- that docs/spec/plan are written inside the feature worktree after workspace setup
- which script to call for each deterministic phase
- which Superpowers skills remain required
- that bugfixes must use `systematic-debugging` before code changes
- that implementation tasks must use `test-driven-development`

- [ ] **Step 2: Keep the skill concise**

Run: `wc -w .agents/skills/auto-dev-workflow/SKILL.md`
Expected: concise body with details pushed into references/scripts rather than duplicated.

- [ ] **Step 3: Re-run skill validation**

Run: `uv run python /home/wcqqq21/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/auto-dev-workflow`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add .agents/skills/auto-dev-workflow
git commit -m "feat(skill): finalize auto workflow orchestration"
```

### Task 6: Validate the workflow end-to-end at a smoke-test level

**Files:**
- Test: `.agents/skills/auto-dev-workflow/scripts/create_feature_workspace.sh`
- Test: `.agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh`
- Test: `.agents/skills/auto-dev-workflow/scripts/complete_task_commit.sh`
- Test: `.agents/skills/auto-dev-workflow/scripts/run_final_gate.sh`
- Test: `.agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh`

- [ ] **Step 1: Run skill validation one final time**

Run: `uv run python /home/wcqqq21/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/auto-dev-workflow`
Expected: PASS

- [ ] **Step 2: Run smoke checks for the scripts**

Execute safe representative commands to prove:
- clean `wcq` can create a feature worktree
- task commit script refuses empty staged diff
- final gate selects backend checks and frontend checks including `eslint` and `prettier`
- merge script refuses drifted `wcq`

- [ ] **Step 3: Review resulting diff for intended scope**

Run: `git diff -- .agents/skills/auto-dev-workflow AGENTS.md docs/superpowers/specs/2026-04-07-auto-dev-workflow-skill-design.md docs/superpowers/plans/2026-04-07-auto-dev-workflow-skill.md`
Expected: Only workflow skill, docs, and repo wiring changes are present.

- [ ] **Step 4: Commit documentation artifacts**

```bash
git add docs/superpowers/specs/2026-04-07-auto-dev-workflow-skill-design.md docs/superpowers/plans/2026-04-07-auto-dev-workflow-skill.md
git commit -m "docs(skill): add workflow design and implementation plan"
```
