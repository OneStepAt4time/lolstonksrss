# Enhanced Deployment Script for LoL Stonks RSS
# Supports blue-green deployment strategy with automated rollback

param(
    [string]$ImageTag = "latest",
    [string]$Environment = "blue",  # "blue" or "green"
    [switch]$SkipBuild,
    [switch]$NoBrowser,
    [switch]$SkipHealthCheck,
    [int]$Port = 8000,
    [string]$ContainerName = "lolstonksrss"
)

$ErrorActionPreference = "Stop"

# Color output functions
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { Write-ColorOutput @args -Color "Green" }
function Write-Error { Write-ColorOutput @args -Color "Red" }
function Write-Warning { Write-ColorOutput @args -Color "Yellow" }
function Write-Info { Write-ColorOutput @args -Color "Cyan" }

Write-Success "=== LoL Stonks RSS Enhanced Deployment ==="
Write-Info "Environment: $Environment"
Write-Info "Image Tag: $ImageTag"
Write-Host ""

# Configuration
$BluePort = 8000
$GreenPort = 8001
$CurrentPort = if ($Environment -eq "blue") { $BluePort } else { $GreenPort }
$FullImageName = "lolstonksrss:$ImageTag"
$LogFile = Join-Path $PSScriptRoot "..\logs\deploy-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

# Ensure logs directory exists
$logsDir = Split-Path $LogFile -Parent
if (-not (Test-Path $logsDir)) {
    New-Item -Path $logsDir -ItemType Directory -Force | Out-Null
}

# Logging function
function Write-DeploymentLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] $Message"
    Add-Content -Path $LogFile -Value $logEntry
    Write-Host $logEntry
}

Write-DeploymentLog "Starting deployment to $Environment environment"

# Function to check if command exists
function Test-Command {
    param($Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
if (-not (Test-Command docker)) {
    Write-Error "Error: Docker not found. Please install Docker Desktop for Windows."
    Write-Info "Download from: https://www.docker.com/products/docker-desktop/"
    exit 1
}

# Verify Docker is running
try {
    docker ps > $null 2>&1
    Write-Success "  Docker is running"
} catch {
    Write-Error "Error: Docker is not running. Please start Docker Desktop."
    exit 1
}

# Check Docker Compose
$composeCmd = "docker compose"
if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $composeCmd = "docker-compose"
    Write-Success "  Using docker-compose"
} else {
    Write-Success "  Using docker compose"
}

# Create data directory
Write-Host ""
Write-DeploymentLog "Creating data directory..."
$dataDir = Join-Path $PSScriptRoot "..\data"
if (-not (Test-Path $dataDir)) {
    New-Item -Path $dataDir -ItemType Directory -Force | Out-Null
    Write-Success "  Created: $dataDir"
} else {
    Write-Success "  Already exists: $dataDir"
}

# Backup current version before deployment
Write-Host ""
Write-DeploymentLog "Backing up current version..."
$currentImage = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String -Pattern "^lolstonksrss:latest$"
if ($currentImage) {
    try {
        docker tag lolstonksrss:latest lolstonksrss:previous 2>$null
        Write-Success "  Current version tagged as :previous"
        Write-DeploymentLog "Backed up current image as lolstonksrss:previous"
    } catch {
        Write-Warning "  Could not tag previous version (may not exist yet)"
    }
}

# Build image if needed
if (-not $SkipBuild) {
    Write-Host ""
    Write-DeploymentLog "Building Docker image..."
    Push-Location (Join-Path $PSScriptRoot "..")
    try {
        docker build -t $FullImageName .
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build failed"
        }

        # Tag as latest
        docker tag $FullImageName lolstonksrss:latest
        Write-Success "  Build successful: $FullImageName"
        Write-DeploymentLog "Built image: $FullImageName"
    } catch {
        Write-Error "Error: Docker build failed."
        Write-Error $_.Exception.Message
        Pop-Location
        exit 1
    }
    Pop-Location
} else {
    Write-Host ""
    Write-Info "Skipping build (--SkipBuild flag set)"
}

# Blue-Green Deployment Strategy
Write-Host ""
Write-Info "=== Blue-Green Deployment Strategy ==="

# Check which environment is currently active
$BlueRunning = docker ps --filter "name=lolstonksrss-blue" --format "{{.Names}}" | Select-String -Pattern "lolstonksrss-blue"
$GreenRunning = docker ps --filter "name=lolstonksrss-green" --format "{{.Names}}" | Select-String -Pattern "lolstonksrss-green"

if ($BlueRunning) {
    Write-Info "Current active: BLUE environment"
    $ActiveEnvironment = "blue"
} elseif ($GreenRunning) {
    Write-Info "Current active: GREEN environment"
    $ActiveEnvironment = "green"
} else {
    Write-Warning "No active environment found. Will deploy to $Environment"
    $ActiveEnvironment = "none"
}

# Deploy to specified environment
$TargetContainerName = "$ContainerName-$Environment"
$TargetPort = if ($Environment -eq "blue") { $BluePort } else { $GreenPort }

Write-Host ""
Write-DeploymentLog "Deploying to $TargetContainerName on port $TargetPort"

# Stop existing container in target environment
Write-Info "Checking for existing container in $Environment environment..."
$existingContainer = docker ps -a --filter "name=$TargetContainerName" --format "{{.Names}}"
if ($existingContainer) {
    Write-Warning "  Stopping existing container: $TargetContainerName"
    docker stop $TargetContainerName 2>$null | Out-Null
    docker rm $TargetContainerName 2>$null | Out-Null
    Write-Success "  Removed existing container"
}

# Start new container in target environment
Write-Host ""
Write-DeploymentLog "Starting container: $TargetContainerName"

# Build docker run command
$dockerRunArgs = @(
    "run", "-d",
    "--name", $TargetContainerName,
    "--restart", "unless-stopped",
    "-p", "$TargetPort`:8000",
    "-v", "$(Resolve-Path $dataDir)`:/app/data",
    "-e", "DATABASE_PATH=/app/data/articles.db",
    "-e", "HOST=0.0.0.0",
    "-e", "PORT=8000",
    "-e", "LOG_LEVEL=INFO",
    "-e", "BASE_URL=http://localhost:$TargetPort",
    "-e", "SUPPORTED_LOCALES=en-us,it-it",
    "--label", "environment=$Environment",
    "--label", "deployed_at=$(Get-Date -Format 'o')",
    "lolstonksrss:latest"
)

try {
    & docker $dockerRunArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start container"
    }
    Write-Success "  Container started: $TargetContainerName"
    Write-DeploymentLog "Started container: $TargetContainerName (port $TargetPort)"
} catch {
    Write-Error "Error: Failed to start container."
    Write-Error $_.Exception.Message
    exit 1
}

# Health Check
if (-not $SkipHealthCheck) {
    Write-Host ""
    Write-DeploymentLog "Waiting for service health check..."
    $maxAttempts = 30
    $attempt = 0
    $healthy = $false

    while ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 2
        $attempt++

        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$TargetPort/health" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                $healthData = $response.Content | ConvertFrom-Json
                if ($healthData.status -eq "healthy") {
                    $healthy = $true
                    break
                }
            }
        } catch {
            # Service not ready yet
        }

        Write-Host "  Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
    }

    if ($healthy) {
        Write-Success "=== Deployment Successful! ==="
        Write-Host ""
        Write-Info "Service is running at:"
        Write-Host "  Health Check:  http://localhost:$TargetPort/health" -ForegroundColor White
        Write-Host "  RSS Feed:      http://localhost:$TargetPort/feed.xml" -ForegroundColor White
        Write-Host "  API Docs:      http://localhost:$TargetPort/docs" -ForegroundColor White
        Write-Host ""
        Write-Info "Available feeds:"
        Write-Host "  English:       http://localhost:$TargetPort/feeds/en-us.xml" -ForegroundColor White
        Write-Host "  Italian:       http://localhost:$TargetPort/feeds/it-it.xml" -ForegroundColor White
        Write-Host ""

        # Additional verification
        Write-Info "Verifying feed endpoints..."
        try {
            $feedResponse = Invoke-WebRequest -Uri "http://localhost:$TargetPort/feed.xml" -UseBasicParsing -TimeoutSec 5
            if ($feedResponse.StatusCode -eq 200) {
                Write-Success "  Main feed OK"
            }
        } catch {
            Write-Warning "  Main feed check failed"
        }

        try {
            $enFeedResponse = Invoke-WebRequest -Uri "http://localhost:$TargetPort/feeds/en-us.xml" -UseBasicParsing -TimeoutSec 5
            if ($enFeedResponse.StatusCode -eq 200) {
                Write-Success "  English feed OK"
            }
        } catch {
            Write-Warning "  English feed check failed"
        }

        try {
            $itFeedResponse = Invoke-WebRequest -Uri "http://localhost:$TargetPort/feeds/it-it.xml" -UseBasicParsing -TimeoutSec 5
            if ($itFeedResponse.StatusCode -eq 200) {
                Write-Success "  Italian feed OK"
            }
        } catch {
            Write-Warning "  Italian feed check failed"
        }

        Write-Host ""
        Write-Info "Deployment summary:"
        Write-Host "  Environment:  $Environment" -ForegroundColor White
        Write-Host "  Container:    $TargetContainerName" -ForegroundColor White
        Write-Host "  Port:         $TargetPort" -ForegroundColor White
        Write-Host "  Image:        $FullImageName" -ForegroundColor White
        Write-Host ""

        # Log deployment event
        $deploymentEvent = @{
            timestamp = Get-Date -Format "o"
            environment = $Environment
            container = $TargetContainerName
            port = $TargetPort
            image = $FullImageName
            status = "success"
            health_check = "passed"
        }

        Write-DeploymentLog "Deployment successful: $($deploymentEvent | ConvertTo-Json)"

        # Open browser if requested
        if (-not $NoBrowser) {
            Write-Info "Opening browser..."
            Start-Sleep -Seconds 1
            Start-Process "http://localhost:$TargetPort/docs"
        }

        # Traffic switching instructions
        if ($ActiveEnvironment -ne "none" -and $ActiveEnvironment -ne $Environment) {
            Write-Host ""
            Write-Info "=== Traffic Switch ==="
            Write-Warning "New version deployed to $Environment environment"
            Write-Info "To switch traffic to $Environment:"
            Write-Host "  1. Verify $Environment environment is working correctly" -ForegroundColor White
            Write-Host "  2. Update your reverse proxy/load balancer to point to port $TargetPort" -ForegroundColor White
            Write-Host "  3. Monitor for issues" -ForegroundColor White
            Write-Host "  4. Stop old environment: docker stop $ContainerName-$ActiveEnvironment" -ForegroundColor White
            Write-Host ""
        }

    } else {
        Write-Host ""
        Write-Error "=== Deployment Failed - Health Check ==="
        Write-Warning "Container started but health check failed after $maxAttempts attempts"
        Write-Host ""

        # Automated rollback suggestion
        Write-Warning "Suggested actions:"
        Write-Host "  1. Check logs: docker logs $TargetContainerName" -ForegroundColor White
        Write-Host "  2. Verify configuration" -ForegroundColor White
        Write-Host "  3. Rollback to previous version:" -ForegroundColor White
        Write-Host "     .\scripts\rollback.ps1" -ForegroundColor Cyan
        Write-Host ""

        Write-DeploymentLog "Deployment failed: health check timeout"

        # Offer automatic rollback
        $rollbackChoice = Read-Host "Do you want to rollback to previous version? (yes/no)"
        if ($rollbackChoice -eq "yes" -or $rollbackChoice -eq "y") {
            Write-Info "Initiating rollback..."
            & "$PSScriptRoot\rollback.ps1" -Force -NoWait
        }

        exit 1
    }
} else {
    Write-Host ""
    Write-Success "=== Deployment Initiated ==="
    Write-Warning "Health check skipped (--SkipHealthCheck flag set)"
    Write-Host ""
    Write-Info "Container: $TargetContainerName"
    Write-Info "Port: $TargetPort"
    Write-Host ""
    Write-Info "Manual health check:"
    Write-Host "  curl http://localhost:$TargetPort/health" -ForegroundColor White
}

Write-Host ""
Write-Info "Management commands:"
Write-Host "  View logs:     docker logs -f $TargetContainerName" -ForegroundColor White
Write-Host "  Stop:          docker stop $TargetContainerName" -ForegroundColor White
Write-Host "  Restart:       docker restart $TargetContainerName" -ForegroundColor White
Write-Host ""
Write-Info "Deployment log: $LogFile"
Write-Host ""

exit 0
