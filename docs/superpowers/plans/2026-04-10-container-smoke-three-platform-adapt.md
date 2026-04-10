# Container Smoke Three-Platform Adapt Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the container smoke workflow pass again by switching hosted Windows runners into Linux-container mode before startup and by removing unnecessary Docker build fragility on Ubuntu.

**Architecture:** Keep the existing hosted Ubuntu/Windows plus self-hosted macOS split, but extend the Windows preflight with an explicit Linux-engine preparation step. Remove the remote Dockerfile syntax dependency from both image builds so the Ubuntu startup path has fewer external failure points before the application stack is even constructed.

**Tech Stack:** GitHub Actions YAML, Dockerfiles, pytest text-contract tests, Markdown docs

---

## Chunk 1: Lock the New Failure Contracts

### Task 1: Write failing tests for the Windows engine-prep path and Dockerfile hardening

**Files:**
- Modify: `tests/scripts/test_container_stack_contract.py`
- Reference: `.github/workflows/container-stack-smoke.yml`
- Reference: `docker/backend.Dockerfile`
- Reference: `docker/frontend.Dockerfile`

- [ ] **Step 1: Write the failing regression tests**

Add assertions that require:

- the workflow contains a Windows-only step that attempts to switch Docker into Linux mode before the final platform check
- the workflow still performs the final `docker version --format '{{.Server.Os}}/{{.Server.Arch}}'` assertion and requires `linux/amd64`
- `docker/backend.Dockerfile` does not contain `# syntax=docker/dockerfile:1.7`
- `docker/frontend.Dockerfile` does not contain `# syntax=docker/dockerfile:1.7`

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q`
Expected: FAIL because the current workflow does not prepare the Windows Linux engine and the Dockerfiles still pin the remote syntax image.

## Chunk 2: Implement the Minimal Fix

### Task 2: Update the workflow, Dockerfiles, and docs

**Files:**
- Modify: `.github/workflows/container-stack-smoke.yml`
- Modify: `docker/backend.Dockerfile`
- Modify: `docker/frontend.Dockerfile`
- Modify: `docs/deployment/containerized.md`
- Modify: `tests/scripts/test_container_stack_contract.py`
- Create: `docs/superpowers/specs/2026-04-10-container-smoke-three-platform-adapt-design.md`
- Create: `docs/superpowers/plans/2026-04-10-container-smoke-three-platform-adapt.md`

- [ ] **Step 3: Write the minimal implementation**

Update `.github/workflows/container-stack-smoke.yml` so the Windows lane:

- checks Docker availability first
- attempts to switch to Linux containers when the server platform is not already `linux/amd64`
- waits/retries until Docker responds again
- keeps the existing final `linux/amd64` guard before compose startup

Update both Dockerfiles to remove the remote `docker/dockerfile:1.7` syntax directive.

Update `docs/deployment/containerized.md` to explain:

- hosted Windows runners may require an explicit Linux-engine switch
- the smoke stack avoids unnecessary remote Dockerfile syntax resolution in the build path

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q`
Expected: PASS

## Chunk 3: Verification And Integration

### Task 3: Run scoped verification and prepare integration

**Files:**
- Modify: `.github/workflows/container-stack-smoke.yml`
- Modify: `docker/backend.Dockerfile`
- Modify: `docker/frontend.Dockerfile`
- Modify: `docs/deployment/containerized.md`
- Modify: `tests/scripts/test_container_stack_contract.py`
- Create: `docs/superpowers/specs/2026-04-10-container-smoke-three-platform-adapt-design.md`
- Create: `docs/superpowers/plans/2026-04-10-container-smoke-three-platform-adapt.md`

- [ ] **Step 5: Run scoped checks**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh --base-sha <BASE_SHA> --diff-target worktree --cmd 'uv run pytest tests/scripts/test_container_stack_contract.py -q'`
Expected: PASS

- [ ] **Step 6: Run the final gate**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_final_gate.sh --base-sha <BASE_SHA>`
Expected: PASS

- [ ] **Step 7: Commit the task**

Run:

```bash
git add .github/workflows/container-stack-smoke.yml docker/backend.Dockerfile docker/frontend.Dockerfile tests/scripts/test_container_stack_contract.py docs/deployment/containerized.md docs/superpowers/specs/2026-04-10-container-smoke-three-platform-adapt-design.md docs/superpowers/plans/2026-04-10-container-smoke-three-platform-adapt.md
git commit -m "fix(ci): harden container smoke startup"
```

Expected: a single commit containing only the workflow, Dockerfile, test, and documentation changes for this fix.
