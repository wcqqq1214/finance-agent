$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "../..")).Path
$EnvFile = Join-Path $ProjectRoot ".env"

function Require-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Error: required command 'docker' is not available."
        exit 1
    }

    try {
        docker compose version | Out-Null
    }
    catch {
        Write-Error "Error: 'docker compose' is not available. Install Docker Desktop or Docker Engine with Compose support."
        exit 1
    }
}

if (-not (Test-Path $EnvFile)) {
    Write-Error "Error: .env is missing. Copy .env.example to .env and add the required keys before starting the container stack."
    exit 1
}

Require-Docker

Push-Location $ProjectRoot
try {
    docker compose up -d --build
    & (Join-Path $ScriptDir "smoke_test_container_stack.ps1")
}
finally {
    Pop-Location
}
