# Rollback Script for LoL Stonks RSS Deployment
# This script automates rollback to the previous Docker image version

param(
    [Parameter(Position=0)]
    [string]$ImageTag = "previous",

    [switch]$Force,
    [switch]$NoWait,
    [int]$HealthCheckPort = 8000
)

$ErrorActionPreference = "Stop"
$ContainerName = "lolstonksrss"
$PreviousImageTag = "$ContainerName`:$ImageTag"
$LogFile = Join-Path $PSScriptRoot "..\logs\rollback-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

# Ensure logs directory exists
$logsDir = Split-Path $LogFile -Parent
if (-not (Test-Path $logsDir)) {
    New-Item -Path $logsDir -ItemType Directory -Force | Out-Null
}

# Function to write to both console and log file
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"

    # Write to console with color
    switch ($Level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "WARN"  { Write-Host $logMessage -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        default { Write-Host $logMessage -ForegroundColor White }
    }

    # Write to log file
    Add-Content -Path $LogFile -Value $logMessage
}

Write-Log "=== LoL Stonks RSS Rollback Script ===" "INFO"
Write-Log "Rollback target: $PreviousImageTag" "INFO"
Write-Log "Container name: $ContainerName" "INFO"
Write-Log ""

# Function to check if command exists
function Test-Command {
    param($Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Check Docker
Write-Log "Checking Docker installation..." "INFO"
if (-not (Test-Command docker)) {
    Write-Log "Error: Docker not found. Please install Docker Desktop for Windows." "ERROR"
    exit 1
}

# Verify Docker is running
try {
    docker ps > $null 2>&1
    Write-Log "Docker is running" "SUCCESS"
} catch {
    Write-Log "Error: Docker is not running. Please start Docker Desktop." "ERROR"
    exit 1
}

# Check if previous image exists
Write-Log "Checking for previous image: $PreviousImageTag" "INFO"
$previousImage = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String -Pattern "^$PreviousImageTag$"

if (-not $previousImage) {
    Write-Log "Error: Previous image '$PreviousImageTag' not found locally." "ERROR"
    Write-Log "Available images:" "WARN"
    docker images --format "  {{.Repository}}:{{.Tag}}" | Select-String -Pattern "^$ContainerName"

    if (-not $Force) {
        Write-Log ""
        Write-Log "No previous image found for rollback. Aborting." "ERROR"
        Write-Log "Use -Force to attempt rollback anyway (will try to pull from registry if available)." "WARN"
        exit 1
    } else {
        Write-Log "Force mode enabled: Attempting to continue..." "WARN"
    }
}

# Get current container state
Write-Log "Checking current container state..." "INFO"
$currentContainer = docker ps --filter "name=$ContainerName" --format "{{.Names}}:{{.Status}}" | Select-String -Pattern "^$ContainerName"

if ($currentContainer) {
    Write-Log "Current container is running: $currentContainer" "INFO"

    # Get current image
    $currentImage = docker inspect $ContainerName --format '{{.Config.Image}}' 2>$null
    Write-Log "Current image: $currentImage" "INFO"
} else {
    Write-Log "No container named '$ContainerName' is currently running." "WARN"
}

# Confirm rollback unless forced
if (-not $Force) {
    Write-Log ""
    Write-Log "This will stop the current container and start the previous version." "WARN"
    $confirmation = Read-Host "Do you want to proceed? (yes/no)"

    if ($confirmation -ne "yes" -and $confirmation -ne "y") {
        Write-Log "Rollback cancelled by user." "WARN"
        exit 0
    }
}

# Stop current container
Write-Log ""
Write-Log "Stopping current container..." "INFO"
try {
    docker stop $ContainerName 2>$null | Out-Null
    Write-Log "Container stopped successfully" "SUCCESS"
} catch {
    Write-Log "Warning: Could not stop container (may not be running)" "WARN"
}

# Remove current container
Write-Log "Removing current container..." "INFO"
try {
    docker rm $ContainerName 2>$null | Out-Null
    Write-Log "Container removed successfully" "SUCCESS"
} catch {
    Write-Log "Warning: Could not remove container" "WARN"
}

# Tag previous image as latest if it exists
if ($previousImage) {
    Write-Log "Tagging previous image as latest..." "INFO"
    try {
        docker tag $PreviousImageTag "$ContainerName`:latest"
        Write-Log "Image tagged successfully" "SUCCESS"
    } catch {
        Write-Log "Warning: Could not tag image" "WARN"
    }
}

# Start container with previous image
Write-Log ""
Write-Log "Starting container with previous image..." "INFO"

# Determine docker compose command
$composeCmd = "docker compose"
if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $composeCmd = "docker-compose"
}

# Check if docker-compose.yml exists
$composeFile = Join-Path $PSScriptRoot "..\docker-compose.yml"

if (Test-Path $composeFile) {
    Write-Log "Using docker-compose to start container..." "INFO"
    Push-Location (Split-Path $composeFile -Parent)

    try {
        # Pull latest (which is now the previous version)
        Write-Log "Pulling image: $ContainerName`:latest" "INFO"
        docker pull $ContainerName`:latest 2>$null | Out-Null

        # Start with docker-compose
        Invoke-Expression "$composeCmd up -d"
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to start container with docker-compose"
        }
        Write-Log "Container started with docker-compose" "SUCCESS"
    } catch {
        Write-Log "Error: Failed to start container." "ERROR"
        Write-Log $_.Exception.Message "ERROR"
        Pop-Location
        exit 1
    }

    Pop-Location
} else {
    Write-Log "Using docker run to start container..." "INFO"

    # Build docker run command
    $dataDir = Join-Path $PSScriptRoot "..\data"

    $dockerRunArgs = @(
        "run", "-d",
        "--name", $ContainerName,
        "--restart", "unless-stopped",
        "-p", "$HealthCheckPort`:8000",
        "-v", "$dataDir`:/app/data",
        "-e", "DATABASE_PATH=/app/data/articles.db",
        "-e", "HOST=0.0.0.0",
        "-e", "PORT=8000",
        "$ContainerName`:latest"
    )

    try {
        & docker $dockerRunArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to start container"
        }
        Write-Log "Container started successfully" "SUCCESS"
    } catch {
        Write-Log "Error: Failed to start container." "ERROR"
        Write-Log $_.Exception.Message "ERROR"
        exit 1
    }
}

# Health check
if (-not $NoWait) {
    Write-Log ""
    Write-Log "Waiting for service to be healthy..." "INFO"

    $maxAttempts = 30
    $attempt = 0
    $healthy = $false

    while ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 2
        $attempt++

        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$HealthCheckPort/health" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                $healthData = $response.Content | ConvertFrom-Json
                if ($healthData.status -eq "healthy") {
                    $healthy = $true
                    break
                }
            }
        } catch {
            # Service not ready yet, continue waiting
        }

        Write-Log "  Attempt $attempt/$maxAttempts..." "INFO"
    }

    if ($healthy) {
        Write-Log ""
        Write-Log "=== Rollback Successful! ===" "SUCCESS"
        Write-Log ""
        Write-Log "Service is running at:" "INFO"
        Write-Log "  Health Check:  http://localhost:$HealthCheckPort/health" "SUCCESS"
        Write-Log "  RSS Feed:      http://localhost:$HealthCheckPort/feed.xml" "SUCCESS"
        Write-Log ""

        # Log rollback event
        $rollbackEvent = @{
            timestamp = Get-Date -Format "o"
            event = "rollback"
            from_image = if ($currentImage) { $currentImage } else { "unknown" }
            to_image = $PreviousImageTag
            status = "success"
            health_check = "passed"
        }

        Write-Log "Rollback event logged to: $LogFile" "INFO"

    } else {
        Write-Log ""
        Write-Log "=== Rollback Completed with Warnings ===" "WARN"
        Write-Log "Container started but health check failed." "WARN"
        Write-Log ""
        Write-Log "The service may still be initializing." "WARN"
        Write-Log "Check logs with: docker logs -f $ContainerName" "WARN"
        Write-Log ""

        # Log rollback event with warning
        $rollbackEvent = @{
            timestamp = Get-Date -Format "o"
            event = "rollback"
            from_image = if ($currentImage) { $currentImage } else { "unknown" }
            to_image = $PreviousImageTag
            status = "warning"
            health_check = "failed"
        }

        exit 1
    }
} else {
    Write-Log ""
    Write-Log "=== Rollback Initiated ===" "SUCCESS"
    Write-Log "Container started without health check (--NoWait flag set)." "WARN"
    Write-Log ""
    Write-Log "Check status manually:" "INFO"
    Write-Log "  docker logs -f $ContainerName" "INFO"
}

Write-Log "Rollback log saved to: $LogFile" "INFO"
exit 0
