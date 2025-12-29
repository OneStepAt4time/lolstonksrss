# Scripts for LoL Stonks RSS

This directory contains automation scripts to help manage and deploy the LoL Stonks RSS application.

## Available Scripts

### Python Scripts

#### test_news_workflow.py

Test script for GitHub Pages news publishing workflow. Simulates all workflow steps locally to verify everything works before deploying to GitHub Actions.

**Usage:**
```bash
python scripts/test_news_workflow.py
python scripts/test_news_workflow.py --limit 50
```

**Parameters:**
- `--limit, -l`: Number of articles to include (default: 100)

**Examples:**
```bash
# Test with default settings (100 articles)
python scripts/test_news_workflow.py

# Test with 50 articles
python scripts/test_news_workflow.py --limit 50

# Test with maximum articles
python scripts/test_news_workflow.py --limit 500
```

**What it tests:**
1. Database initialization
2. News fetching from LoL API
3. HTML page generation
4. GitHub Pages directory structure creation
5. File output verification

**Output:**
- Detailed progress reporting
- Success/failure indicators
- File size information
- Next steps guidance
- Troubleshooting hints

**Use this before:**
- Pushing workflow to GitHub
- Testing template changes
- Debugging workflow issues
- Verifying local setup

---

#### generate_news_page.py

Generate HTML news page from database articles. Used by the GitHub Actions workflow and can be run standalone.

**Usage:**
```bash
python scripts/generate_news_page.py
python scripts/generate_news_page.py --output custom.html --limit 100
```

**Parameters:**
- `--output, -o`: Output HTML file path (default: news.html)
- `--limit, -l`: Maximum number of articles (default: 50, max: 500)

**Examples:**
```bash
# Generate with defaults
python scripts/generate_news_page.py

# Custom output location
python scripts/generate_news_page.py --output public/index.html

# More articles
python scripts/generate_news_page.py --limit 100

# Combine options
python scripts/generate_news_page.py --output docs/news.html --limit 200
```

**Features:**
- Beautiful LoL-themed HTML
- Responsive design (mobile-friendly)
- Dark/light mode toggle
- Real-time filtering and search
- Auto-refresh every 5 minutes
- Category and source badges

---

### PowerShell Scripts

### 1. windows-deploy.ps1

Automated deployment script that handles the entire deployment process.

**Usage:**
```powershell
.\scripts\windows-deploy.ps1
```

**Parameters:**
- `-SkipBuild`: Skip the Docker build step (use existing image)
- `-NoBrowser`: Don't open browser after deployment
- `-Port`: Specify custom port (default: 8000)

**Examples:**
```powershell
# Full deployment
.\scripts\windows-deploy.ps1

# Deploy without rebuilding
.\scripts\windows-deploy.ps1 -SkipBuild

# Deploy on custom port
.\scripts\windows-deploy.ps1 -Port 8001

# Deploy without opening browser
.\scripts\windows-deploy.ps1 -NoBrowser
```

**What it does:**
1. Checks Docker installation
2. Creates data directory
3. Creates .env from template (if needed)
4. Builds Docker image
5. Stops existing containers
6. Starts new container
7. Waits for health check
8. Opens browser (unless -NoBrowser)

### 2. monitor.ps1

Continuous health monitoring script for the RSS service.

**Usage:**
```powershell
.\scripts\monitor.ps1
```

**Parameters:**
- `-IntervalSeconds`: Check interval in seconds (default: 60)
- `-Port`: Service port to monitor (default: 8000)
- `-LogFile`: Path to log file (optional)

**Examples:**
```powershell
# Monitor with default settings (60 second interval)
.\scripts\monitor.ps1

# Monitor every 30 seconds
.\scripts\monitor.ps1 -IntervalSeconds 30

# Monitor with logging to file
.\scripts\monitor.ps1 -LogFile "C:\logs\monitor.log"

# Monitor custom port
.\scripts\monitor.ps1 -Port 8001
```

**Features:**
- Continuous health monitoring
- Success/failure tracking
- Consecutive failure alerts
- Statistics every 10 checks
- Optional logging to file
- Color-coded output

**Press Ctrl+C to stop monitoring**

### 3. backup.ps1

Backup script for database and configuration files.

**Usage:**
```powershell
.\scripts\backup.ps1
```

**Parameters:**
- `-BackupDir`: Backup directory (default: ..\backups)
- `-SkipStop`: Don't stop container before backup
- `-KeepDays`: Days to keep old backups (default: 30, 0 = keep all)

**Examples:**
```powershell
# Standard backup (stops container)
.\scripts\backup.ps1

# Backup without stopping container (hot backup)
.\scripts\backup.ps1 -SkipStop

# Backup to custom location
.\scripts\backup.ps1 -BackupDir "D:\Backups"

# Keep backups for 60 days
.\scripts\backup.ps1 -KeepDays 60

# Keep all backups (no cleanup)
.\scripts\backup.ps1 -KeepDays 0
```

**What it backs up:**
- Database files (data directory)
- Configuration files (.env)
- Backup manifest (metadata)

**Automatic cleanup:**
- Removes backups older than specified days
- Default: 30 days retention

## Quick Reference

### First Time Deployment
```powershell
# Navigate to project directory
cd C:\lolstonksrss

# Run deployment script
.\scripts\windows-deploy.ps1
```

### Regular Monitoring
```powershell
# Start monitoring in a separate window
Start-Process powershell -ArgumentList "-NoExit", "-File", ".\scripts\monitor.ps1"
```

### Scheduled Backups

Create a Windows Task Scheduler task:

1. Open Task Scheduler
2. Create Basic Task
3. Name: "LoL RSS Backup"
4. Trigger: Daily at 2:00 AM
5. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-File C:\lolstonksrss\scripts\backup.ps1`
   - Start in: `C:\lolstonksrss\scripts`

### Common Tasks

**Deploy/Update:**
```powershell
.\scripts\windows-deploy.ps1
```

**Check Health:**
```powershell
Invoke-WebRequest -Uri http://localhost:8000/health | ConvertFrom-Json
```

**View Logs:**
```powershell
docker-compose logs -f
```

**Backup:**
```powershell
.\scripts\backup.ps1
```

**Restart Service:**
```powershell
docker-compose restart
```

**Stop Service:**
```powershell
docker-compose down
```

## Troubleshooting

### Script Execution Policy

If you get an error about execution policy:

```powershell
# Check current policy
Get-ExecutionPolicy

# Set policy to allow local scripts (as Administrator)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Docker Not Found

If script says Docker not found:

1. Verify Docker Desktop is installed
2. Ensure Docker Desktop is running
3. Restart PowerShell to refresh PATH
4. Try: `docker --version`

### Permission Denied

If you get permission errors:

```powershell
# Run PowerShell as Administrator
# Or fix directory permissions:
icacls ".\data" /grant Everyone:(OI)(CI)F /T
```

### Port Already in Use

If port 8000 is in use:

```powershell
# Find what's using the port
netstat -ano | Select-String ":8000"

# Use different port
.\scripts\windows-deploy.ps1 -Port 8001
```

## Best Practices

### Production Deployment
1. Test deployment in non-production environment first
2. Review logs after deployment
3. Monitor health for at least 24 hours
4. Set up regular backups
5. Document any customizations

### Monitoring
1. Run monitor.ps1 in separate window or as scheduled task
2. Review statistics regularly
3. Set up alerts for consecutive failures
4. Log to file for historical analysis

### Backups
1. Schedule daily backups via Task Scheduler
2. Store backups on separate drive/server
3. Test restoration procedure regularly
4. Keep at least 30 days of backups
5. Monitor backup disk space

### Updates
1. Pull latest code: `git pull`
2. Review changelog
3. Test in development environment
4. Backup before updating production
5. Deploy during low-traffic period

## Advanced Usage

### Custom Deployment Script

Create your own deployment script based on windows-deploy.ps1:

```powershell
# my-deploy.ps1
param([string]$Environment = "production")

# Set environment-specific variables
if ($Environment -eq "production") {
    $port = 8000
    $logLevel = "INFO"
} else {
    $port = 8001
    $logLevel = "DEBUG"
}

# Call main deployment script
.\scripts\windows-deploy.ps1 -Port $port
```

### Automated Health Alerts

Modify monitor.ps1 to send email alerts:

```powershell
# Add to monitor.ps1
if ($consecutiveFailures -ge 5) {
    Send-MailMessage `
        -To "admin@example.com" `
        -From "alerts@example.com" `
        -Subject "LoL RSS Alert" `
        -Body "Service unhealthy for 5+ consecutive checks" `
        -SmtpServer "smtp.example.com"
}
```

### Pre-Backup Script Hook

Run custom actions before backup:

```powershell
# pre-backup.ps1
Write-Host "Running pre-backup tasks..."

# Your custom tasks here
# Examples:
# - Flush caches
# - Export reports
# - Notify administrators

.\scripts\backup.ps1
```

## Script Maintenance

### Updating Scripts

When updating scripts from repository:

```powershell
# Pull latest changes
git pull

# Review changes
git diff HEAD~1 scripts/

# Test in non-production environment first
```

### Customization

Feel free to customize these scripts for your environment. Common customizations:

- Change default ports
- Add custom health checks
- Integrate with monitoring systems
- Add notification hooks
- Custom backup locations
- Different retention policies

### Contributing

If you improve these scripts:
1. Test thoroughly
2. Document changes
3. Follow PowerShell best practices
4. Consider backward compatibility

## Support

For issues with scripts:
1. Check troubleshooting section above
2. Review script output/logs
3. Check Docker logs: `docker logs lolstonksrss`
4. See main documentation: `docs/WINDOWS_DEPLOYMENT.md`
