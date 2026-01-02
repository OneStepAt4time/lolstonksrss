# Automated Deployment Guide

Complete guide for automated deployment of LoL Stonks RSS to Windows Server using GitHub Actions.

## Overview

The deployment system uses GitHub Actions to automatically build, test, and deploy the application to a Windows Server running Docker Desktop. The deployment includes:

- Automated Docker image building and pushing to GitHub Container Registry (GHCR)
- SSH-based remote deployment to Windows Server
- Automated health checks and verification
- Automatic rollback on deployment failure
- Blue-green deployment support

## Architecture

```
GitHub Push/Release
    ↓
GitHub Actions CI/CD
    ↓
Build Docker Image
    ↓
Push to GHCR
    ↓
SSH to Windows Server
    ↓
Deploy Container
    ↓
Health Check
    ↓
Success or Rollback
```

## Prerequisites

### 1. Windows Server Setup

**Required Software:**
- Windows Server 2019 or later
- Docker Desktop for Windows (with WSL 2 backend)
- OpenSSH Server (for remote access)
- Git (optional, for manual deployment)

**Installation Steps:**

```powershell
# Install Docker Desktop for Windows
# Download from: https://www.docker.com/products/docker-desktop/

# Enable OpenSSH Server (if not already enabled)
# Go to Settings > Apps > Optional Features > OpenSSH Server

# Start SSH service
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# Confirm SSH is running
Get-Service sshd
```

### 2. Firewall Configuration

```powershell
# Allow SSH (port 22)
New-NetFirewallRule -DisplayName "SSH" -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow

# Allow application port (8000)
New-NetFirewallRule -DisplayName "LoL Stonks RSS" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow

# Verify rules
Get-NetFirewallRule -DisplayName "SSH", "LoL Stonks RSS"
```

### 3. Docker Configuration

```powershell
# Verify Docker is running
docker --version
docker ps

# Login to GitHub Container Registry (for manual pulls)
# Username: GitHub username
# Password: GitHub Personal Access Token (PAT) with `read:packages` scope
docker login ghcr.io
```

### 4. Deployment Directory Setup

```powershell
# Create deployment directory
mkdir C:\lolstonksrss
cd C:\lolstonksrss

# Create required subdirectories
mkdir data
mkdir logs

# Verify permissions
icacls . /grant "${env:USERNAME}:(OI)(CI)F"
```

## GitHub Secrets Configuration

### Required Secrets

Configure the following secrets in your GitHub repository (`Settings > Secrets and variables > Actions > New repository secret`):

| Secret Name | Description | Example |
|------------|-------------|---------|
| `WINDOWS_SERVER_HOST` | Server hostname or IP address | `192.168.1.100` or `server.example.com` |
| `WINDOWS_SERVER_USER` | SSH username | `deploy` or `Administrator` |
| `WINDOWS_SERVER_SSH_KEY` | Private SSH key for authentication | See key generation below |
| `WINDOWS_SERVER_DEPLOY_PATH` | Deployment path on server | `C:\lolstonksrss` or `C:\inetpub\wwwroot\lolstonksrss` |
| `GITHUB_TOKEN` | Automatically provided by GitHub Actions | N/A (automatic) |

### SSH Key Generation

**On your local machine:**

```powershell
# Generate SSH key pair (if you don't have one)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_actions_deploy

# This creates:
# - Private key: ~/.ssh/github_actions_deploy
# - Public key: ~/.ssh/github_actions_deploy.pub
```

**On Windows Server:**

```powershell
# Copy the PUBLIC key content and add it to:
# C:\Users\<USERNAME>\.ssh\authorized_keys

# If file doesn't exist, create it:
mkdir C:\Users\$env:USERNAME\.ssh
New-Item C:\Users\$env:USERNAME\.ssh\authorized_keys

# Add the public key content to authorized_keys
# (Use your favorite text editor)

# Set proper permissions
icacls C:\Users\$env:USERNAME\.ssh\authorized_keys /inheritance:r
icacls C:\Users\$env:USERNAME\.ssh\authorized_keys /grant "$($env:USERNAME):R"

# Test SSH connection from GitHub Actions runner (via manual workflow)
```

**Add Private Key to GitHub Secrets:**

1. Copy the content of the private key file (e.g., `github_actions_deploy`)
2. Go to GitHub repository: `Settings > Secrets and variables > Actions`
3. Click `New repository secret`
4. Name: `WINDOWS_SERVER_SSH_KEY`
5. Paste the entire private key content (including `-----BEGIN` and `-----END` lines)
6. Click `Add secret`

**Important Security Notes:**
- Never commit private keys to the repository
- Use dedicated deploy user with minimal permissions
- Rotate SSH keys regularly
- Restrict SSH access by IP address using firewall rules

## Deployment Workflow

### Automatic Deployment

Deployment is automatically triggered on:
- Push to `main` or `master` branch
- Creating release tags (e.g., `v1.0.0`)
- Manual workflow dispatch

### Manual Deployment

1. Go to `Actions` tab in GitHub
2. Select `Deploy to Production (Windows Server)` workflow
3. Click `Run workflow`
4. Select branch
5. Choose environment (production or staging)
6. Click `Run workflow`

## Deployment Process

### Step-by-Step

1. **Pre-deployment Checks**
   - Verify repository state
   - Extract image metadata
   - Confirm deployment should proceed

2. **Build and Push**
   - Build Docker image using Buildx
   - Tag with multiple versions (latest, semver, SHA)
   - Push to GitHub Container Registry (GHCR)
   - Generate artifact attestation

3. **Deploy to Server**
   - Setup SSH connection
   - Verify SSH connectivity
   - Backup current version as `:previous`
   - Pull new Docker image
   - Stop existing container
   - Start new container
   - Wait for startup (45 seconds)

4. **Health Check**
   - Check `/health` endpoint (up to 30 attempts)
   - Verify main feed: `/feed.xml`
   - Verify English feed: `/feeds/en-us.xml`
   - Verify Italian feed: `/feeds/it-it.xml`

5. **Success or Rollback**
   - **Success**: Display deployment summary
   - **Failure**: Automatic rollback to `:previous` image

## Rollback Strategy

### Automatic Rollback

If deployment fails (health check timeout), the workflow automatically:
1. Stops the failed container
2. Tags `:previous` image as `:latest`
3. Starts container with previous version
4. Verifies rollback health
5. Sends notification

### Manual Rollback

If you need to manually rollback:

```powershell
# On the Windows Server
cd C:\lolstonksrss

# Run the rollback script
.\scripts\rollback.ps1

# Or with specific image tag
.\scripts\rollback.ps1 -ImageTag "previous"

# Force rollback (skip confirmation)
.\scripts\rollback.ps1 -Force
```

### Rollback Verification

After rollback, verify:

```powershell
# Check container status
docker ps

# Check health endpoint
Invoke-WebRequest -Uri http://localhost:8000/health

# Check logs
docker logs -f lolstonksrss
```

## Blue-Green Deployment

### Overview

Blue-green deployment maintains two identical production environments:
- **Blue**: Currently active environment
- **Green**: New version being deployed

### Benefits

- Zero-downtime deployment
- Instant rollback capability
- Safe testing before cutover
- Reduced deployment risk

### Implementation

The deployment script (`scripts/deploy.ps1`) supports blue-green deployments:

```powershell
# Deploy to blue environment
.\scripts\deploy.ps1 -Environment "blue"

# Deploy to green environment
.\scripts\deploy.ps1 -Environment "green"
```

### Traffic Switching

After deploying to the inactive environment:

1. **Verify new environment**
   ```powershell
   # Check health on green (port 8001)
   Invoke-WebRequest -Uri http://localhost:8001/health
   ```

2. **Switch traffic** (choose one method)

   **Method A: Port forwarding change**
   - Update reverse proxy to point to new port
   - Switch port mappings: `docker stop lolstonksrss-blue`

   **Method B: DNS switch**
   - Update DNS records to point to new environment
   - Wait for DNS propagation

3. **Monitor for issues**
   ```powershell
   docker logs -f lolstonksrss-green
   ```

4. **Clean up old environment** (after verification)
   ```powershell
   docker stop lolstonksrss-blue
   docker rm lolstonksrss-blue
   ```

## Monitoring and Logging

### Container Logs

```powershell
# Follow logs in real-time
docker logs -f lolstonksrss

# Last 100 lines
docker logs --tail 100 lolstonksrss

# Logs with timestamps
docker logs -t lolstonksrss
```

### Deployment Logs

Deployment logs are stored in:
- GitHub Actions workflow logs (web UI)
- Server: `C:\lolstonksrss\logs\deploy-*.log`
- Rollback logs: `C:\lolstonksrss\logs\rollback-*.log`

### Health Monitoring

Create a monitoring script:

```powershell
# monitor.ps1
while ($true) {
    try {
        $response = Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing -TimeoutSec 10
        $data = $response.Content | ConvertFrom-Json

        if ($data.status -eq "healthy") {
            Write-Host "[$(Get-Date)] Service healthy" -ForegroundColor Green
        } else {
            Write-Host "[$(Get-Date)] Service unhealthy: $($data.status)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[$(Get-Date)] Service unreachable: $($_.Exception.Message)" -ForegroundColor Red
    }

    Start-Sleep -Seconds 60
}
```

## Troubleshooting

### Common Issues

#### 1. SSH Connection Failed

**Symptoms:**
- Workflow fails at "Verify SSH connection" step
- Error: "Connection refused" or "Authentication failed"

**Solutions:**
```powershell
# On Windows Server, check SSH service
Get-Service sshd
Start-Service sshd

# Check firewall
Get-NetFirewallRule -DisplayName "SSH"

# Test SSH locally
ssh localhost

# Check authorized_keys
cat C:\Users\$env:USERNAME\.ssh\authorized_keys

# Check SSH logs
Get-WinEvent -LogName OpenSSH/Operational -MaxEvents 50
```

#### 2. Docker Pull Failed

**Symptoms:**
- Workflow fails at "Pull new Docker image" step
- Error: "denied" or "authentication required"

**Solutions:**
```powershell
# Login to GHCR manually
docker login ghcr.io

# Verify credentials
# Use GitHub PAT with `read:packages` scope

# Check image exists
# Visit: https://github.com/OneStepAt4time/lolstonksrss/pkgs/container/lolstonksrss
```

#### 3. Container Won't Start

**Symptoms:**
- Container exits immediately after start
- Health check fails

**Solutions:**
```powershell
# Check container logs
docker logs lolstonksrss

# Check if port is in use
netstat -ano | Select-String ":8000"

# Run container manually to debug
docker run -it --rm lolstonksrss:latest /bin/bash

# Check data directory permissions
icacls C:\lolstonksrss\data
```

#### 4. Health Check Timeout

**Symptoms:**
- Deployment fails after health check attempts
- Service not responding on port 8000

**Solutions:**
```powershell
# Test health endpoint manually
Invoke-WebRequest -Uri http://localhost:8000/health

# Check if container is running
docker ps

# Check container logs for errors
docker logs --tail 50 lolstonksrss

# Verify port mapping
docker port lolstonksrss

# Increase health check timeout
# Edit workflow: increase `sleep 45` to `sleep 90`
```

#### 5. Rollback Failed

**Symptoms:**
- Rollback doesn't restore previous version
- No `:previous` image exists

**Solutions:**
```powershell
# List available images
docker images

# Manually tag previous version
# Find previous image ID and tag it
docker tag <IMAGE_ID> lolstonksrss:previous

# Run rollback
.\scripts\rollback.ps1 -Force
```

## Security Best Practices

### 1. SSH Security

```powershell
# Disable password authentication (key-only)
# Edit: C:\ProgramData\ssh\sshd_config
PasswordAuthentication no

# Restrict allowed users
AllowUsers deploy

# Restart SSH service
Restart-Service sshd
```

### 2. Docker Security

```powershell
# Run as non-root user (already configured in Dockerfile)
# Set resource limits
docker update --memory="512m" --cpus="1.0" lolstonksrss

# Use read-only root filesystem (advanced)
docker run --read-only --tmpfs /tmp lolstonksrss:latest
```

### 3. Network Security

```powershell
# Isolate container network
docker network create --driver bridge lolrss_isolated

# Restrict inbound traffic
New-NetFirewallRule -DisplayName "LoL Stonks RSS" `
  -Direction Inbound -Protocol TCP -LocalPort 8000 `
  -Action Allow -RemoteAddress "192.168.1.0/24"
```

### 4. Secrets Management

- Never commit secrets to repository
- Use GitHub Secrets for sensitive data
- Rotate credentials regularly
- Use environment-specific secrets (dev, staging, prod)
- Limit secret access to necessary workflows

## Performance Optimization

### 1. Image Size Reduction

Already implemented in Dockerfile:
- Multi-stage build
- Minimal base image (python:3.11-slim)
- Non-root user
- Optimized layer caching

### 2. Deployment Speed

- Use GitHub Actions cache for Docker layers
- Parallel build for multiple architectures
- Pre-pull images during low-traffic periods
- Use layer caching in Buildx

### 3. Container Performance

```yaml
# Add to docker-compose.yml for resource limits
services:
  lolstonksrss:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

## Backup and Disaster Recovery

### Database Backup

```powershell
# Automated backup script
$backupDir = "C:\lolstonksrss\backups\$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -Path $backupDir -ItemType Directory -Force

# Stop container
docker stop lolstonksrss

# Backup database
Copy-Item C:\lolstonksrss\data\articles.db $backupDir\

# Start container
docker start lolstonksrss

# Compress backup
Compress-Archive -Path $backupDir -DestinationPath "$backupDir.zip"
```

### Disaster Recovery Plan

1. **Regular Backups**
   - Daily automated database backups
   - Weekly full application backups
   - Store backups off-site

2. **Documentation**
   - Keep deployment documentation up-to-date
   - Document all custom configurations
   - Maintain runbook for common issues

3. **Testing**
   - Regular backup restoration tests
   - Disaster recovery drills
   - Rollback procedure validation

## Maintenance

### Regular Updates

```powershell
# Update Docker Desktop
# Check for updates in Docker Desktop UI

# Update base image
docker pull python:3.11-slim

# Rebuild application image
cd C:\lolstonksrss
docker build -t lolstonksrss:latest .
```

### Log Rotation

```powershell
# Configure Docker log rotation
# Edit: C:\ProgramData\docker\config\daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

# Restart Docker service
Restart-Service docker
```

### Health Monitoring

Set up automated monitoring:
- Use Application Insights or similar
- Configure alerting for health check failures
- Monitor container resource usage
- Track deployment success rate

## Support and Resources

### Documentation

- [Main Documentation](./index.md)
- [Windows Deployment Guide](./WINDOWS_DEPLOYMENT.md)
- [Docker Guide](./DOCKER.md)
- [Troubleshooting](./TROUBLESHOOTING.md)

### External Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Windows Server Documentation](https://docs.microsoft.com/en-us/windows-server/)

### Getting Help

- Check GitHub Issues
- Review deployment logs
- Check container logs
- Verify system requirements
- Test with staging environment first

## Quick Reference

### Essential Commands

```powershell
# Deploy manually
.\scripts\deploy.ps1 -Environment "blue"

# Rollback
.\scripts\rollback.ps1

# Check status
docker ps
docker logs lolstonksrss

# Health check
Invoke-WebRequest -Uri http://localhost:8000/health

# View feeds
Invoke-WebRequest -Uri http://localhost:8000/feed.xml
```

### GitHub Workflow

- **Workflow**: `.github/workflows/deploy-production.yml`
- **Trigger**: Push to main/master or manual dispatch
- **Duration**: ~5-10 minutes
- **Timeout**: 600 seconds (10 minutes)

### Ports

- **Application**: 8000
- **SSH**: 22
- **Blue environment**: 8000
- **Green environment**: 8001

## Success Criteria

Deployment is successful when:
- [ ] Workflow completes without errors
- [ ] Container is running on server
- [ ] Health check returns "healthy"
- [ ] All feed endpoints are accessible
- [ ] Logs show no errors
- [ ] Previous version is backed up as `:previous`

## Next Steps

After setting up automated deployment:
1. Test deployment to staging environment
2. Verify rollback mechanism
3. Set up monitoring and alerting
4. Document custom configurations
5. Train team on deployment process
6. Schedule regular maintenance
7. Review and update documentation regularly
