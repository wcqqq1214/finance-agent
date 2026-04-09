# Container Smoke Three-Platform Adapt Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep real container smoke coverage on Ubuntu, macOS, and Windows by pinning supported runners, splitting startup from smoke verification, and updating the workflow contract tests.

**Architecture:** Ubuntu and Windows stay in a hosted smoke matrix, while macOS moves to a dedicated self-hosted job with an explicit trust boundary and timeout. The deployment wrappers stop chaining smoke verification so GitHub Actions can report startup and health-check failures as separate steps.

**Tech Stack:** GitHub Actions YAML, Bash, PowerShell, pytest

---

## Chunk 1: Workflow Contract And Wrapper Split

### Task 1: Lock the contract, then implement the workflow and wrapper changes

**Files:**
- Modify: `.github/workflows/container-stack-smoke.yml`
- Modify: `scripts/deploy/start_container_stack.sh`
- Modify: `scripts/deploy/start_container_stack.ps1`
- Modify: `tests/scripts/test_container_stack_contract.py`
- Modify: `docs/deployment/containerized.md`
- Verify unchanged reliance: `scripts/deploy/smoke_test_container_stack.sh`
- Verify unchanged reliance: `scripts/deploy/smoke_test_container_stack.ps1`
- Verify unchanged reliance: `scripts/deploy/stop_container_stack.sh`
- Verify unchanged reliance: `scripts/deploy/stop_container_stack.ps1`

- [ ] **Step 1: Write the failing regression tests**

Add assertions in `tests/scripts/test_container_stack_contract.py` that require:

- workflow runner pins `ubuntu-24.04` and `windows-2025`
- workflow includes `self-hosted`, `macOS`, and `container-smoke`
- workflow no longer includes `ubuntu-latest`, `windows-latest`, or `macos-latest`
- workflow isolates macOS into a dedicated self-hosted job instead of mixing it into the hosted matrix
- workflow uses `actions/checkout@v5`
- workflow `Check Docker availability` step still contains both `docker version` and `docker compose version`
- workflow includes the Windows Docker server platform check for `linux/amd64`
- macOS job sets `timeout-minutes: 30`
- macOS job contains a guard equivalent to `github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository`
- workflow keeps `on.pull_request` and does not introduce `pull_request_target`
- workflow keeps teardown on the wrapper entrypoint and marks it unconditional with `if: always()`
- workflow copies `.env.example` to `.env` on each platform
- startup wrappers contain `docker compose up -d --build`
- startup wrappers do not invoke `smoke_test_container_stack.sh` or `smoke_test_container_stack.ps1`
- workflow startup and smoke steps each call the correct wrapper explicitly
- workflow assertions use tolerant string or regex checks rather than formatting-sensitive exact YAML blocks

- [ ] **Step 2: Run the contract test and verify it fails**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q`
Expected: FAIL because at least one of the new workflow-runner or wrapper-split assertions is not satisfied by the current code.

- [ ] **Step 3: Write the minimal implementation**

Update `.github/workflows/container-stack-smoke.yml` to:

- keep a hosted matrix for `ubuntu-24.04` and `windows-2025`
- define a dedicated macOS job on `[self-hosted, macOS, container-smoke]`
- upgrade `actions/checkout` from `v4` to `v5`
- keep `on.pull_request` and do not add `pull_request_target`
- keep `Prepare .env`, `Check Docker availability`, and `Resolve compose configuration`
- add the Windows Docker server platform preflight using `docker version --format '{{.Server.Os}}/{{.Server.Arch}}'` and fail unless it resolves to `linux/amd64`
- set `timeout-minutes: 30` on the macOS job
- guard the macOS job with `github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository` so fork pull requests do not target self-hosted infrastructure
- run startup and smoke verification as separate steps that continue to call `start_container_stack.*` and `smoke_test_container_stack.*`
- keep teardown on `stop_container_stack.*` with `if: always()`

Update `scripts/deploy/start_container_stack.sh` and `scripts/deploy/start_container_stack.ps1` so they only validate prerequisites and run `docker compose up -d --build`.

Leave `smoke_test_container_stack.*` and `stop_container_stack.*` unchanged unless verification shows they still depend on the old chained startup behavior.

Update `docs/deployment/containerized.md` to document the self-hosted macOS runner requirement, the trusted-flow boundary, and the separated workflow phases.

- [ ] **Step 4: Run the contract test and verify it passes**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q`
Expected: PASS

- [ ] **Step 5: Run scoped checks for the task**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh --base-sha <BASE_SHA> --diff-target worktree --cmd 'uv run pytest tests/scripts/test_container_stack_contract.py -q'`
Expected setup: replace `<BASE_SHA>` with the recorded value printed by `create_feature_workspace.sh` for the current feature worktree.
Expected: PASS

- [ ] **Step 6: Commit the task**

Run:

```bash
git add .github/workflows/container-stack-smoke.yml scripts/deploy/start_container_stack.sh scripts/deploy/start_container_stack.ps1 tests/scripts/test_container_stack_contract.py docs/deployment/containerized.md docs/superpowers/specs/2026-04-10-container-smoke-three-platform-adapt-design.md docs/superpowers/plans/2026-04-10-container-smoke-three-platform-adapt.md
git commit -m "fix(ci): adapt container smoke runners"
```

Expected: commit created with only the planned workflow, wrapper, test, doc, spec, and plan changes that were actually touched during this task.
