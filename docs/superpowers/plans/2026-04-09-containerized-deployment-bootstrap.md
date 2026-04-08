# Containerized Deployment Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the repository from a Redis-only compose stub to a production-like five-service container stack with safe wrapper scripts, deployment docs, and cross-platform smoke verification.

**Architecture:** Keep one official compose topology rooted in the existing top-level `docker-compose.yml`, but expand it to run `redis`, `market-data-mcp`, `news-search-mcp`, `api`, and `frontend` as separate services. Use one shared backend Dockerfile with stage targets for the Python services, one frontend Dockerfile, thin shell/PowerShell wrappers for start-stop-smoke flows, and one contract test file that locks in the deployment surface so future edits cannot silently regress it.

**Tech Stack:** Docker Compose, Python 3.13, `uv`, FastAPI, Next.js 16, pnpm, Bash, PowerShell, pytest, GitHub Actions

---

## File Map

- Modify: `docker-compose.yml`
  - Expand the current Redis-only compose file into the official five-service stack.
- Create: `.dockerignore`
  - Keep build contexts small and deterministic for backend/frontend images.
- Create: `docker/backend.Dockerfile`
  - Shared multi-stage Python build with named targets for `api`, `market-data-mcp`, and `news-search-mcp`.
- Create: `docker/frontend.Dockerfile`
  - Production frontend build using pnpm/corepack and `next build` + `next start`.
- Create: `scripts/deploy/start_container_stack.sh`
  - Unix wrapper for startup, `.env` validation, compose up, and health polling.
- Create: `scripts/deploy/stop_container_stack.sh`
  - Unix wrapper for deterministic compose teardown.
- Create: `scripts/deploy/smoke_test_container_stack.sh`
  - Unix smoke runner for HTTP/Redis health verification.
- Create: `scripts/deploy/start_container_stack.ps1`
  - Native Windows startup wrapper with the same contract as the shell version.
- Create: `scripts/deploy/stop_container_stack.ps1`
  - Native Windows teardown wrapper.
- Create: `scripts/deploy/smoke_test_container_stack.ps1`
  - Native Windows smoke runner.
- Modify: `.env.example`
  - Clarify local-vs-compose behavior and make compose overrides predictable.
- Create: `docs/deployment/containerized.md`
  - Canonical deployment instructions and troubleshooting.
- Modify: `README.md`
  - Add a short deployment section and link to the dedicated deployment doc.
- Modify: `README.zh-CN.md`
  - Mirror the deployment entrypoint and troubleshooting link in Chinese.
- Modify: `README.ja.md`
  - Mirror the deployment entrypoint and troubleshooting link in Japanese.
- Create: `.github/workflows/container-stack-smoke.yml`
  - OS-matrix smoke workflow for Linux, macOS, and Windows.
- Create: `tests/scripts/test_container_stack_contract.py`
  - Contract tests for compose topology, Dockerfiles, wrappers, docs, and CI workflow wiring.

## Chunk 1: Container Build And Compose Contract

### Task 1: Lock in the five-service compose contract with a failing test

**Files:**
- Create: `tests/scripts/test_container_stack_contract.py`
- Modify: `docker-compose.yml`
- Create: `.dockerignore`
- Create: `docker/backend.Dockerfile`
- Create: `docker/frontend.Dockerfile`

- [ ] **Step 1: Write the failing contract tests**

Add focused tests that assert:

- `docker-compose.yml` defines exactly `redis`, `market-data-mcp`, `news-search-mcp`, `api`, and `frontend`
- `docker-compose.yml` still keeps `redis_data` as a named volume
- `api` points to `redis://redis:6379/0`
- `api` points to `http://market-data-mcp:8000/mcp` and `http://news-search-mcp:8001/mcp`
- `frontend` exposes `NEXT_PUBLIC_API_URL=http://localhost:8080`
- `docker/backend.Dockerfile` contains named targets for the three Python services
- `docker/frontend.Dockerfile` uses pnpm/corepack and production startup

Suggested test skeleton:

```python
def test_docker_compose_defines_full_container_stack() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for service in (
        "redis:",
        "market-data-mcp:",
        "news-search-mcp:",
        "api:",
        "frontend:",
    ):
        assert service in compose
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q -k compose`
Expected: FAIL because the current compose file only defines Redis and the Dockerfiles do not exist yet.

- [ ] **Step 3: Write the minimal container packaging**

Implement:

- `.dockerignore` with at least `.git`, `.worktrees`, `frontend/node_modules`, `frontend/.next`, `.venv`, `__pycache__`, `data/reports`, and local caches
- `docker/backend.Dockerfile` with:
  - a base stage that copies `/uv` from `ghcr.io/astral-sh/uv`
  - dependency sync from `pyproject.toml`
  - named final targets `api`, `market-data-mcp`, `news-search-mcp`
- `docker/frontend.Dockerfile` with:
  - pnpm install from lockfile
  - `pnpm build`
  - `pnpm start --hostname 0.0.0.0 --port 3000`
- `docker-compose.yml` expanded from the current Redis-only file to the full service graph with health checks and `depends_on`

- [ ] **Step 4: Re-run the focused test to verify it passes**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q -k compose`
Expected: PASS

- [ ] **Step 5: Verify compose resolves successfully**

Run: `docker compose config`
Expected: PASS and rendered output includes the five named services without interpolation errors.

- [ ] **Step 6: Commit the container build slice**

Run:

```bash
git add tests/scripts/test_container_stack_contract.py
git add docker-compose.yml .dockerignore docker/backend.Dockerfile docker/frontend.Dockerfile
git commit -m "feat(deploy): add container stack images"
```

## Chunk 2: Wrapper Script Contract

### Task 2: Add failing wrapper-script coverage before scripting the deployment entrypoints

**Files:**
- Modify: `tests/scripts/test_container_stack_contract.py`
- Create: `scripts/deploy/start_container_stack.sh`
- Create: `scripts/deploy/stop_container_stack.sh`
- Create: `scripts/deploy/smoke_test_container_stack.sh`
- Create: `scripts/deploy/start_container_stack.ps1`
- Create: `scripts/deploy/stop_container_stack.ps1`
- Create: `scripts/deploy/smoke_test_container_stack.ps1`

- [ ] **Step 1: Write the failing wrapper tests**

Extend the contract test file to assert:

- all six wrapper scripts exist
- startup wrappers fail fast when `.env` is missing
- startup wrappers call `docker compose up -d --build`
- stop wrappers call `docker compose down`
- smoke wrappers check:
  - `http://localhost:3000/`
  - `http://localhost:8080/api/health`
  - `http://localhost:8000/health`
  - `http://localhost:8001/health`
- shell wrappers do not contain package-manager installation commands like `brew install`, `apt-get install`, `curl ... uv`, or `winget install`

Suggested shell-contract assertion:

```python
def test_start_wrapper_requires_dotenv() -> None:
    script = (REPO_ROOT / "scripts" / "deploy" / "start_container_stack.sh").read_text(encoding="utf-8")
    assert ".env" in script
    assert "docker compose up -d --build" in script
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q -k wrapper`
Expected: FAIL because the deploy wrappers do not exist yet.

- [ ] **Step 3: Write the minimal wrapper scripts**

Implement the six scripts with the following contract:

- `start_*`:
  - exit non-zero if `.env` is missing
  - check Docker / Docker Compose availability
  - run `docker compose up -d --build`
  - poll documented health endpoints
- `stop_*`:
  - run `docker compose down`
- `smoke_test_*`:
  - verify the four HTTP endpoints above
  - verify Redis health via `docker compose exec` or `docker compose ps` plus Redis health state

- [ ] **Step 4: Re-run the focused test to verify it passes**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q -k wrapper`
Expected: PASS

- [ ] **Step 5: Smoke-check the wrappers with command stubs**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q -k dotenv`
Expected: PASS and confirms the fail-fast `.env` behavior stays enforced.

- [ ] **Step 6: Commit the wrapper slice**

Run:

```bash
git add tests/scripts/test_container_stack_contract.py
git add scripts/deploy/start_container_stack.sh scripts/deploy/stop_container_stack.sh scripts/deploy/smoke_test_container_stack.sh
git add scripts/deploy/start_container_stack.ps1 scripts/deploy/stop_container_stack.ps1 scripts/deploy/smoke_test_container_stack.ps1
git commit -m "feat(deploy): add container stack wrappers"
```

## Chunk 3: Environment And Documentation Contract

### Task 3: Add failing documentation coverage before editing docs

**Files:**
- Modify: `tests/scripts/test_container_stack_contract.py`
- Modify: `.env.example`
- Create: `docs/deployment/containerized.md`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `README.ja.md`

- [ ] **Step 1: Write the failing docs contract tests**

Extend the contract test file to assert:

- `docs/deployment/containerized.md` exists
- docs mention both raw compose and wrapper entrypoints
- docs mention `.env.example` → `.env`
- docs mention Docker Desktop / OrbStack memory guidance with `4 GB` minimum and `8 GB` preferred
- docs clearly separate containerized deployment from native development
- `.env.example` still exposes the relevant keys but documents compose-managed overrides for Redis and MCP URLs

Suggested assertion:

```python
def test_container_deployment_doc_mentions_memory_guidance() -> None:
    text = (REPO_ROOT / "docs" / "deployment" / "containerized.md").read_text(encoding="utf-8")
    assert "4 GB" in text
    assert "8 GB" in text
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q -k doc`
Expected: FAIL because the deployment doc and README references do not exist yet.

- [ ] **Step 3: Write the minimal documentation**

Implement:

- `docs/deployment/containerized.md` as the canonical deployment guide
- `.env.example` comments that distinguish host-local defaults from compose overrides
- concise deployment sections in the three README files that link to the deployment doc and keep native development as a separate path

- [ ] **Step 4: Re-run the focused test to verify it passes**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q -k doc`
Expected: PASS

- [ ] **Step 5: Verify the docs reference the right commands**

Run: `rg -n "docker compose up -d --build|start_container_stack|smoke_test_container_stack|4 GB|8 GB" README.md README.zh-CN.md README.ja.md docs/deployment/containerized.md .env.example`
Expected: matches in the deployment docs and README sections only.

- [ ] **Step 6: Commit the docs slice**

Run:

```bash
git add tests/scripts/test_container_stack_contract.py
git add .env.example docs/deployment/containerized.md README.md README.zh-CN.md README.ja.md
git commit -m "docs(deploy): add container deployment guide"
```

## Chunk 4: Cross-Platform CI Smoke Verification

### Task 4: Add failing CI contract coverage before writing the workflow

**Files:**
- Modify: `tests/scripts/test_container_stack_contract.py`
- Create: `.github/workflows/container-stack-smoke.yml`

- [ ] **Step 1: Write the failing CI contract tests**

Extend the contract test file to assert the workflow:

- exists at `.github/workflows/container-stack-smoke.yml`
- runs on:
  - `ubuntu-latest`
  - `macos-latest`
  - `windows-latest`
- copies `.env.example` to `.env` (or otherwise creates `.env`)
- runs compose resolution/build/start/smoke/teardown
- uses `.sh` wrappers on Unix runners and `.ps1` wrappers on Windows runners

Suggested assertion:

```python
def test_container_smoke_workflow_covers_three_operating_systems() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "container-stack-smoke.yml").read_text(encoding="utf-8")
    for runner in ("ubuntu-latest", "macos-latest", "windows-latest"):
        assert runner in workflow
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q -k workflow`
Expected: FAIL because the workflow file does not exist yet.

- [ ] **Step 3: Write the minimal workflow**

Implement `.github/workflows/container-stack-smoke.yml` with:

- one matrix job over Linux, macOS, and Windows
- checkout
- `.env` creation from `.env.example`
- Docker availability check
- `docker compose config`
- wrapper-based startup
- wrapper-based smoke test
- teardown in an always-run cleanup step

- [ ] **Step 4: Re-run the focused test to verify it passes**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q -k workflow`
Expected: PASS

- [ ] **Step 5: Run the full container contract file**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q`
Expected: PASS

- [ ] **Step 6: Commit the CI slice**

Run:

```bash
git add tests/scripts/test_container_stack_contract.py .github/workflows/container-stack-smoke.yml
git commit -m "ci(deploy): add container stack smoke matrix"
```

## Chunk 5: Scoped Verification And Final Gate

### Task 5: Verify the full container deployment slice

**Files:**
- Modify: `docker-compose.yml`
- Create: `.dockerignore`
- Create: `docker/backend.Dockerfile`
- Create: `docker/frontend.Dockerfile`
- Create: `scripts/deploy/start_container_stack.sh`
- Create: `scripts/deploy/stop_container_stack.sh`
- Create: `scripts/deploy/smoke_test_container_stack.sh`
- Create: `scripts/deploy/start_container_stack.ps1`
- Create: `scripts/deploy/stop_container_stack.ps1`
- Create: `scripts/deploy/smoke_test_container_stack.ps1`
- Modify: `.env.example`
- Create: `docs/deployment/containerized.md`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `README.ja.md`
- Create: `.github/workflows/container-stack-smoke.yml`
- Create: `tests/scripts/test_container_stack_contract.py`

- [ ] **Step 1: Run the focused contract tests**

Run: `uv run pytest tests/scripts/test_container_stack_contract.py -q`
Expected: PASS

- [ ] **Step 2: Resolve the compose file once more**

Run: `docker compose config`
Expected: PASS and rendered output includes `redis`, `market-data-mcp`, `news-search-mcp`, `api`, and `frontend`.

- [ ] **Step 3: Run scoped checks with the feature branch base**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh --base-sha 03712e9230c6b882195304ccb6782f2f6b269e7d --diff-target worktree --cmd 'uv run pytest tests/scripts/test_container_stack_contract.py -q'`
Expected: PASS

- [ ] **Step 4: Run the final gate**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_final_gate.sh --base-sha 03712e9230c6b882195304ccb6782f2f6b269e7d`
Expected: PASS once the new non-integration test file is present and all touched frontend checks are green.

- [ ] **Step 5: Optional live smoke run if Docker is available locally**

Run: `bash scripts/deploy/start_container_stack.sh && bash scripts/deploy/smoke_test_container_stack.sh`
Expected: PASS with healthy HTTP endpoints and Redis. If `.env` is intentionally absent, the startup wrapper should fail fast with the documented message instead of mutating the host.
