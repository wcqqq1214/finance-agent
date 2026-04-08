# Remove Squash Merge Stub Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the retired `squash_merge_to_wcq.sh` compatibility stub and update the test contract so the legacy script path is treated as absent.

**Architecture:** This cleanup only changes the workflow script inventory and the script smoke-test contract. The implementation keeps `ff_merge_to_wcq.sh` untouched, removes the obsolete shell entrypoint, and shifts the test suite from redirect behavior to non-existence behavior.

**Tech Stack:** Bash workflow scripts, pytest, git worktrees, `uv`

---

## Chunk 1: Remove The Legacy Script Contract

### Task 1: Lock in the new absence contract with a failing test

**Files:**
- Modify: `tests/scripts/test_auto_dev_workflow.py`
- Test: `tests/scripts/test_auto_dev_workflow.py`

- [ ] **Step 1: Write the failing test**

Add a test near the existing `ff_merge_to_wcq` script tests:

```python
def test_squash_merge_to_wcq_script_is_absent() -> None:
    legacy_script = SCRIPT_ROOT / "squash_merge_to_wcq.sh"
    assert not legacy_script.exists()
```

- [ ] **Step 2: Run the new test to verify it fails**

Run: `uv run pytest tests/scripts/test_auto_dev_workflow.py -q -k squash_merge_to_wcq_script_is_absent`
Expected: FAIL because `.agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh` still exists.

- [ ] **Step 3: Remove the old redirect test**

Delete the test named `test_squash_merge_to_wcq_redirects_to_ff_merge_script` from `tests/scripts/test_auto_dev_workflow.py`.

- [ ] **Step 4: Delete the retired script**

Delete `.agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh`.

- [ ] **Step 5: Run the focused test to verify it passes**

Run: `uv run pytest tests/scripts/test_auto_dev_workflow.py -q -k squash_merge_to_wcq_script_is_absent`
Expected: PASS.

- [ ] **Step 6: Run the full script smoke-test file**

Run: `uv run pytest tests/scripts/test_auto_dev_workflow.py -q`
Expected: PASS for the entire file.

- [ ] **Step 7: Verify the repository no longer references the removed script**

Run: `rg -n "squash_merge_to_wcq\\.sh" . --hidden -g '!**/.git/**' -g '!**/node_modules/**'`
Expected: no matches.

- [ ] **Step 8: Commit the cleanup**

Run:

```bash
git add tests/scripts/test_auto_dev_workflow.py
git add -u .agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh
git commit -m "refactor(workflow): remove squash merge stub"
```
