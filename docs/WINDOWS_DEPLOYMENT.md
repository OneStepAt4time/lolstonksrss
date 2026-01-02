# Windows Server Deployment Guide

Complete guide for deploying LoL Stonks RSS on Windows Server using Docker.

## Deployment Methods

This guide covers two deployment approaches:

1. **Automated Deployment** (Recommended for production)
   - GitHub Actions CI/CD pipeline
   - Zero-touch deployment
   - Automated rollback on failure
   - See: [Automated Deployment Guide](./DEPLOYMENT.md)

2. **Manual Deployment** (For development/staging)
   - Manual Docker commands
   - Full control over deployment process
   - Covered in this document

For production use, see the [Automated Deployment Guide](./DEPLOYMENT.md) for GitHub Actions setup.

## Prerequisites

### 1. Windows Server Requirements
- Windows Server 2019 or later (Windows 10/11 also supported)
- 4GB RAM minimum (8GB recommended)
- 20GB free disk space
- Administrator access

### 2. Install Docker Desktop for Windows

Download and install Docker Desktop:
https://www.docker.com/products/docker-desktop/

**Post-installation:**
```powershell
# Verify installation
docker --version
docker-compose --version

# Enable WSL 2 backend (recommended for better performance)
wsl --install
wsl --set-default-version 2
```

### 3. Install Git (optional, for cloning)
https://git-scm.com/download/win

## Deployment Steps

### Step 1: Prepare Application Files

**Option A: Clone from repository**
```powershell
git clone <repository-url>
cd lolstonksrss
```

**Option B: Copy files manually**
- Copy entire project folder to `C:\lolstonksrss\`

### Step 2: Configure Environment

Create `.env` file in project root (or use .env.example as template):
```env
# Database Configuration
DATABASE_PATH=data/articles.db

# LoL News API Configuration
LOL_NEWS_BASE_URL=https://www.leagueoflegends.com
SUPPORTED_LOCALES=en-us,it-it

# Caching Configuration (seconds)
CACHE_TTL_SECONDS=21600
BUILD_ID_CACHE_SECONDS=86400

# RSS Feed Configuration
RSS_FEED_TITLE=League of Legends News
RSS_FEED_DESCRIPTION=Latest LoL news and updates
RSS_FEED_LINK=https://www.leagueoflegends.com/news
RSS_MAX_ITEMS=50

# Server Configuration
BASE_URL=http://your-server-ip:8000
HOST=0.0.0.0
PORT=8000

# Update Configuration
UPDATE_INTERVAL_MINUTES=30

# Logging
LOG_LEVEL=INFO
```

### Step 3: Build Docker Image

Open PowerShell as Administrator:
```powershell
cd C:\lolstonksrss

# Build image
docker build -t lolstonksrss:latest .

# Verify
docker images | Select-String "lolstonksrss"
```

### Step 4: Create Data Directory

```powershell
# Create data directory with proper permissions
New-Item -Path ".\data" -ItemType Directory -Force
```

### Step 5: Start Container

**Using docker-compose (recommended):**
```powershell
# Start in detached mode
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Using docker run:**
```powershell
docker run -d `
  --name lolstonksrss `
  --restart unless-stopped `
  -p 8000:8000 `
  -v ${PWD}\data:/app/data `
  -e DATABASE_PATH=/app/data/articles.db `
  -e HOST=0.0.0.0 `
  -e PORT=8000 `
  lolstonksrss:latest

# Check status
docker ps

# View logs
docker logs -f lolstonksrss
```

### Step 6: Verify Deployment

**Test endpoints:**
```powershell
# Health check
Invoke-WebRequest -Uri http://localhost:8000/health

# Get RSS feed
Invoke-WebRequest -Uri http://localhost:8000/feed.xml

# View API documentation
Start-Process "http://localhost:8000/docs"
```

**Test from command line:**
```powershell
# Using curl (if installed)
curl http://localhost:8000/health
curl http://localhost:8000/feed.xml

# Or with PowerShell
(Invoke-WebRequest -Uri http://localhost:8000/health).Content | ConvertFrom-Json
```

## Windows Firewall Configuration

Allow inbound traffic on port 8000:

```powershell
# Open PowerShell as Administrator

# Add firewall rule
New-NetFirewallRule `
  -DisplayName "LoL Stonks RSS" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8000 `
  -Action Allow `
  -Profile Domain,Private

# Verify rule
Get-NetFirewallRule -DisplayName "LoL Stonks RSS"
```

## Running as Windows Service (Optional)

### Using Docker restart policy:
Already configured in docker-compose with `restart: unless-stopped`

Docker Desktop automatically starts on Windows startup, and containers with restart policy will auto-start.

### Using NSSM (Non-Sucking Service Manager):

1. Download NSSM: https://nssm.cc/download

2. Install as Windows Service:
```powershell
# Install service
nssm install LolStonksRSS "C:\Program Files\Docker\Docker\resources\bin\docker-compose.exe"
nssm set LolStonksRSS AppDirectory "C:\lolstonksrss"
nssm set LolStonksRSS AppParameters "up"

# Start service
nssm start LolStonksRSS

# Check status
nssm status LolStonksRSS
```

## Maintenance Commands

### View logs:
```powershell
# Using docker-compose
docker-compose logs -f

# Using docker directly
docker logs -f lolstonksrss

# Last 100 lines
docker logs --tail 100 lolstonksrss
```

### Restart container:
```powershell
# Using docker-compose
docker-compose restart

# Using docker directly
docker restart lolstonksrss
```

### Stop container:
```powershell
# Using docker-compose
docker-compose down

# Using docker directly
docker stop lolstonksrss
```

### Update application:
```powershell
# Pull latest code (if using git)
git pull

# Stop containers
docker-compose down

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs
```

### Backup database:
```powershell
# Stop container to ensure clean backup
docker-compose down

# Create backup directory
$backupDate = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -Path ".\backups\backup-$backupDate" -ItemType Directory -Force

# Backup data directory
Copy-Item -Path ".\data\*" -Destination ".\backups\backup-$backupDate" -Recurse

# Restart container
docker-compose up -d

Write-Host "Backup completed: .\backups\backup-$backupDate"
```

### Clean up Docker resources:
```powershell
# Remove unused containers
docker container prune -f

# Remove unused images
docker image prune -f

# Remove unused volumes
docker volume prune -f

# Full cleanup (careful!)
docker system prune -a -f
```

## Troubleshooting

### Container won't start:

```powershell
# Check logs for errors
docker logs lolstonksrss

# Check if port is in use
netstat -ano | Select-String ":8000"

# Check Docker status
docker ps -a

# Check container details
docker inspect lolstonksrss
```

### Permission issues:

```powershell
# Fix data directory permissions
icacls ".\data" /grant Everyone:(OI)(CI)F /T

# Or reset to user permissions
icacls ".\data" /grant ${env:USERNAME}:(OI)(CI)F /T
```

### Database locked:

```powershell
# Ensure only one container is running
docker ps -a | Select-String "lolstonksrss"

# Remove duplicate containers
docker stop lolstonksrss
docker rm lolstonksrss

# Restart fresh
docker-compose up -d
```

### Health check failing:

```powershell
# Check application logs
docker logs lolstonksrss

# Test health endpoint manually
Invoke-WebRequest -Uri http://localhost:8000/health

# Access container shell
docker exec -it lolstonksrss /bin/bash
```

### Port already in use:

```powershell
# Find process using port 8000
netstat -ano | Select-String ":8000"

# Kill process (replace PID)
Stop-Process -Id <PID> -Force

# Or change port in docker-compose.yml
# ports:
#   - "8001:8000"  # Use port 8001 on host
```

## Monitoring

### Health checks:
```powershell
# Manual health check
$health = Invoke-WebRequest -Uri http://localhost:8000/health | ConvertFrom-Json
$health

# Scheduler status
$status = Invoke-WebRequest -Uri http://localhost:8000/admin/scheduler/status | ConvertFrom-Json
$status

# RSS feed stats
Invoke-WebRequest -Uri http://localhost:8000/feed.xml
```

### Resource usage:
```powershell
# Real-time stats
docker stats lolstonksrss

# Container details
docker inspect lolstonksrss

# Disk usage
docker system df
```

### Automated monitoring script:
```powershell
# Save as monitor.ps1
while ($true) {
    $response = Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    if ($response.StatusCode -eq 200) {
        Write-Host "[$timestamp] Service healthy" -ForegroundColor Green
    } else {
        Write-Host "[$timestamp] Service unhealthy - Status: $($response.StatusCode)" -ForegroundColor Red
    }

    Start-Sleep -Seconds 60
}
```

## Security Considerations

### 1. Network Security:
```powershell
# Configure Windows Firewall properly
# Only allow specific IPs if needed
New-NetFirewallRule `
  -DisplayName "LoL Stonks RSS - Restricted" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8000 `
  -Action Allow `
  -RemoteAddress "192.168.1.0/24"
```

### 2. Use reverse proxy for HTTPS:
- Configure IIS or nginx as reverse proxy
- Install SSL certificate
- Redirect HTTP to HTTPS

### 3. File Permissions:
```powershell
# Data directory should be writable by container
icacls ".\data" /grant "Users:(OI)(CI)M"

# .env file should be restricted
icacls ".\.env" /inheritance:r
icacls ".\.env" /grant "${env:USERNAME}:R"
```

### 4. Regular Updates:
```powershell
# Update Docker images regularly
docker pull python:3.11-slim
docker-compose build --no-cache
docker-compose up -d
```

## Production Checklist

- [ ] Docker Desktop installed and running
- [ ] WSL 2 backend enabled (for better performance)
- [ ] Firewall configured to allow port 8000
- [ ] .env file configured with production settings
- [ ] Data directory created with proper permissions
- [ ] Container started with restart policy (unless-stopped)
- [ ] Health check endpoint responding
- [ ] RSS feeds accessible (all locales)
- [ ] Logs being monitored
- [ ] Backup strategy in place
- [ ] Monitoring configured (health checks)
- [ ] Documentation reviewed
- [ ] Admin credentials secured (if applicable)
- [ ] SSL/TLS configured (if using reverse proxy)
- [ ] Resource limits set (if needed)

## Advanced Configuration

### Resource Limits:
Edit `docker-compose.yml` to add resource constraints:

```yaml
services:
  lolstonksrss:
    # ... existing config ...
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Custom Logging:
```yaml
services:
  lolstonksrss:
    # ... existing config ...
    logging:
      driver: "local"
      options:
        max-size: "10m"
        max-file: "5"
        compress: "true"
```

### Network Isolation:
```powershell
# Create custom network
docker network create lolrss_isolated

# Run with custom network
docker-compose --file docker-compose.yml up -d
```

## Support and Troubleshooting

### Common Issues:

1. **"Port already in use"**
   - Change port in docker-compose.yml or stop conflicting service

2. **"Permission denied"**
   - Run PowerShell as Administrator
   - Check file/folder permissions with icacls

3. **"Container exits immediately"**
   - Check logs: `docker logs lolstonksrss`
   - Verify .env file exists and is valid

4. **"Health check failing"**
   - Check application logs
   - Verify port 8000 is accessible inside container
   - Test: `docker exec lolstonksrss curl http://localhost:8000/health`

### Getting Help:
- Check Docker logs: `docker logs lolstonksrss`
- Check application logs in container
- Review this documentation
- Check GitHub issues (if applicable)

## Next Steps

After successful deployment:
1. Test all RSS feed endpoints
2. Verify automatic updates are working
3. Set up monitoring/alerting
4. Configure backups
5. Document any custom configuration
6. Plan for updates and maintenance
