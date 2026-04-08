$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "../..")).Path

function Wait-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$MaxAttempts = 60,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                Write-Host "Healthy: $Url"
                return
            }
        }
        catch {
        }

        Start-Sleep -Seconds $DelaySeconds
    }

    throw "Timed out waiting for $Url"
}

function Wait-RedisHealth {
    param(
        [int]$MaxAttempts = 30,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            $output = docker compose exec -T redis redis-cli ping 2>$null
            if ($LASTEXITCODE -eq 0 -and $output -match "PONG") {
                Write-Host "Healthy: redis://localhost:6379"
                return
            }
        }
        catch {
        }

        Start-Sleep -Seconds $DelaySeconds
    }

    throw "Timed out waiting for Redis health."
}

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
    foreach ($endpoint in @(
        "http://localhost:3000/",
        "http://localhost:8080/api/health",
        "http://localhost:8000/health",
        "http://localhost:8001/health"
    )) {
        Wait-HttpEndpoint -Url $endpoint
    }

    Wait-RedisHealth
    docker compose ps
}
finally {
    Pop-Location
}
