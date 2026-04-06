# Merge Conflict Summary Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured conflict-file output to `squash_merge_to_wcq.sh` when the temporary squash merge fails.

**Architecture:** Extend the merge script with a small helper that reads unmerged paths from the temporary integration worktree and appends them to the fatal error output. Drive the change with a script-level regression test that creates a real merge conflict in a temp repo.

**Tech Stack:** Bash, git worktrees, pytest script tests

---

## Chunk 1: Conflict Summary Output

### Task 1: Reproduce conflict failure in tests

**Files:**
- Modify: `tests/scripts/test_auto_dev_workflow.py`
- Test: `tests/scripts/test_auto_dev_workflow.py`

- [ ] **Step 1: Write the failing test**

Add a test that creates a `wcq` base commit, then creates a feature worktree from the previous commit so the branch can conflict on `README.md`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/scripts/test_auto_dev_workflow.py -q`
Expected: FAIL because the merge script reports only the generic conflict error and omits conflicted file paths.

- [ ] **Step 3: Write minimal implementation**

Update `squash_merge_to_wcq.sh` to read unmerged paths from the temporary integration worktree and include them under `CONFLICT_FILES:` in stderr before exiting.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/scripts/test_auto_dev_workflow.py -q`
Expected: PASS with the new conflict-summary assertion satisfied.

- [ ] **Step 5: Run focused verification**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh --base-sha <BASE_SHA> --diff-target worktree --cmd 'uv run python -m pytest tests/scripts/test_auto_dev_workflow.py -q'`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-04-07-merge-conflict-summary-design.md \
        docs/superpowers/plans/2026-04-07-merge-conflict-summary.md \
        tests/scripts/test_auto_dev_workflow.py \
        .agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh
git commit -m "fix(skill): summarize merge conflict files"
```
