# Container Smoke Three-Platform Adapt Design

## Goal

Repair `.github/workflows/container-stack-smoke.yml` so the repository keeps real container smoke coverage on Ubuntu, macOS, and Windows while matching what GitHub-hosted and self-hosted runners can actually support.

## Context

The current workflow assumes all three `*-latest` runners can run the same Docker preflight and container startup path. The latest run disproves that assumption:

- `macos-latest` fails at `docker version`, so the hosted macOS runner does not provide the required Docker environment.
- `ubuntu-latest` and `windows-latest` reach the container startup step, but the workflow bundles stack startup and smoke verification into one wrapper entrypoint, which makes failures harder to localize.
- The current run also emits the GitHub warning that `actions/checkout@v4` still runs on Node.js 20. The `actions/checkout` v5 release notes explicitly say v5 updates the action runtime to Node 24, so upgrading that action is part of this fix.

## Approaches Considered

### Approach A: Keep all three jobs on GitHub-hosted runners

Try to bootstrap Docker on hosted macOS and keep Windows on hosted runners.

This was rejected because the current hosted macOS environment already fails before any project code runs, and adding an ad-hoc Docker bootstrap path would make the workflow more fragile than the smoke check it is supposed to validate.

### Approach B: Run real smoke only on Ubuntu, downgrade macOS/Windows to contract checks

This would likely produce the fastest green CI, but it drops the user's requirement for real three-platform container coverage.

### Approach C: Keep real three-platform smoke, but move unsupported platforms to controlled runners

Use fixed runner targets instead of `*-latest`, keep Ubuntu and Windows on GitHub-hosted runners, move macOS to a self-hosted runner label that is expected to provide Docker, and structure the workflow so macOS is isolated from the hosted matrix.

This is the chosen approach because it preserves the intended coverage and makes the infrastructure assumption explicit in the workflow instead of hiding it in failing shell scripts.

## Chosen Design

### Runner strategy

- Ubuntu and Windows remain in one GitHub-hosted smoke job matrix with fixed labels `ubuntu-24.04` and `windows-2025`.
- macOS moves to a dedicated `smoke-macos` job that runs on explicit self-hosted labels `[self-hosted, macOS, container-smoke]`.

Runner label validation note:

- GitHub's GitHub-hosted runner reference currently lists `windows-2025` as a valid hosted Windows label, so this workflow pins to `windows-2025` instead of `windows-latest`.
- GitHub's runner-images release notes for the Windows Server 2025 image announce Docker Server/Client and Docker Compose updates on that image. Based on that official image inventory, this design treats Docker Engine plus Compose v2 as part of the expected hosted Windows contract.

The macOS self-hosted runner contract is:

- the runner must advertise the default `self-hosted` and `macOS` labels plus custom label `container-smoke`
- the runner owner must preinstall a working Docker Engine / Docker Desktop environment with `docker version` and `docker compose version`
- if no runner matches those labels, GitHub will leave the job queued until a matching runner becomes available, and GitHub's self-hosted runner routing rules eventually fail queued jobs after the platform timeout window
- the workflow should set `timeout-minutes: 30` on the macOS job to cap execution time after the runner has started the job; this is not a mitigation for queue delay
- runner availability is an operational dependency outside repository control, so this workflow does not attempt to fast-fail missing macOS self-hosted capacity before scheduling

The workflow must encode these runner requirements directly in YAML so a maintainer can tell from the job definitions which environments are expected to own Docker.

Minimal shape:

```yaml
jobs:
  smoke-hosted:
    strategy:
      matrix:
        include:
          - os: ubuntu-24.04
          - os: windows-2025
    runs-on: ${{ matrix.os }}

  smoke-macos:
    runs-on: [self-hosted, macOS, container-smoke]
    timeout-minutes: 30
```

The Windows hosted runner contract is:

- `runs-on: windows-2025`
- `docker version` must succeed
- `docker compose version` must succeed
- preflight should also verify the Docker server reports `linux/amd64`, because the smoke scripts validate the existing Linux-based Compose stack rather than switching to Windows containers
- the workflow will not attempt to switch Docker into Linux-container mode; if that preflight fails, the result is treated as a runner or image configuration problem rather than an application regression
- if GitHub retires `windows-2025`, the maintenance fallback label is `windows-2022`; that fallback is a future workflow-and-test update, not runtime fallback logic inside this patch

The expected Windows platform-check command is a PowerShell guard around:

`docker version --format '{{.Server.Os}}/{{.Server.Arch}}'`

and it must fail the step unless that value resolves to `linux/amd64`.

### Trust boundary

Real three-platform smoke coverage is guaranteed for trusted flows only:

- `push`
- `workflow_dispatch`
- same-repository pull requests

Fork pull requests are out of scope for the macOS self-hosted job because GitHub documents the security risk of running untrusted fork code on self-hosted runners. The workflow should therefore guard the macOS job so fork PRs do not target self-hosted infrastructure. Ubuntu and Windows hosted smoke may still run for those PRs.

Concrete workflow shape:

- keep `on.pull_request`
- do not add `pull_request_target`
- set the macOS job guard to:

```yaml
if: ${{ github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository }}
```

### Step structure

The workflow should stop treating `start_container_stack.*` as both startup and smoke verification.

Instead, each job should expose the same five phases:

1. preflight (`docker version`, `docker compose version`, environment preparation)
2. compose resolution (`docker compose config`)
3. stack startup (`start_container_stack.*`)
4. smoke verification (`smoke_test_container_stack.*`)
5. teardown (`stop_container_stack.*`, always)

This keeps the wrapper scripts reusable while making GitHub Actions failures diagnosable from the step list alone.

### Wrapper responsibility split

The start wrappers should only validate prerequisites and start the stack. They should no longer invoke the smoke wrappers internally.

The smoke wrappers remain responsible for endpoint checks and Redis validation. This separation is required so the workflow's `Start container stack` and `Run smoke checks` steps reflect distinct failure modes.

### Node runtime compatibility

Upgrade `actions/checkout` from `v4` to `v5` in the same workflow change. This is directly tied to the observed warning because the `actions/checkout` v5 release notes state that v5 updates the action to use Node 24.

## Acceptance Criteria

Real three-platform smoke coverage means each participating job must do all of the following on its assigned runner:

1. prepare `.env`
2. pass `docker version`
3. pass `docker compose version`
4. on Windows, pass a Docker server platform check that resolves to `linux/amd64`
5. pass `docker compose config`
6. start the Compose stack without chaining smoke verification inside the start wrapper
7. run smoke verification as a separate step that checks:
   - `http://localhost:3000/`
   - `http://localhost:8080/api/health`
   - `http://localhost:8000/health`
   - `http://localhost:8001/health`
   - Redis ping through `docker compose exec -T redis redis-cli ping`
8. always run teardown

For fork pull requests, the acceptance criterion changes: the macOS self-hosted job must not run, and that absence is treated as intentional policy rather than missing coverage.

The `.env` preparation contract is:

- every platform copies `.env.example` to `.env`
- the workflow does not synthesize a separate smoke-only env file
- the workflow does not inject secrets for this smoke path
- the resulting `.env` preparation must stay deterministic across Bash and PowerShell runners

## Files In Scope

- `.github/workflows/container-stack-smoke.yml`
- `scripts/deploy/start_container_stack.sh`
- `scripts/deploy/start_container_stack.ps1`
- `scripts/deploy/smoke_test_container_stack.sh`
- `scripts/deploy/smoke_test_container_stack.ps1`
- `scripts/deploy/stop_container_stack.sh`
- `scripts/deploy/stop_container_stack.ps1`
- `tests/scripts/test_container_stack_contract.py`
- `docs/deployment/containerized.md`

## Out Of Scope

- Reworking `docker-compose.yml`
- Changing service health endpoints
- Adding host-level bootstrap/install logic for Docker
- Modifying backend/frontend application behavior

## Testing

- Add a regression test that locks in the workflow runner strategy by asserting:
  - `ubuntu-24.04` is present
  - `windows-2025` is present
  - the workflow contains `self-hosted`, `macOS`, and `container-smoke`
  - no `ubuntu-latest`, `windows-latest`, or `macos-latest` labels remain
  - the workflow isolates macOS from the hosted matrix by defining a dedicated self-hosted macOS job
- Add a regression test that locks in the action-runtime fix by asserting `actions/checkout@v5` is used
- Add a regression test that locks in the preflight contract by asserting:
  - `Check Docker availability` still contains both `docker version` and `docker compose version`
  - the workflow contains the Windows Docker server platform check for `linux/amd64`
  - the macOS job sets an explicit `timeout-minutes`
- Add a regression test that locks in the trust boundary by asserting the macOS job contains a guard that excludes fork pull requests from self-hosted execution
- Add a regression test that locks in the split between startup and smoke steps by asserting:
  - workflow startup steps call `start_container_stack.sh` or `start_container_stack.ps1`
  - workflow smoke steps call `smoke_test_container_stack.sh` or `smoke_test_container_stack.ps1`
  - the startup wrappers themselves no longer invoke the smoke wrappers internally
- Put the new workflow-YAML assertions in `tests/scripts/test_container_stack_contract.py`, following the existing text-contract style instead of introducing a YAML parser dependency. Use semantic string checks or tolerant multiline regexes rather than formatting-sensitive exact block matches.
- Extend the contract tests so startup wrappers are required to use `docker compose up -d --build` without chaining smoke verification.
- Run `uv run pytest tests/scripts/test_container_stack_contract.py -q` before and after the change.
