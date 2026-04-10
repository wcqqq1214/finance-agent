# Container Smoke Three-Platform Adapt Design

## Goal

Repair the container smoke CI so `ubuntu-24.04`, `windows-2025`, and macOS each run the intended smoke workflow on infrastructure that can actually satisfy the stack contract.

## Context

The runner migration already moved the workflow away from `*-latest`, but the latest public run still fails in two different places:

- `windows-2025` fails in `Check Windows Docker server platform`, which means the hosted runner is not already exposing the expected Linux container engine.
- `ubuntu-24.04` fails in `Start container stack`, so the failure is now in the real Compose startup path rather than in workflow syntax or runner selection.

Local investigation adds one more signal:

- the service processes themselves can start and answer the documented health endpoints when run directly on the host
- the Docker build path is more fragile than necessary because both Dockerfiles force resolution of `docker/dockerfile:1.7` before the application build even begins

That means the remaining work is no longer "pick the right runners". It is "make the hosted Windows runner reach a Linux container engine" and "make container startup less brittle on Ubuntu".

## Approaches Considered

### Approach A: Keep the current Windows preflight and only add more diagnostics

This was rejected because the current Windows failure happens before the stack even starts. More logging would explain the failure, but it would not make the job pass.

### Approach B: Drop Windows real smoke and replace it with contract checks

This would likely turn CI green fastest, but it gives up the real three-platform coverage requirement the user explicitly wanted to preserve.

### Approach C: Keep real smoke, but adapt each failing platform to the environment it actually provides

This is the chosen approach.

- On Windows, switch Docker Desktop into Linux-container mode before enforcing the server-platform guard.
- On Ubuntu, remove the unnecessary remote Dockerfile syntax dependency so `docker compose up -d --build` has fewer failure points before image construction.

This keeps real smoke coverage while fixing the two failures at their actual boundaries.

## Chosen Design

### Runner strategy

Keep the existing split:

- hosted matrix job for `ubuntu-24.04` and `windows-2025`
- dedicated self-hosted macOS job on `[self-hosted, macOS, container-smoke]`

That part of the earlier redesign stays correct and does not need to be reversed.

### Windows hosted runner contract

The workflow should treat Windows as a hosted machine that may boot Docker in Windows-container mode first.

The Windows lane therefore becomes:

1. check out the repository
2. prepare `.env`
3. verify Docker CLI availability
4. if the Docker server is not already `linux/amd64`, attempt to switch to Linux containers
5. wait for Docker to come back
6. enforce the final platform guard that requires `linux/amd64`
7. continue with compose config, startup, smoke, and teardown

Implementation requirements:

- prefer an official Docker Desktop CLI if available
- support the legacy `DockerCli.exe -SwitchLinuxEngine` path as fallback because hosted Windows images may not expose the newer subcommand surface consistently
- fail with a clear error if the runner still does not report `linux/amd64` after the switch attempt

### Ubuntu container-start contract

The Ubuntu job now fails in `Start container stack`, not in preflight. The service processes themselves are healthy outside Docker, so the remaining fragility is in the Docker build/start path.

The immediate hardening change is:

- remove `# syntax=docker/dockerfile:1.7` from `docker/backend.Dockerfile`
- remove `# syntax=docker/dockerfile:1.7` from `docker/frontend.Dockerfile`

Reasoning:

- the Dockerfiles only use standard instructions
- the remote syntax image is an unnecessary external dependency in the smoke path
- removing it reduces one network/build-resolution failure point before the actual application images are even built

This does not change runtime behavior of the containers themselves. It only reduces startup fragility.

### Workflow phase split

Keep startup and smoke verification as separate workflow steps.

That separation is already the right shape because:

- `Start container stack` isolates build/boot failures
- `Run smoke checks` isolates endpoint and Redis health failures
- the current Ubuntu failure is diagnosable precisely because the phases are already separated

### Trust boundary

Keep the existing policy:

- preserve `pull_request`
- do not introduce `pull_request_target`
- keep the macOS self-hosted guard that excludes fork pull requests

No trust-boundary change is needed for this follow-up fix.

## Acceptance Criteria

1. `windows-2025` no longer fails solely because Docker starts in Windows-container mode.
2. The Windows job contains an explicit Linux-engine preparation step before the final platform assertion.
3. The final Windows platform assertion still requires `linux/amd64`.
4. `ubuntu-24.04` no longer depends on a remote Dockerfile syntax image during stack startup.
5. Both Dockerfiles remain valid for the existing Compose build flow after removing the syntax directive.
6. Contract tests cover the Windows Linux-engine preparation step and the Dockerfile syntax-dependency removal.
7. Existing runner-selection, trust-boundary, wrapper-split, and checkout-v5 contract tests remain green.

## Files In Scope

- `.github/workflows/container-stack-smoke.yml`
- `docker/backend.Dockerfile`
- `docker/frontend.Dockerfile`
- `tests/scripts/test_container_stack_contract.py`
- `docs/deployment/containerized.md`
- `docs/superpowers/specs/2026-04-10-container-smoke-three-platform-adapt-design.md`
- `docs/superpowers/plans/2026-04-10-container-smoke-three-platform-adapt.md`

## Out Of Scope

- reverting the hosted/self-hosted runner split
- downgrading Windows or macOS to contract-only coverage
- changing the application health endpoints
- changing Compose topology
- introducing a separate smoke-only application configuration

## Testing

- add a regression test that requires a dedicated Windows step which attempts to switch Docker into Linux mode before the final platform check
- add a regression test that keeps the final `linux/amd64` assertion
- add a regression test that requires both Dockerfiles to omit the remote `docker/dockerfile:1.7` syntax directive
- rerun `uv run pytest tests/scripts/test_container_stack_contract.py -q`
- rerun the repository scoped check command for this task
