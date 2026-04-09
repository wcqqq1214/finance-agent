# Containerized Deployment

This repository's official deployment path is the Docker Compose stack defined in the top-level `docker-compose.yml`. Native development remains supported for contributors, but it is a separate workflow that continues to use `scripts/startup/` and `frontend` development commands instead of host bootstrap automation.

## Before You Start

1. Install Docker with Compose support.
2. Copy `.env.example` to `.env`.
3. Fill in the API keys your deployment needs before starting the stack.

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env -Force
```

If `.env` is missing, the startup wrappers fail fast and tell you to copy `.env.example` first.

## Memory Guidance

If you use Docker Desktop or OrbStack, allocate at least `4 GB` of memory to the Docker engine before running the build. `8 GB` is preferred for smoother image builds and to reduce out-of-memory failures during `pnpm build`, `uv sync`, and multi-service startup.

## Start The Stack

Wrapper entrypoints:

```bash
bash scripts/deploy/start_container_stack.sh
bash scripts/deploy/smoke_test_container_stack.sh
bash scripts/deploy/stop_container_stack.sh
```

Windows PowerShell wrappers:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy/start_container_stack.ps1
powershell -ExecutionPolicy Bypass -File scripts/deploy/smoke_test_container_stack.ps1
powershell -ExecutionPolicy Bypass -File scripts/deploy/stop_container_stack.ps1
```

Raw Compose entrypoints:

```bash
docker compose up -d --build
docker compose config
docker compose down --remove-orphans
```

The smoke scripts probe:

- `http://localhost:3000/`
- `http://localhost:8080/api/health`
- `http://localhost:8000/health`
- `http://localhost:8001/health`

They also verify Redis health from inside the Compose stack.

## CI Smoke Workflow

The repository's GitHub Actions smoke workflow now uses two runner lanes:

- GitHub-hosted matrix: `ubuntu-24.04` and `windows-2025`
- Dedicated self-hosted macOS job: `[self-hosted, macOS, container-smoke]`

The macOS self-hosted lane is restricted to trusted flows only. The workflow keeps `pull_request`, but the macOS job is guarded so fork pull requests do not target self-hosted infrastructure. That means real three-platform smoke coverage is guaranteed for `push`, `workflow_dispatch`, and same-repository pull requests.

The CI smoke flow is intentionally split into separate phases:

1. Prepare `.env` by copying `.env.example` to `.env` (`Copy-Item ... -Force` on Windows)
2. Check Docker availability
3. Resolve Compose configuration
4. Start the stack
5. Run smoke checks
6. Tear the stack down

The startup wrappers only bring the stack up. They do not run smoke verification internally anymore, so GitHub Actions can report startup failures and smoke failures as separate steps.

## Service Topology

The containerized deployment runs five services:

- `redis`
- `market-data-mcp`
- `news-search-mcp`
- `api`
- `frontend`

Compose-managed service discovery overrides the local defaults in `.env`. In containers, the backend uses `redis://redis:6379/0`, `http://market-data-mcp:8000/mcp`, and `http://news-search-mcp:8001/mcp` even though `.env.example` keeps localhost values for native development.

## Native Development Boundary

Containerized deployment and native development are intentionally separate:

- Official deployment: Docker Compose plus `scripts/deploy/`
- Native development: `scripts/startup/`, `uv sync`, and `cd frontend && pnpm dev`

Do not use the deploy wrappers to install host dependencies. If you want a local, non-containerized contributor workflow, keep using the existing `scripts/startup/` scripts and the frontend dev server.

## Troubleshooting

- `docker compose config` should resolve before you try to start containers.
- If startup fails immediately, confirm `.env` exists and contains the keys you need.
- If the frontend is blank or the wrappers time out, check whether Docker Desktop or OrbStack has enough memory.
- If Redis health fails, inspect `docker compose ps` and `docker compose logs redis`.
