# Replace Squash Merge Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the auto-dev workflow's final squash merge with validated fast-forward integration so `wcq` keeps the feature branch's task commits.

**Architecture:** Keep the current `wcq` drift guard and cleanup contract, but rename the integration script to `ff_merge_to_wcq.sh` and verify the feature branch tip in a detached temporary worktree before `git merge --ff-only` updates `wcq`. Update the workflow docs and script tests together so the new contract is enforced end to end.

**Tech Stack:** Bash, Git worktrees, pytest, repository-local skill docs

---

## Chunk 1: Script Contract and TDD

### Task 1: Replace the integration-script test contract

**Files:**
- Modify: `tests/scripts/test_auto_dev_workflow.py`

- [ ] **Step 1: Rewrite the existing squash-merge tests to describe fast-forward behavior**

Update the script tests so they target `ff_merge_to_wcq.sh` and assert:
- drifted base still fails
- non-worktree path still fails
- successful integration preserves the branch head commit on `wcq`
- diverged history fails with a fast-forward-specific error
- explicit merge-message behavior is removed

- [ ] **Step 2: Run the targeted script tests to verify RED**

Run: `uv run pytest tests/scripts/test_auto_dev_workflow.py -q`
Expected: FAIL because the repository still exposes squash-based behavior and references.

- [ ] **Step 3: Do not commit in the RED state**

Keep the failing test edits uncommitted until the implementation turns the task GREEN and the scoped checks pass.

### Task 2: Implement the fast-forward integration script

**Files:**
- Create: `.agents/skills/auto-dev-workflow/scripts/ff_merge_to_wcq.sh`
- Modify: `.agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh`

- [ ] **Step 1: Implement the new script and a compatibility stub with the minimal behavior required by the failing tests**

Required behavior:
- accept `--branch`, `--base-sha`, and `--worktree`
- refuse dirty `wcq`
- refuse dirty feature worktree
- refuse drifted `wcq`
- run the final gate in a temporary detached worktree at the feature branch tip
- fast-forward `wcq` with `git merge --ff-only`
- clean up the feature worktree and feature branch on success
- make `squash_merge_to_wcq.sh` fail immediately with a redirect to `ff_merge_to_wcq.sh`

- [ ] **Step 2: Run the targeted script tests to verify GREEN**

Run: `uv run pytest tests/scripts/test_auto_dev_workflow.py -q`
Expected: PASS

- [ ] **Step 3: Run scoped checks for the task**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh --base-sha 03583c4c93a77866e8bb626ba398f1a7386e5fe5 --diff-target cached --cmd 'uv run pytest tests/scripts/test_auto_dev_workflow.py -q'`
Expected: PASS

- [ ] **Step 4: Commit with the workflow helper**

```bash
git add .agents/skills/auto-dev-workflow/scripts/ff_merge_to_wcq.sh .agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh tests/scripts/test_auto_dev_workflow.py
bash .agents/skills/auto-dev-workflow/scripts/complete_task_commit.sh --message "feat(workflow): preserve task commits with fast-forward integration" --cmd "uv run pytest tests/scripts/test_auto_dev_workflow.py -q"
```

## Chunk 2: Workflow Documentation and Wiring

### Task 3: Update workflow references to the new integration contract

**Files:**
- Modify: `.agents/skills/auto-dev-workflow/SKILL.md`
- Modify: `.agents/skills/auto-dev-workflow/references/workflow-contract.md`
- Modify: `.agents/skills/auto-dev-workflow/references/claude-code-adapter.md`
- Modify: `.agents/skills/auto-dev-workflow/references/gstack-adapter.md`
- Modify: `.agents/skills/auto-dev-workflow/agents/openai.yaml`

- [ ] **Step 1: Replace squash wording and script names with fast-forward wording**

Update all repository-local workflow references so they consistently describe:
- preserved task commits on `wcq`
- `ff_merge_to_wcq.sh` as the integration script
- no `--message` option on the integration script
- drift as a hard stop rather than an implicit rebase

- [ ] **Step 2: Verify all in-repo references are updated**

Run: `rg -n "squash merge|local squash merge|--message" .agents/skills/auto-dev-workflow tests/scripts/test_auto_dev_workflow.py`
Expected: No stale squash-only workflow wording or `--message` references remain. `squash_merge_to_wcq.sh` may still appear only in the compatibility stub and its redirect test coverage.

- [ ] **Step 3: Run the targeted workflow tests again**

Run: `uv run pytest tests/scripts/test_auto_dev_workflow.py -q`
Expected: PASS

- [ ] **Step 4: Run scoped checks for the task**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh --base-sha 03583c4c93a77866e8bb626ba398f1a7386e5fe5 --diff-target cached --cmd 'uv run pytest tests/scripts/test_auto_dev_workflow.py -q'`
Expected: PASS

- [ ] **Step 5: Commit with the workflow helper**

```bash
git add .agents/skills/auto-dev-workflow/SKILL.md .agents/skills/auto-dev-workflow/references/workflow-contract.md .agents/skills/auto-dev-workflow/references/claude-code-adapter.md .agents/skills/auto-dev-workflow/references/gstack-adapter.md .agents/skills/auto-dev-workflow/agents/openai.yaml
bash .agents/skills/auto-dev-workflow/scripts/complete_task_commit.sh --message "docs(workflow): switch auto workflow to fast-forward integration" --cmd "uv run pytest tests/scripts/test_auto_dev_workflow.py -q"
```

## Chunk 3: Final Verification and Integration

### Task 4: Verify the workflow change and merge it back to `wcq`

**Files:**
- Verify: `tests/scripts/test_auto_dev_workflow.py`
- Verify: `.agents/skills/auto-dev-workflow/scripts/run_final_gate.sh`
- Verify: `.agents/skills/auto-dev-workflow/scripts/ff_merge_to_wcq.sh`

- [ ] **Step 1: Run scoped checks for the changed workflow files**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh --base-sha 03583c4c93a77866e8bb626ba398f1a7386e5fe5 --diff-target worktree --cmd 'uv run pytest tests/scripts/test_auto_dev_workflow.py -q'`
Expected: Workflow-specific checks and the targeted pytest command pass.

- [ ] **Step 2: Run the final gate**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_final_gate.sh --base-sha 03583c4c93a77866e8bb626ba398f1a7386e5fe5`
Expected: PASS

- [ ] **Step 3: Fast-forward `wcq` with the new integration script**

Run: `bash .agents/skills/auto-dev-workflow/scripts/ff_merge_to_wcq.sh --branch feat/20260408-replace-squash-merge --base-sha 03583c4c93a77866e8bb626ba398f1a7386e5fe5 --worktree /home/wcqqq21/q-agents/.worktrees/feat-20260408-replace-squash-merge`
Expected: `wcq` advances to the feature branch head, and the feature branch/worktree are removed.
