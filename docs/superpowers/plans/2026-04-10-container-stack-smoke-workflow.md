# Container Stack Smoke Workflow Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the container stack smoke workflow syntactically valid for GitHub Actions without dropping the Linux, macOS, or Windows smoke coverage.

**Architecture:** Keep the existing job matrix and remove the illegal `matrix.shell` usage from step metadata. Rely on each runner's default shell while preserving the existing per-OS command strings in the matrix.

**Tech Stack:** GitHub Actions YAML, pytest

---

## Chunk 1: Regression Coverage And Workflow Fix

### Task 1: Add the failing regression test

**Files:**
- Modify: `tests/scripts/test_container_stack_contract.py`
- Test: `tests/scripts/test_container_stack_contract.py`

- [ ] **Step 1: Write the failing test**

Add a test that rejects any step-level `shell:` entry using `${{ matrix.* }}`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q`
Expected: FAIL because the workflow currently contains `shell: ${{ matrix.shell }}`

- [ ] **Step 3: Write minimal implementation**

Update `.github/workflows/container-stack-smoke.yml` so no step-level `shell:` field references `${{ matrix.* }}`. Keep the current matrix-driven commands and let the runner default shell execute them.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q`
Expected: PASS

- [ ] **Step 5: Verify final diff**

Confirm only the workflow, the regression test, and the design/plan docs changed for this task.
