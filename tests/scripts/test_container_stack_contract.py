"""Contract tests for the repository's container deployment surface."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _deploy_script(name: str) -> Path:
    return REPO_ROOT / "scripts" / "deploy" / name


def _workflow_job_block(workflow: str, job_name: str) -> str:
    """Return one top-level workflow job block by job id."""
    match = re.search(
        rf"(?ms)^  {re.escape(job_name)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
        workflow,
    )
    assert match is not None
    return match.group("body")


def test_docker_compose_defines_full_container_stack() -> None:
    """Compose file should define the full five-service deployment topology."""
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    for service in (
        "redis:",
        "market-data-mcp:",
        "news-search-mcp:",
        "api:",
        "frontend:",
    ):
        assert service in compose

    assert "redis_data:" in compose
    assert "redis://redis:6379/0" in compose
    assert "http://market-data-mcp:8000/mcp" in compose
    assert "http://news-search-mcp:8001/mcp" in compose
    assert "NEXT_PUBLIC_API_URL" in compose
    assert "http://localhost:8080" in compose


def test_backend_dockerfile_exposes_named_python_service_targets() -> None:
    """Backend Dockerfile should expose dedicated targets for each Python service."""
    backend_dockerfile = REPO_ROOT / "docker" / "backend.Dockerfile"
    assert backend_dockerfile.exists()

    dockerfile = backend_dockerfile.read_text(encoding="utf-8")
    assert "ghcr.io/astral-sh/uv" in dockerfile
    assert "FROM base AS api" in dockerfile
    assert "FROM base AS market-data-mcp" in dockerfile
    assert "FROM base AS news-search-mcp" in dockerfile


def test_frontend_dockerfile_builds_and_runs_production_app() -> None:
    """Frontend Dockerfile should install with pnpm and start the production server."""
    frontend_dockerfile = REPO_ROOT / "docker" / "frontend.Dockerfile"
    assert frontend_dockerfile.exists()

    dockerfile = frontend_dockerfile.read_text(encoding="utf-8")
    assert "corepack" in dockerfile
    assert "pnpm install" in dockerfile
    assert "pnpm build" in dockerfile
    assert "pnpm" in dockerfile
    assert "start" in dockerfile
    assert "--hostname" in dockerfile
    assert "0.0.0.0" in dockerfile
    assert "--port" in dockerfile
    assert "3000" in dockerfile


def test_wrapper_scripts_exist_for_shell_and_powershell() -> None:
    """Deployment wrappers should exist for Unix shells and PowerShell."""
    for name in (
        "start_container_stack.sh",
        "stop_container_stack.sh",
        "smoke_test_container_stack.sh",
        "start_container_stack.ps1",
        "stop_container_stack.ps1",
        "smoke_test_container_stack.ps1",
    ):
        assert _deploy_script(name).exists()


def test_start_wrapper_requires_dotenv_and_uses_compose_up() -> None:
    """Startup wrappers should enforce .env presence and use compose up."""
    shell_script = _deploy_script("start_container_stack.sh").read_text(encoding="utf-8")
    powershell_script = _deploy_script("start_container_stack.ps1").read_text(encoding="utf-8")

    assert ".env" in shell_script
    assert "docker compose up -d --build" in shell_script
    assert ".env" in powershell_script
    assert "docker compose up -d --build" in powershell_script


def test_start_wrappers_do_not_run_smoke_checks() -> None:
    """Startup wrappers should not invoke the smoke tests directly."""
    shell_script = _deploy_script("start_container_stack.sh").read_text(encoding="utf-8")
    powershell_script = _deploy_script("start_container_stack.ps1").read_text(encoding="utf-8")

    assert "smoke_test_container_stack.sh" not in shell_script
    assert "smoke_test_container_stack.ps1" not in powershell_script


def test_stop_wrapper_uses_compose_down() -> None:
    """Stop wrappers should tear the stack down with docker compose down."""
    shell_script = _deploy_script("stop_container_stack.sh").read_text(encoding="utf-8")
    powershell_script = _deploy_script("stop_container_stack.ps1").read_text(encoding="utf-8")

    assert "docker compose down" in shell_script
    assert "docker compose down" in powershell_script


def test_smoke_wrapper_checks_documented_endpoints() -> None:
    """Smoke wrappers should probe the documented frontend, API, and MCP endpoints."""
    shell_script = _deploy_script("smoke_test_container_stack.sh").read_text(encoding="utf-8")
    powershell_script = _deploy_script("smoke_test_container_stack.ps1").read_text(encoding="utf-8")

    for endpoint in (
        "http://localhost:3000/",
        "http://localhost:8080/api/health",
        "http://localhost:8000/health",
        "http://localhost:8001/health",
    ):
        assert endpoint in shell_script
        assert endpoint in powershell_script


def test_wrapper_scripts_do_not_install_host_dependencies() -> None:
    """Wrappers should orchestrate compose only, not mutate the host environment."""
    forbidden = (
        "brew install",
        "apt-get install",
        "winget install",
        "curl https://astral.sh",
        "curl -LsSf",
    )

    for name in (
        "start_container_stack.sh",
        "stop_container_stack.sh",
        "smoke_test_container_stack.sh",
        "start_container_stack.ps1",
        "stop_container_stack.ps1",
        "smoke_test_container_stack.ps1",
    ):
        script = _deploy_script(name).read_text(encoding="utf-8")
        for forbidden_snippet in forbidden:
            assert forbidden_snippet not in script


def test_start_wrapper_dotenv_fail_fast() -> None:
    """Shell startup wrapper should fail fast with a clear message when .env is missing."""
    temp_root = REPO_ROOT / ".tmp-test-start-wrapper-dotenv-fail-fast"
    if temp_root.exists():
        shutil.rmtree(temp_root)
    script = temp_root / "scripts" / "deploy" / "start_container_stack.sh"
    env = os.environ.copy()
    script.parent.mkdir(parents=True)
    script.write_text(
        _deploy_script("start_container_stack.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    try:
        result = subprocess.run(
            ["bash", str(script)],
            cwd=temp_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    assert result.returncode != 0
    combined_output = f"{result.stdout}\n{result.stderr}"
    assert ".env" in combined_output
    assert ".env.example" in combined_output


def test_container_deployment_doc_mentions_entrypoints_and_env_copy() -> None:
    """Deployment doc should cover wrapper and raw compose entrypoints plus .env setup."""
    deployment_doc = (REPO_ROOT / "docs" / "deployment" / "containerized.md").read_text(
        encoding="utf-8"
    )

    assert "docker compose up -d --build" in deployment_doc
    assert "start_container_stack.sh" in deployment_doc
    assert "start_container_stack.ps1" in deployment_doc
    assert ".env.example" in deployment_doc
    assert ".env" in deployment_doc


def test_container_deployment_doc_mentions_memory_guidance_and_native_boundary() -> None:
    """Deployment doc should document Docker memory guidance and separate native development."""
    deployment_doc = (REPO_ROOT / "docs" / "deployment" / "containerized.md").read_text(
        encoding="utf-8"
    )

    assert "4 GB" in deployment_doc
    assert "8 GB" in deployment_doc
    assert "Docker Desktop" in deployment_doc or "OrbStack" in deployment_doc
    assert "native development" in deployment_doc
    assert "scripts/startup/" in deployment_doc


def test_env_example_documents_compose_managed_overrides() -> None:
    """Example env file should distinguish local defaults from compose-managed service URLs."""
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "Compose overrides this inside containers" in env_example
    assert "redis://redis:6379/0" in env_example
    assert "http://market-data-mcp:8000/mcp" in env_example
    assert "http://news-search-mcp:8001/mcp" in env_example


def test_readme_docs_point_to_container_guide_and_keep_native_dev_separate() -> None:
    """Top-level READMEs should route deployment to the dedicated container guide."""
    for path in (
        REPO_ROOT / "README.md",
        REPO_ROOT / "README.zh-CN.md",
        REPO_ROOT / "README.ja.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "docs/deployment/containerized.md" in text
        assert ".env.example" in text
        assert "scripts/startup/" in text


def test_container_smoke_workflow_pins_supported_runners_and_isolates_macos() -> None:
    """Smoke workflow should pin hosted runners and isolate macOS to self-hosted."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "container-stack-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert "ubuntu-24.04" in workflow
    assert "windows-2025" in workflow
    for runner in ("ubuntu-latest", "windows-latest", "macos-latest"):
        assert runner not in workflow

    matrix_job = _workflow_job_block(workflow, "smoke-hosted")
    assert "ubuntu-24.04" in matrix_job
    assert "windows-2025" in matrix_job
    assert "macos" not in matrix_job.lower()

    mac_job = _workflow_job_block(workflow, "smoke-macos")
    assert "self-hosted" in mac_job
    assert "macOS" in mac_job
    assert "container-smoke" in mac_job
    assert "timeout-minutes: 30" in mac_job
    assert re.search(
        r"github\.event_name\s*!=\s*'pull_request'\s*\|\|\s*github\.event\.pull_request\.head\.repo\.full_name\s*==\s*github\.repository",
        mac_job,
    )


def test_container_smoke_workflow_preserves_pull_request_trigger_only() -> None:
    """Workflow should keep pull_request and avoid pull_request_target."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "container-stack-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert "pull_request:" in workflow
    assert "pull_request_target" not in workflow


def test_container_smoke_workflow_uses_checkout_v5() -> None:
    """Workflow should upgrade checkout to v5."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "container-stack-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert "actions/checkout@v5" in workflow


def test_container_smoke_workflow_keeps_docker_availability_check() -> None:
    """Docker availability step must check both docker and docker compose."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "container-stack-smoke.yml").read_text(
        encoding="utf-8"
    )

    match = re.search(
        r"-\s*name:\s*Check Docker availability\s*\n(?P<body>(?:^[ \t]+.*\n)+)",
        workflow,
        flags=re.MULTILINE,
    )
    assert match
    body = match.group("body")
    assert "docker version" in body
    assert "docker compose version" in body


def test_container_smoke_workflow_windows_server_platform_check() -> None:
    """Windows job should enforce Linux/amd64 Docker server platform."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "container-stack-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert "docker version --format '{{.Server.Os}}/{{.Server.Arch}}'" in workflow
    assert "linux/amd64" in workflow


def test_container_smoke_workflow_does_not_use_matrix_context_for_step_shells() -> None:
    """Step shells should be explicit because matrix context is rejected in that field."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "container-stack-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert re.search(r"^\s*shell:\s*\$\{\{\s*matrix\.", workflow, flags=re.MULTILINE) is None


def test_container_smoke_workflow_prepares_env_and_uses_wrappers() -> None:
    """Workflow should create .env and call the shell/PowerShell wrapper entrypoints."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "container-stack-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert ".env.example" in workflow
    assert ".env" in workflow
    assert "scripts/deploy/start_container_stack.sh" in workflow
    assert "scripts/deploy/smoke_test_container_stack.sh" in workflow
    assert "scripts/deploy/stop_container_stack.sh" in workflow
    assert "scripts/deploy/start_container_stack.ps1" in workflow
    assert "scripts/deploy/smoke_test_container_stack.ps1" in workflow
    assert "scripts/deploy/stop_container_stack.ps1" in workflow

    assert "cp .env.example .env" in workflow
    assert "Copy-Item .env.example .env -Force" in workflow


def test_container_smoke_workflow_invokes_correct_wrappers_per_phase() -> None:
    """Workflow should call the start and smoke wrapper explicitly in distinct steps."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "container-stack-smoke.yml").read_text(
        encoding="utf-8"
    )

    start_match = re.search(
        r"-\s*name:\s*Start container stack\s*\n(?P<body>(?:^[ \t]+.*\n)+)",
        workflow,
        flags=re.MULTILINE,
    )
    smoke_match = re.search(
        r"-\s*name:\s*Run smoke checks\s*\n(?P<body>(?:^[ \t]+.*\n)+)",
        workflow,
        flags=re.MULTILINE,
    )
    assert start_match
    assert smoke_match
    assert "start_container_stack" in start_match.group("body")
    assert "smoke_test_container_stack" in smoke_match.group("body")


def test_container_smoke_workflow_runs_compose_resolution_and_cleanup() -> None:
    """Workflow should resolve compose config and always tear the stack down."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "container-stack-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert "docker compose config" in workflow
    teardown_match = re.search(
        r"-\s*name:\s*Tear down container stack\s*\n(?P<body>(?:^[ \t]+.*\n)+)",
        workflow,
        flags=re.MULTILINE,
    )
    assert teardown_match
    teardown_body = teardown_match.group("body")
    assert "if: always()" in teardown_body
    assert "stop_container_stack" in teardown_body
