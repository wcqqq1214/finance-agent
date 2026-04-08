$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "../..")).Path

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

Push-Location $ProjectRoot
try {
    docker compose down --remove-orphans
}
finally {
    Pop-Location
}
