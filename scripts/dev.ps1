[CmdletBinding()]
param(
    [ValidateSet("bootstrap", "up", "down", "restart", "build", "test", "status", "logs", "config", "health")]
    [string]$Command = "bootstrap",
    [string]$EnvFile = ".env.local",
    [switch]$Follow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) {
    $EnvFile
} else {
    Join-Path $repoRoot $EnvFile
}
$script:DockerCommand = $null

function Resolve-DockerCommand {
    $pathCommand = Get-Command docker -ErrorAction SilentlyContinue
    if ($pathCommand) {
        return $pathCommand.Source
    }

    $candidates = @()
    if ($env:LOCALAPPDATA) {
        $candidates += Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"
    }
    if ($env:ProgramFiles) {
        $candidates += Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe"
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }

    return $null
}

function New-UrlSafeSecret {
    $bytes = New-Object byte[] 32
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    } finally {
        $generator.Dispose()
    }

    return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function Initialize-EnvironmentFile {
    if (Test-Path -LiteralPath $envPath) {
        return
    }

    $examplePath = Join-Path $repoRoot ".env.example"
    if (-not (Test-Path -LiteralPath $examplePath)) {
        throw "Missing environment template: $examplePath"
    }

    $content = [System.IO.File]::ReadAllText($examplePath)
    foreach ($placeholder in @(
        "CHANGE_ME_POSTGRES_PASSWORD",
        "CHANGE_ME_NEO4J_PASSWORD",
        "CHANGE_ME_REDIS_PASSWORD"
    )) {
        $content = $content.Replace($placeholder, (New-UrlSafeSecret))
    }

    $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($envPath, $content, $utf8WithoutBom)
    Write-Host "Created $envPath with random local data-service credentials."
}

function Assert-EnvironmentFile {
    if (-not (Test-Path -LiteralPath $envPath)) {
        throw "Missing $envPath. Run: pwsh ./scripts/dev.ps1 bootstrap"
    }

    $content = [System.IO.File]::ReadAllText($envPath)
    if ($content.Contains("CHANGE_ME_")) {
        throw "$envPath still contains CHANGE_ME placeholders. Run bootstrap with a new env file or replace them manually."
    }

    foreach ($requiredName in @("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "NEO4J_USER", "NEO4J_PASSWORD", "REDIS_PASSWORD")) {
        if ($content -notmatch "(?m)^$([regex]::Escape($requiredName))=.+$") {
            throw "$envPath is missing a non-empty $requiredName entry."
        }
    }
}

function Assert-Docker {
    $script:DockerCommand = Resolve-DockerCommand
    if (-not $script:DockerCommand) {
        throw "Docker CLI was not found. Install and start Docker Desktop, then retry."
    }

    & $script:DockerCommand compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose v2 is required."
    }

    & $script:DockerCommand info --format "{{.ServerVersion}}" *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is installed, but its Linux container engine is not running. Start Docker Desktop, then retry."
    }
}

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    & $script:DockerCommand compose --project-directory $repoRoot --env-file $envPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed with exit code $LASTEXITCODE."
    }
}

function Invoke-DockerBuild {
    param([string]$Dockerfile, [string]$Target, [string]$Tag)

    & $script:DockerCommand build --file (Join-Path $repoRoot $Dockerfile) --target $Target --tag $Tag $repoRoot
    if ($LASTEXITCODE -ne 0) {
        throw "docker build failed for $Dockerfile with exit code $LASTEXITCODE."
    }
}

Set-Location $repoRoot
Assert-Docker

switch ($Command) {
    "bootstrap" {
        Initialize-EnvironmentFile
        Assert-EnvironmentFile
        Invoke-Compose config --quiet
        Invoke-Compose up --detach --build --wait --wait-timeout 240
        Write-Host "RegOntology is ready: http://127.0.0.1:8080"
        Write-Host "API health: http://127.0.0.1:8000/api/v1/health"
    }
    "up" {
        Assert-EnvironmentFile
        Invoke-Compose up --detach --build --wait --wait-timeout 240
    }
    "down" {
        Assert-EnvironmentFile
        Invoke-Compose down --remove-orphans
    }
    "restart" {
        Assert-EnvironmentFile
        Invoke-Compose restart
    }
    "build" {
        Assert-EnvironmentFile
        Invoke-Compose build --pull
    }
    "test" {
        Invoke-DockerBuild "deploy/docker/backend.Dockerfile" "test" "regontology-api:test"
        Invoke-DockerBuild "deploy/docker/frontend.Dockerfile" "test" "regontology-web:test"
    }
    "status" {
        Assert-EnvironmentFile
        Invoke-Compose ps
    }
    "logs" {
        Assert-EnvironmentFile
        if ($Follow) {
            Invoke-Compose logs --follow --tail 200
        } else {
            Invoke-Compose logs --tail 200
        }
    }
    "config" {
        Assert-EnvironmentFile
        Invoke-Compose config --quiet
        Write-Host "Compose configuration is valid."
    }
    "health" {
        $webResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8080/healthz" -TimeoutSec 5 -UseBasicParsing
        $apiResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 5 -UseBasicParsing
        Write-Host "web=$($webResponse.StatusCode) api=$($apiResponse.StatusCode)"
    }
}
