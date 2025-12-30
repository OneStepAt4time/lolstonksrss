# GitHub Pages Auto-Sync Integration

**Complete guide for setting up automatic GitHub Pages updates from Windows server**

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup Guide (Windows-Specific)](#setup-guide-windows-specific)
- [Configuration Reference](#configuration-reference)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)
- [Testing the Integration](#testing-the-integration)
- [FAQ](#faq)
- [Performance Impact](#performance-impact)
- [Rollback Procedure](#rollback-procedure)
- [Support](#support)

---

## Overview

The GitHub Pages auto-sync feature enables your Windows-hosted LoL Stonks RSS application to **automatically trigger GitHub Pages updates** whenever new League of Legends news articles are discovered. This reduces the latency between news publication and your live news page updates from 5 minutes (cron schedule) to approximately 30 seconds.

### What Problem Does It Solve?

**Without auto-sync:**
- Your Windows app fetches news every 5 minutes
- GitHub Actions runs independently on a 5-minute cron schedule
- Potential delay: Up to 10 minutes for new articles to appear on your live page
- Two independent systems that may drift out of sync

**With auto-sync:**
- Windows app detects new articles immediately
- Triggers GitHub workflow via API within seconds
- GitHub Pages updated within ~30 seconds
- Near real-time updates for your audience
- Cron schedule continues as backup fallback

### When to Use vs Cron Schedule

| Scenario | Recommendation |
|----------|----------------|
| **Real-time news updates needed** | Enable auto-sync |
| **Content creators / streamers** | Enable auto-sync |
| **High traffic website** | Enable auto-sync |
| **Personal use / low priority** | Cron schedule is sufficient |
| **Limited GitHub Actions minutes** | Cron schedule is sufficient |
| **Testing / development** | Start with cron, add auto-sync later |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        WINDOWS SERVER                                   │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  LoL Stonks RSS Application (Docker Container)                 │   │
│  │                                                                 │   │
│  │  ┌──────────────┐                                              │   │
│  │  │ APScheduler  │ ─────> Every 5 minutes                       │   │
│  │  └──────┬───────┘                                              │   │
│  │         │                                                       │   │
│  │         v                                                       │   │
│  │  ┌──────────────────────┐                                      │   │
│  │  │  Update Service      │                                      │   │
│  │  │  - Fetch LoL News    │                                      │   │
│  │  │  - Save to SQLite    │                                      │   │
│  │  │  - Detect NEW items  │                                      │   │
│  │  └──────────┬───────────┘                                      │   │
│  │             │                                                   │   │
│  │             │ IF new_articles > 0                              │   │
│  │             v                                                   │   │
│  │  ┌──────────────────────────────────────────────────┐          │   │
│  │  │  GitHub Pages Sync Module                       │          │   │
│  │  │                                                  │          │   │
│  │  │  - Checks: ENABLE_GITHUB_PAGES_SYNC=true       │          │   │
│  │  │  - Validates: GITHUB_TOKEN exists              │          │   │
│  │  │  - Triggers: workflow_dispatch API call        │          │   │
│  │  └──────────────────────┬───────────────────────────┘          │   │
│  └─────────────────────────┼──────────────────────────────────────┘   │
└────────────────────────────┼───────────────────────────────────────────┘
                             │
                             │ HTTPS POST Request
                             │ Authorization: token ghp_xxxxx
                             v
┌─────────────────────────────────────────────────────────────────────────┐
│                      GITHUB.COM API                                     │
│  POST /repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches    │
│                                                                         │
│  Payload:                                                               │
│  {                                                                      │
│    "ref": "main",                                                       │
│    "inputs": {                                                          │
│      "triggered_by": "windows-app",                                     │
│      "reason": "new-articles-detected",                                 │
│      "article_limit": "100"                                             │
│    }                                                                    │
│  }                                                                      │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ Workflow queued (~5-15 seconds)
                             v
┌─────────────────────────────────────────────────────────────────────────┐
│                  GITHUB ACTIONS (Runner)                                │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │  publish-news.yml Workflow                                   │     │
│  │                                                               │     │
│  │  Steps:                                                       │     │
│  │  1. Checkout repository                                       │     │
│  │  2. Setup Python 3.11 + UV                                    │     │
│  │  3. Install dependencies                                      │     │
│  │  4. Fetch latest LoL news (from API)                          │     │
│  │  5. Generate news.html page                                   │     │
│  │  6. Deploy to GitHub Pages                                    │     │
│  │                                                               │     │
│  │  Duration: ~2-3 minutes                                       │     │
│  └───────────────────────────┬───────────────────────────────────┘     │
└────────────────────────────┬─┴────────────────────────────────────────┘
                             │
                             │ Pages deployment (~10-20 seconds)
                             v
┌─────────────────────────────────────────────────────────────────────────┐
│                    GITHUB PAGES (CDN)                                   │
│                                                                         │
│  https://OneStepAt4time.github.io/lolstonksrss/                       │
│                                                                         │
│  ✅ Updated news.html now live                                          │
│  ✅ Latest articles visible to users                                    │
│  ✅ Total latency: ~30 seconds from detection                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Flow Explanation

**Step 1: Windows App Detects New Articles**
- APScheduler triggers update every 5 minutes
- `UpdateService` fetches latest news from Riot Games API
- Articles saved to local SQLite database
- Service checks: `new_articles_count > 0`

**Step 2: GitHub API Authentication**
- App reads environment variables:
  - `ENABLE_GITHUB_PAGES_SYNC=true`
  - `GITHUB_TOKEN=ghp_xxxxx`
  - `GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss`
- Validates token exists and feature is enabled

**Step 3: Workflow Dispatch Mechanism**
- HTTP POST to GitHub API endpoint:
  ```
  POST https://api.github.com/repos/OneStepAt4time/lolstonksrss/actions/workflows/publish-news.yml/dispatches
  ```
- Headers:
  ```
  Authorization: token ghp_xxxxx
  Accept: application/vnd.github+json
  X-GitHub-Api-Version: 2022-11-28
  ```
- Body:
  ```json
  {
    "ref": "main",
    "inputs": {
      "triggered_by": "windows-app",
      "reason": "new-articles-detected",
      "article_limit": "100"
    }
  }
  ```

**Step 4: GitHub Actions Execution**
- Workflow queued (5-15 seconds)
- Runner assigned and starts workflow
- Fetches news independently (doesn't rely on Windows server)
- Generates HTML news page
- Deploys to GitHub Pages
- Total workflow duration: ~2-3 minutes

**Step 5: GitHub Pages Deployment**
- CDN propagation: 10-20 seconds
- Live page updated
- Users see latest articles

### Expected Latency

| Stage | Duration |
|-------|----------|
| Windows app detects new articles | 0s (immediate after 5-min check) |
| GitHub API request | 0.2-0.5s |
| Workflow queue time | 5-15s |
| Workflow execution | 2-3 minutes |
| Pages CDN propagation | 10-20s |
| **Total latency** | **~3 minutes** |

**Compare to cron-only:** Up to 10 minutes (5 min Windows + 5 min GitHub schedule drift)

---

## Prerequisites

Before you start, ensure you have:

### Required Access

- **Windows Server** with Docker installed (Windows Server 2019+ or Windows 10/11)
- **GitHub account** with push access to `OneStepAt4time/lolstonksrss` repository
- **Administrator privileges** on Windows server (for environment variables)
- **Basic command line knowledge** (PowerShell or Command Prompt)

### Software Requirements

| Software | Minimum Version | Notes |
|----------|----------------|-------|
| Windows | Server 2019 / Windows 10 | For Docker Desktop |
| Docker Desktop | 4.0+ | Must be running Linux containers |
| Git | 2.0+ | For cloning repository |
| Text Editor | Any | Notepad, VS Code, Notepad++, etc. |

### Verification Commands

```powershell
# Check Windows version
systeminfo | findstr /B /C:"OS Name" /C:"OS Version"

# Check Docker
docker --version
docker ps  # Should list running containers

# Check Git
git --version

# Check if LoL Stonks RSS is running
docker ps | findstr lolstonksrss
```

---

## Setup Guide (Windows-Specific)

### Step 1: Create GitHub Personal Access Token

**Detailed Instructions:**

1. **Navigate to GitHub Settings**
   - Open browser to: https://github.com/settings/tokens
   - Or: GitHub.com → Profile Picture → Settings → Developer settings → Personal access tokens → Tokens (classic)

2. **Generate New Token**
   - Click **"Generate new token (classic)"** button
   - You may need to re-authenticate with password/2FA

3. **Configure Token**
   - **Note (Token name):** `LoL Stonks RSS - Windows Server`
   - **Expiration:**
     - Recommended: `90 days` (you'll need to rotate it)
     - Maximum: `No expiration` (⚠️ security risk)
     - Best practice: `60 days` with calendar reminder

4. **Select Scopes (Permissions)**

   **Required scopes:**
   - ☑️ **`repo`** - Full control of private repositories
     - This includes `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`, `security_events`
   - ☑️ **`workflow`** - Update GitHub Actions workflows

   **DO NOT select:** `admin:repo_hook`, `delete_repo`, or other unnecessary permissions

5. **Generate Token**
   - Scroll to bottom and click **"Generate token"** button
   - Token will be displayed **only once** (starts with `ghp_`)

6. **Copy Token Immediately**
   ```
   Example format: ghp_AbCdEfGh123456789XXXXXXXXXXXXXXXXX
   ```
   - ⚠️ **IMPORTANT:** This is your ONLY chance to see the token
   - Copy to clipboard or save to password manager immediately
   - **Never commit this token to Git**

7. **Store Token Securely**
   - **Option A:** Save in password manager (1Password, LastPass, Bitwarden)
   - **Option B:** Save in encrypted text file on server
   - **Option C:** Write down and store in secure location
   - **DO NOT:** Email it, paste in Slack, commit to Git, share publicly

### Step 2: Configure Windows Environment

You have two options for configuration. **Option A (`.env` file)** is recommended for Docker deployments.

#### Option A: Using .env File (Recommended)

1. **Navigate to Project Directory**
   ```powershell
   cd D:\lolstonksrss
   ```

2. **Copy Example Configuration**
   ```powershell
   # If .env doesn't exist yet
   copy .env.example .env
   ```

3. **Open .env File**
   ```powershell
   # Using Notepad
   notepad .env

   # Or VS Code
   code .env

   # Or Notepad++
   notepad++ .env
   ```

4. **Add GitHub Pages Configuration**

   Scroll to the bottom of `.env` file and add:

   ```env
   # ============================================
   # GITHUB PAGES INTEGRATION
   # ============================================

   # Enable automatic GitHub Pages updates when new articles are found
   # Set to 'true' to enable, 'false' or omit to disable
   ENABLE_GITHUB_PAGES_SYNC=true

   # GitHub Personal Access Token (required if sync enabled)
   # Create at: https://github.com/settings/tokens
   # Required scopes: 'repo' and 'workflow'
   # ⚠️ SECURITY: Never commit this token to Git (.env is in .gitignore)
   GITHUB_TOKEN=ghp_yourActualTokenHere

   # GitHub repository in format: owner/repo
   # Default: OneStepAt4time/lolstonksrss
   GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss

   # Workflow file name (optional, default: publish-news.yml)
   # GITHUB_WORKFLOW_FILE=publish-news.yml
   ```

5. **Replace Placeholder with Your Token**
   ```env
   # BEFORE (example):
   GITHUB_TOKEN=ghp_yourActualTokenHere

   # AFTER (with your real token):
   GITHUB_TOKEN=ghp_AbCdEfGh123456789XXXXXXXXXXXXXXXXX
   ```

6. **Save File**
   - Press `Ctrl+S` in your editor
   - Verify file is saved: `type .env` to display contents
   - **CRITICAL:** Ensure `.env` is listed in `.gitignore`

7. **Verify .gitignore Protection**
   ```powershell
   # Check if .env is in .gitignore
   findstr /C:".env" .gitignore

   # Should output: .env
   ```

#### Option B: Using Windows Environment Variables

1. **Open Command Prompt as Administrator**
   - Press `Win+X` → "Command Prompt (Admin)" or "Windows PowerShell (Admin)"

2. **Set Environment Variables**
   ```cmd
   setx ENABLE_GITHUB_PAGES_SYNC "true"
   setx GITHUB_TOKEN "ghp_yourActualTokenHere"
   setx GITHUB_REPOSITORY "OneStepAt4time/lolstonksrss"
   ```

3. **Verify Variables Set**
   ```cmd
   echo %ENABLE_GITHUB_PAGES_SYNC%
   echo %GITHUB_TOKEN%
   echo %GITHUB_REPOSITORY%
   ```

4. **Restart Command Prompt**
   - Close and reopen Command Prompt for changes to take effect

5. **Update Docker Compose (if using)**

   Edit `docker-compose.yml` to pass environment variables:
   ```yaml
   services:
     lolstonksrss:
       environment:
         - ENABLE_GITHUB_PAGES_SYNC=${ENABLE_GITHUB_PAGES_SYNC}
         - GITHUB_TOKEN=${GITHUB_TOKEN}
         - GITHUB_REPOSITORY=${GITHUB_REPOSITORY}
   ```

### Step 3: Restart Application

#### Using Docker Compose (Recommended)

```powershell
# Navigate to project directory
cd D:\lolstonksrss

# Stop existing containers
docker-compose down

# Rebuild image (if code changed)
docker-compose build

# Start with new configuration
docker-compose up -d

# Verify container is running
docker-compose ps
```

#### Using Docker Run

```powershell
# Stop and remove existing container
docker stop lolstonksrss
docker rm lolstonksrss

# Run with .env file
docker run -d `
  --name lolstonksrss `
  -p 8000:8000 `
  --env-file .env `
  -v D:\lolstonksrss\data:/app/data `
  --restart unless-stopped `
  lolstonksrss:latest

# Or run with environment variables
docker run -d `
  --name lolstonksrss `
  -p 8000:8000 `
  -e ENABLE_GITHUB_PAGES_SYNC=true `
  -e GITHUB_TOKEN=ghp_yourToken `
  -e GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss `
  -v D:\lolstonksrss\data:/app/data `
  --restart unless-stopped `
  lolstonksrss:latest
```

#### Using Windows Deploy Script (Automated)

```powershell
# Run deployment script (handles everything)
.\scripts\windows-deploy.ps1

# Or with verbose output
.\scripts\windows-deploy.ps1 -Verbose
```

### Step 4: Verify Integration

#### Check Application Logs

```powershell
# View last 100 lines of logs
docker logs lolstonksrss --tail 100

# Follow logs in real-time
docker logs lolstonksrss -f

# Search for GitHub-related logs
docker logs lolstonksrss 2>&1 | findstr /I "github"
```

#### Expected Log Messages

**Success (Feature Enabled):**
```
[INFO] GitHub Pages sync enabled (repository: OneStepAt4time/lolstonksrss)
[INFO] Update complete: 3 new articles
[INFO] GitHub Pages update triggered (new_articles=3)
[INFO] GitHub workflow dispatch successful (status=204)
```

**Warning (Token Missing):**
```
[WARNING] GitHub Pages sync enabled but GITHUB_TOKEN not configured
[INFO] Skipping GitHub Pages update trigger
```

**Error (API Failure):**
```
[ERROR] Failed to trigger GitHub Pages update: 401 Unauthorized
[ERROR] GitHub token may be invalid or expired
```

#### Verify GitHub Workflow Triggered

1. **Open GitHub Actions Page**
   - Navigate to: https://github.com/OneStepAt4time/lolstonksrss/actions
   - Or: Repository → Actions tab

2. **Check Recent Workflow Runs**
   - Look for "Publish News to GitHub Pages" workflow
   - Most recent run should show: "triggered by: windows-app"
   - Status should be: ✅ Success (green checkmark)

3. **View Workflow Details**
   - Click on the workflow run
   - Check "Log trigger source" step should show:
     ```
     Workflow triggered by: windows-app
     Reason: new-articles-detected
     ```

#### Test HTTP Endpoint (Optional)

```powershell
# Check health endpoint
curl http://localhost:8000/health

# Expected response includes:
# - "status": "healthy"
# - "github_pages_sync_enabled": true
```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENABLE_GITHUB_PAGES_SYNC` | No | `false` | Enable/disable auto-sync feature |
| `GITHUB_TOKEN` | Yes* | - | GitHub Personal Access Token (starts with `ghp_`) |
| `GITHUB_REPOSITORY` | No | `OneStepAt4time/lolstonksrss` | Target repository in `owner/repo` format |
| `GITHUB_WORKFLOW_FILE` | No | `publish-news.yml` | Workflow filename to trigger |

*Required only if `ENABLE_GITHUB_PAGES_SYNC=true`

### GitHub Token Scopes Required

The Personal Access Token must have these permissions:

| Scope | Required | Purpose |
|-------|----------|---------|
| `repo` | ✅ Yes | Access repository code and settings |
| `workflow` | ✅ Yes | Trigger workflow_dispatch events |
| `admin:org` | ❌ No | **NOT needed** (security risk) |
| `delete_repo` | ❌ No | **NOT needed** (security risk) |

### Example .env Configuration

```env
# Minimal configuration (recommended)
ENABLE_GITHUB_PAGES_SYNC=true
GITHUB_TOKEN=ghp_abcd1234efgh5678ijkl9012mnop3456qrst7890
GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss

# Full configuration (with all options)
ENABLE_GITHUB_PAGES_SYNC=true
GITHUB_TOKEN=ghp_abcd1234efgh5678ijkl9012mnop3456qrst7890
GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss
GITHUB_WORKFLOW_FILE=publish-news.yml
```

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  lolstonksrss:
    build: .
    image: lolstonksrss:latest
    container_name: lolstonksrss
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      # GitHub Pages Integration
      - ENABLE_GITHUB_PAGES_SYNC=${ENABLE_GITHUB_PAGES_SYNC:-false}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_REPOSITORY=${GITHUB_REPOSITORY:-OneStepAt4time/lolstonksrss}
    restart: unless-stopped
```

---

## How It Works

### Normal Flow (Without Auto-Sync)

```
Timeline: 0:00 - Windows app update cycle
          0:00 - Fetches news, finds 0 new articles

          5:00 - Windows app update cycle
          5:00 - Fetches news, finds 3 NEW articles ✅
          5:00 - Stores in local SQLite database

          7:30 - GitHub Actions cron triggers (scheduled)
          7:30 - Fetches news independently
          7:30 - Generates HTML page
          10:00 - GitHub Pages updated

Total delay: ~5 minutes from detection to live page
```

### With Auto-Sync Enabled

```
Timeline: 0:00 - Windows app update cycle
          0:00 - Fetches news, finds 0 new articles

          5:00 - Windows app update cycle
          5:00 - Fetches news, finds 3 NEW articles ✅
          5:00 - Stores in local SQLite database
          5:00 - Triggers GitHub API immediately 🚀
          5:05 - GitHub workflow starts
          5:05 - Fetches news independently
          5:05 - Generates HTML page
          7:30 - GitHub Pages updated

Total delay: ~2.5 minutes from detection to live page
(50% faster than cron-only)
```

### Fallback Mechanism

**The auto-sync feature does NOT replace the cron schedule.** Both run in parallel:

1. **Cron schedule** (every 5 minutes):
   - Always runs, regardless of auto-sync
   - Ensures updates happen even if Windows server is offline
   - Provides redundancy and reliability

2. **Auto-sync trigger** (when new articles found):
   - Triggers immediately when Windows app detects new articles
   - Reduces latency for breaking news
   - Fails gracefully if GitHub API is unavailable

**If auto-sync fails:**
- Error logged but application continues normally
- Cron schedule will update within 5 minutes
- No user-facing impact

### API Rate Limits

**GitHub API Limits:**
- **Authenticated requests:** 5000/hour
- **Workflow dispatches:** 1000/hour per workflow
- **Our usage:** ~12 triggers/hour (one every 5 minutes if always finding new articles)
- **Conclusion:** Well within limits (< 2% usage)

**Rate Limit Headers (from GitHub):**
```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4988
X-RateLimit-Reset: 1735555200
```

---

## Troubleshooting

### Problem: "GitHub Pages sync enabled but GITHUB_TOKEN not configured"

**Symptoms:**
```
[WARNING] GitHub Pages sync enabled but GITHUB_TOKEN not configured
[INFO] Skipping GitHub Pages update trigger
```

**Diagnosis:**
- Environment variable `GITHUB_TOKEN` is not set or empty
- Docker container not reading `.env` file correctly

**Solutions:**

1. **Verify .env file exists and has token:**
   ```powershell
   type .env | findstr GITHUB_TOKEN
   ```
   Should output: `GITHUB_TOKEN=ghp_xxxxx`

2. **Check Docker container environment:**
   ```powershell
   docker exec lolstonksrss env | findstr GITHUB
   ```
   Should show:
   ```
   ENABLE_GITHUB_PAGES_SYNC=true
   GITHUB_TOKEN=ghp_xxxxx
   GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss
   ```

3. **Restart container with --env-file:**
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

4. **Verify token in .env has no quotes:**
   ```env
   # WRONG:
   GITHUB_TOKEN="ghp_xxxxx"

   # CORRECT:
   GITHUB_TOKEN=ghp_xxxxx
   ```

### Problem: "Failed to trigger GitHub Pages update: 401 Unauthorized"

**Symptoms:**
```
[ERROR] Failed to trigger GitHub Pages update: 401 Unauthorized
[ERROR] HTTP Status: 401, Message: Bad credentials
```

**Diagnosis:**
- GitHub token is invalid, expired, or revoked
- Token missing required scopes

**Solutions:**

1. **Verify token is valid:**
   - Go to: https://github.com/settings/tokens
   - Check if token exists and hasn't expired
   - Check "Note" field matches: "LoL Stonks RSS - Windows Server"

2. **Test token manually:**
   ```powershell
   $token = "ghp_yourTokenHere"
   $headers = @{
       "Authorization" = "token $token"
       "Accept" = "application/vnd.github+json"
   }
   Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headers
   ```
   Should return your GitHub user info. If error, token is invalid.

3. **Regenerate token:**
   - Go to: https://github.com/settings/tokens
   - Click "Delete" on old token
   - Create new token (follow Step 1 instructions)
   - Update `.env` file with new token
   - Restart container: `docker-compose restart`

4. **Verify token scopes:**
   - Token must have `repo` and `workflow` scopes selected
   - Regenerate if scopes are missing

### Problem: "Failed to trigger GitHub Pages update: 403 Forbidden"

**Symptoms:**
```
[ERROR] Failed to trigger GitHub Pages update: 403 Forbidden
[ERROR] Resource not accessible by integration
```

**Diagnosis:**
- Rate limit exceeded (unlikely with 1000/hour limit)
- Token doesn't have access to repository
- Repository or workflow doesn't exist

**Solutions:**

1. **Check rate limit status:**
   ```powershell
   $token = "ghp_yourTokenHere"
   $headers = @{
       "Authorization" = "token $token"
       "Accept" = "application/vnd.github+json"
   }
   Invoke-RestMethod -Uri "https://api.github.com/rate_limit" -Headers $headers
   ```
   Check `resources.core.remaining` value.

2. **Verify repository access:**
   - Open: https://github.com/OneStepAt4time/lolstonksrss
   - Ensure you have push/admin access to repository
   - Token must belong to user with repository access

3. **Check repository name format:**
   ```env
   # WRONG formats:
   GITHUB_REPOSITORY=https://github.com/OneStepAt4time/lolstonksrss
   GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss.git
   GITHUB_REPOSITORY=OneStepAt4time\lolstonksrss

   # CORRECT format:
   GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss
   ```

4. **Wait for rate limit reset:**
   - If truly rate-limited, wait 1 hour
   - Check reset time: `X-RateLimit-Reset` header
   - Consider increasing `UPDATE_INTERVAL_MINUTES` to reduce triggers

### Problem: "Failed to trigger GitHub Pages update: 404 Not Found"

**Symptoms:**
```
[ERROR] Failed to trigger GitHub Pages update: 404 Not Found
[ERROR] Workflow file not found
```

**Diagnosis:**
- Workflow file `publish-news.yml` doesn't exist
- Repository name is incorrect
- Typo in `GITHUB_WORKFLOW_FILE` variable

**Solutions:**

1. **Verify workflow file exists:**
   - Open: https://github.com/OneStepAt4time/lolstonksrss/blob/main/.github/workflows/publish-news.yml
   - File should exist at this path

2. **Check repository name:**
   ```powershell
   # Should match exactly:
   GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss
   ```

3. **Verify workflow filename:**
   ```env
   # Default (no need to set):
   GITHUB_WORKFLOW_FILE=publish-news.yml

   # If workflow has different name:
   GITHUB_WORKFLOW_FILE=your-workflow-name.yml
   ```

4. **Clone fresh copy to verify:**
   ```powershell
   git clone https://github.com/OneStepAt4time/lolstonksrss.git temp-verify
   dir temp-verify\.github\workflows\publish-news.yml
   ```

### Problem: Workflow triggered but GitHub Pages not updating

**Symptoms:**
- Logs show: "GitHub workflow dispatch successful"
- GitHub Actions shows workflow run completed
- But live page (https://OneStepAt4time.github.io/lolstonksrss/) not updated

**Diagnosis:**
- Workflow ran but deployment step failed
- GitHub Pages not enabled in repository settings
- CDN cache delay

**Solutions:**

1. **Check workflow logs:**
   - Go to: https://github.com/OneStepAt4time/lolstonksrss/actions
   - Click on latest workflow run
   - Check "Deploy to GitHub Pages" step for errors

2. **Verify GitHub Pages enabled:**
   - Go to: https://github.com/OneStepAt4time/lolstonksrss/settings/pages
   - Source should be: "GitHub Actions"
   - URL should be: `https://OneStepAt4time.github.io/lolstonksrss/`

3. **Hard refresh browser:**
   ```
   Windows: Ctrl + F5
   Mac: Cmd + Shift + R
   ```

4. **Wait for CDN propagation:**
   - CDN can take 30-60 seconds to update globally
   - Check workflow completion time vs your refresh time

5. **Check workflow permissions:**
   - Go to: https://github.com/OneStepAt4time/lolstonksrss/settings/actions
   - Scroll to "Workflow permissions"
   - Should be: "Read and write permissions" ✅

### Problem: High latency (updates taking longer than expected)

**Symptoms:**
- Auto-sync triggering successfully
- But live page updates take 5+ minutes

**Diagnosis:**
- GitHub Actions queue congestion
- Workflow inefficiency
- CDN propagation delays

**Solutions:**

1. **Check GitHub Status:**
   - Visit: https://www.githubstatus.com/
   - Look for "Actions" or "Pages" incidents

2. **Review workflow run times:**
   - Go to: https://github.com/OneStepAt4time/lolstonksrss/actions
   - Check "Duration" column
   - Normal: 2-3 minutes
   - Slow: 5+ minutes (GitHub congestion)

3. **Optimize workflow (if consistently slow):**
   - Enable caching in workflow (already done)
   - Reduce article limit temporarily
   - Consider self-hosted runners (advanced)

4. **Accept normal latency:**
   - 2-3 minutes is normal for GitHub Actions workflow
   - 30-60 seconds for CDN propagation
   - Total: ~3-4 minutes is expected and acceptable

---

## Security Best Practices

### Token Security

**DO:**
- ✅ Store token in `.env` file (excluded from Git via `.gitignore`)
- ✅ Use minimal required scopes (`repo` and `workflow` only)
- ✅ Set token expiration (60-90 days recommended)
- ✅ Rotate tokens regularly (every 90 days)
- ✅ Revoke immediately if compromised
- ✅ Use unique token per server/environment
- ✅ Store backup copy in password manager

**DON'T:**
- ❌ Commit token to Git repository
- ❌ Share token in email, chat, or messages
- ❌ Use "no expiration" tokens in production
- ❌ Grant unnecessary scopes (admin, delete, etc.)
- ❌ Reuse token across multiple servers
- ❌ Store token in unencrypted text files
- ❌ Include token in screenshots or recordings

### Monitoring Token Usage

**GitHub Token Activity:**
1. Go to: https://github.com/settings/tokens
2. Click on your token
3. View "Recent activity" section
4. Check for:
   - Unexpected API calls
   - Unusual timestamps (3 AM, etc.)
   - Unfamiliar IP addresses

**Set Up Email Notifications:**
1. Go to: https://github.com/settings/notifications
2. Enable "Actions" notifications
3. Choose "Email" for failed workflows
4. You'll be alerted if workflow fails unexpectedly

### Token Rotation Procedure

**Every 90 days (or when compromised):**

1. **Generate new token:**
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Name: "LoL Stonks RSS - Windows Server (2025-03-01)"
   - Scopes: `repo` + `workflow`
   - Expiration: 90 days
   - Copy new token: `ghp_NEW_TOKEN_HERE`

2. **Update .env file:**
   ```powershell
   cd D:\lolstonksrss
   notepad .env

   # Replace old token with new:
   GITHUB_TOKEN=ghp_NEW_TOKEN_HERE
   ```

3. **Restart container:**
   ```powershell
   docker-compose restart
   ```

4. **Verify new token works:**
   ```powershell
   docker logs lolstonksrss --tail 50
   # Look for: "GitHub workflow dispatch successful"
   ```

5. **Revoke old token:**
   - Go to: https://github.com/settings/tokens
   - Find old token (check "Note" field)
   - Click "Delete"
   - Confirm deletion

6. **Set calendar reminder:**
   - Set reminder for 90 days from now
   - Subject: "Rotate LoL Stonks RSS GitHub token"

### Backup and Recovery

**Backup Token Securely:**
```powershell
# Option 1: Export to encrypted file
$token = "ghp_yourToken"
$token | ConvertTo-SecureString -AsPlainText -Force | ConvertFrom-SecureString | Out-File D:\secure\github-token.txt

# Option 2: Save to password manager
# Use 1Password, LastPass, Bitwarden, etc.
```

**If Token Lost:**
1. Token cannot be retrieved (GitHub doesn't show it again)
2. Generate new token (follow Step 1 instructions)
3. Update configuration and restart
4. Old token still works until you revoke it

**If Token Compromised:**
1. **Immediately revoke:** https://github.com/settings/tokens → Delete
2. Generate new token with different name
3. Update configuration
4. Review repository audit log for suspicious activity
5. Consider changing repository visibility temporarily

### Windows Server Security

**File Permissions:**
```powershell
# Restrict .env file access to Administrators only
icacls D:\lolstonksrss\.env /inheritance:r
icacls D:\lolstonksrss\.env /grant:r Administrators:F
```

**Firewall Rules:**
```powershell
# Ensure port 8000 is only accessible from trusted IPs
# (if exposing publicly)
netsh advfirewall firewall add rule name="LoL RSS - Allow Trusted IPs" dir=in action=allow protocol=TCP localport=8000 remoteip=YOUR_TRUSTED_IP
```

**Docker Security:**
- Keep Docker Desktop updated
- Use non-root user in container (already configured)
- Enable Docker Content Trust for image verification
- Regularly scan images for vulnerabilities

---

## Testing the Integration

### Manual Test (Recommended)

**Step-by-step testing:**

1. **Enable feature in .env:**
   ```powershell
   cd D:\lolstonksrss
   notepad .env

   # Ensure these lines exist:
   ENABLE_GITHUB_PAGES_SYNC=true
   GITHUB_TOKEN=ghp_yourToken
   GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss
   ```

2. **Restart container:**
   ```powershell
   docker-compose restart
   ```

3. **Verify feature enabled in logs:**
   ```powershell
   docker logs lolstonksrss --tail 50

   # Look for:
   [INFO] GitHub Pages sync enabled (repository: OneStepAt4time/lolstonksrss)
   ```

4. **Wait for next scheduled update:**
   - Updates run every 5 minutes
   - Check current time: `Get-Date`
   - Wait maximum 5 minutes for next update cycle

5. **Monitor logs in real-time:**
   ```powershell
   docker logs lolstonksrss -f

   # Expected output when new articles found:
   [INFO] Update complete: 3 new articles, 0 duplicates
   [INFO] GitHub Pages update triggered (new_articles=3)
   [INFO] GitHub workflow dispatch successful (status=204)
   ```

6. **Verify workflow triggered on GitHub:**
   - Open: https://github.com/OneStepAt4time/lolstonksrss/actions
   - Check latest "Publish News to GitHub Pages" run
   - Status should be: "In progress" or "Success" ✅
   - Triggered by: "windows-app"

7. **Check workflow logs:**
   - Click on workflow run
   - Find "Log trigger source" step
   - Verify shows:
     ```
     Workflow triggered by: windows-app
     Reason: new-articles-detected
     Triggered at: 2025-12-30T14:35:00Z
     ```

8. **Wait for workflow completion:**
   - Normal duration: 2-3 minutes
   - Status changes to: "Success" ✅

9. **Verify GitHub Pages updated:**
   - Open: https://OneStepAt4time.github.io/lolstonksrss/
   - Hard refresh: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
   - Check timestamp on page
   - Verify latest articles appear

10. **Confirm end-to-end latency:**
    - Note: Time workflow started (from GitHub Actions page)
    - Note: Time page was updated (from page footer timestamp)
    - Calculate: Should be ~3-4 minutes total

### Automated Test Script (PowerShell)

Save as `test-github-integration.ps1`:

```powershell
# Test GitHub Pages Integration
Write-Host "Testing GitHub Pages Integration..." -ForegroundColor Cyan

# 1. Check environment variables
Write-Host "`n1. Checking environment configuration..." -ForegroundColor Yellow
$env:ENABLE_GITHUB_PAGES_SYNC = docker exec lolstonksrss env | findstr ENABLE_GITHUB_PAGES_SYNC
$env:GITHUB_TOKEN = docker exec lolstonksrss env | findstr GITHUB_TOKEN | ForEach-Object { $_.Substring(0, 30) + "..." }
$env:GITHUB_REPOSITORY = docker exec lolstonksrss env | findstr GITHUB_REPOSITORY

Write-Host "  ENABLE_GITHUB_PAGES_SYNC: $($env:ENABLE_GITHUB_PAGES_SYNC)"
Write-Host "  GITHUB_TOKEN: $($env:GITHUB_TOKEN)"
Write-Host "  GITHUB_REPOSITORY: $($env:GITHUB_REPOSITORY)"

# 2. Test GitHub API connectivity
Write-Host "`n2. Testing GitHub API connectivity..." -ForegroundColor Yellow
$token = (docker exec lolstonksrss env | findstr GITHUB_TOKEN).Split("=")[1]
$repo = (docker exec lolstonksrss env | findstr GITHUB_REPOSITORY).Split("=")[1]

try {
    $headers = @{
        "Authorization" = "token $token"
        "Accept" = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
    }

    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo" -Headers $headers
    Write-Host "  ✅ Repository accessible: $($response.full_name)" -ForegroundColor Green
    Write-Host "  ✅ Default branch: $($response.default_branch)" -ForegroundColor Green

    # Check rate limit
    $rateLimitResponse = Invoke-RestMethod -Uri "https://api.github.com/rate_limit" -Headers $headers
    Write-Host "  ✅ Rate limit remaining: $($rateLimitResponse.resources.core.remaining)/5000" -ForegroundColor Green

} catch {
    Write-Host "  ❌ GitHub API test failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 3. Trigger test workflow
Write-Host "`n3. Triggering test workflow..." -ForegroundColor Yellow
try {
    $workflowUrl = "https://api.github.com/repos/$repo/actions/workflows/publish-news.yml/dispatches"
    $body = @{
        ref = "main"
        inputs = @{
            triggered_by = "test-script"
            reason = "integration-test"
            article_limit = "100"
        }
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri $workflowUrl -Method Post -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "  ✅ Workflow triggered successfully" -ForegroundColor Green

} catch {
    Write-Host "  ❌ Workflow trigger failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 4. Wait and check workflow status
Write-Host "`n4. Waiting for workflow to start (15 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

try {
    $runsUrl = "https://api.github.com/repos/$repo/actions/workflows/publish-news.yml/runs?per_page=1"
    $runs = Invoke-RestMethod -Uri $runsUrl -Headers $headers
    $latestRun = $runs.workflow_runs[0]

    Write-Host "  ✅ Latest workflow run: $($latestRun.status)" -ForegroundColor Green
    Write-Host "  ✅ Triggered by: $($latestRun.triggering_actor.login)" -ForegroundColor Green
    Write-Host "  ✅ Run URL: $($latestRun.html_url)" -ForegroundColor Green

} catch {
    Write-Host "  ⚠️  Could not verify workflow status" -ForegroundColor Yellow
}

Write-Host "`n✅ Integration test completed successfully!" -ForegroundColor Green
Write-Host "Check workflow progress at: https://github.com/$repo/actions" -ForegroundColor Cyan
```

**Run test:**
```powershell
.\test-github-integration.ps1
```

### Test with Python Script

Save as `test_github_api.py`:

```python
#!/usr/bin/env python3
"""Test GitHub Pages integration manually."""

import os
import sys
import requests
from datetime import datetime

# Configuration
TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO = os.getenv("GITHUB_REPOSITORY", "OneStepAt4time/lolstonksrss")
WORKFLOW_FILE = "publish-news.yml"

def test_api_connection():
    """Test basic GitHub API connectivity."""
    print("1. Testing GitHub API connection...")

    if not TOKEN:
        print("  ❌ GITHUB_TOKEN not set")
        return False

    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        # Test user endpoint
        response = requests.get("https://api.github.com/user", headers=headers)
        response.raise_for_status()
        user = response.json()
        print(f"  ✅ Authenticated as: {user['login']}")

        # Test repository access
        response = requests.get(f"https://api.github.com/repos/{REPO}", headers=headers)
        response.raise_for_status()
        repo_data = response.json()
        print(f"  ✅ Repository accessible: {repo_data['full_name']}")

        # Check rate limit
        response = requests.get("https://api.github.com/rate_limit", headers=headers)
        rate_data = response.json()
        remaining = rate_data['resources']['core']['remaining']
        print(f"  ✅ Rate limit remaining: {remaining}/5000")

        return True

    except requests.exceptions.RequestException as e:
        print(f"  ❌ API test failed: {e}")
        return False

def trigger_workflow():
    """Trigger GitHub workflow via API."""
    print("\n2. Triggering workflow...")

    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    payload = {
        "ref": "main",
        "inputs": {
            "triggered_by": "manual-test",
            "reason": "testing-integration",
            "article_limit": "100"
        }
    }

    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 204:
            print(f"  ✅ Workflow triggered successfully")
            print(f"  ✅ Timestamp: {datetime.utcnow().isoformat()}Z")
            return True
        else:
            print(f"  ❌ Unexpected status: {response.status_code}")
            print(f"  ❌ Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Trigger failed: {e}")
        return False

def check_workflow_status():
    """Check latest workflow run status."""
    print("\n3. Checking workflow status...")

    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/runs?per_page=1"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        runs = response.json()

        if runs['total_count'] == 0:
            print("  ⚠️  No workflow runs found")
            return

        latest_run = runs['workflow_runs'][0]
        print(f"  ✅ Status: {latest_run['status']}")
        print(f"  ✅ Conclusion: {latest_run.get('conclusion', 'in_progress')}")
        print(f"  ✅ URL: {latest_run['html_url']}")

    except requests.exceptions.RequestException as e:
        print(f"  ⚠️  Could not check status: {e}")

if __name__ == "__main__":
    print("Testing GitHub Pages Integration\n" + "="*40)

    if not test_api_connection():
        sys.exit(1)

    if not trigger_workflow():
        sys.exit(1)

    import time
    print("\nWaiting 10 seconds before checking status...")
    time.sleep(10)

    check_workflow_status()

    print(f"\n✅ Test completed successfully!")
    print(f"Visit: https://github.com/{REPO}/actions")
```

**Run test:**
```bash
# Using UV
uv run python test_github_api.py

# Or directly
python test_github_api.py
```

---

## FAQ

### Q: Do I need to enable this feature?

**A:** No, it's completely optional. The GitHub Actions cron schedule provides automatic updates every 5 minutes as a fallback. Enable auto-sync only if you need:
- Near real-time updates (< 3 minutes latency)
- Immediate notification to users of breaking news
- Competitive advantage in news delivery

For personal use or low-priority scenarios, the cron schedule is sufficient.

---

### Q: What happens if GitHub API is down?

**A:** The Windows application handles failures gracefully:
1. Error logged: `[ERROR] Failed to trigger GitHub Pages update: 503 Service Unavailable`
2. Application continues normally (no crash)
3. Cron schedule will trigger within 5 minutes as backup
4. No user-facing impact on RSS feed or local database

**GitHub Status:** Check https://www.githubstatus.com/ for incidents

---

### Q: How many workflow triggers can I make per hour?

**A:** GitHub limits:
- **Workflow dispatches:** 1000/hour per workflow
- **Our typical usage:** ~12/hour (one every 5 minutes if always finding new articles)
- **Percentage used:** < 2% of limit
- **Conclusion:** Well within safe limits

Even if you reduced update interval to 1 minute, you'd still only use ~60/hour (6% of limit).

---

### Q: Does this cost money?

**A:**
- **Public repositories:** GitHub Actions minutes are FREE (unlimited)
- **Private repositories:** Depends on your GitHub plan
  - Free plan: 2000 minutes/month (enough for ~16,000 workflow runs)
  - Pro plan: 3000 minutes/month
  - Team/Enterprise: More generous limits

**Our workflow duration:** ~2-3 minutes per run
**Monthly usage (public repo):** FREE (no charges)
**Monthly usage (private repo):** ~12 runs/hour × 24 hours × 30 days × 3 minutes = ~25,920 minutes (exceeds free tier)

**Recommendation:** Keep repository public for unlimited free Actions, or reduce update frequency for private repos.

---

### Q: Can I use the same token for multiple servers?

**A:** Technically yes, but **not recommended** for security reasons:

**Pros:**
- Simpler management (one token to rotate)
- Lower token count usage

**Cons:**
- ⚠️ If one server is compromised, all servers are compromised
- 🔐 Harder to track which server made which API call
- 🚫 Revoking token affects all servers simultaneously
- 📊 Difficult to debug issues (which server triggered what?)

**Best practice:** Use separate tokens:
- Name: "LoL RSS - Production Server"
- Name: "LoL RSS - Staging Server"
- Name: "LoL RSS - Development Server"

This allows you to:
- Revoke specific server access if compromised
- Track usage per environment
- Rotate tokens independently

---

### Q: What if I forget to rotate my token?

**A:** GitHub helps prevent token expiration issues:

1. **Email reminders:** GitHub sends email 7 days before expiration
2. **Token page warning:** Red banner appears on https://github.com/settings/tokens
3. **If expired:**
   - Auto-sync stops working
   - Error logged: `[ERROR] Failed to trigger GitHub Pages update: 401 Unauthorized`
   - Cron schedule continues to work (no downtime)
   - Generate new token and update `.env`

**Mitigation:**
- Set calendar reminder for 7 days before expiration
- Use password manager that alerts on expiring credentials
- Monitor error logs for 401 errors
- Consider "no expiration" token (⚠️ security risk, not recommended for production)

---

### Q: How do I disable this feature?

**A:** Three methods:

**Method 1: Environment Variable (Recommended)**
```powershell
# Edit .env file
cd D:\lolstonksrss
notepad .env

# Change to:
ENABLE_GITHUB_PAGES_SYNC=false

# Restart
docker-compose restart
```

**Method 2: Remove Token**
```powershell
# Edit .env file
notepad .env

# Comment out or remove:
# GITHUB_TOKEN=ghp_xxxxx

# Restart
docker-compose restart
```

**Method 3: Delete .env Entry**
```powershell
# Remove entire GitHub Pages section from .env
# Restart
docker-compose restart
```

**Verification:**
```powershell
docker logs lolstonksrss --tail 50
# Should NOT see: "GitHub Pages update triggered"
```

---

### Q: Can I trigger workflows for private repositories?

**A:** Yes, but with considerations:

**Requirements:**
- Token must have `repo` scope (includes private repository access)
- You must have push/admin access to the private repository
- GitHub Actions must be enabled for private repositories
- Workflow file must have proper permissions

**Differences from public repos:**
- Private repos consume GitHub Actions minutes
- May require paid GitHub plan for sufficient minutes
- Rate limits are the same (1000 dispatches/hour)

**Configuration (same as public):**
```env
ENABLE_GITHUB_PAGES_SYNC=true
GITHUB_TOKEN=ghp_yourToken  # With 'repo' scope
GITHUB_REPOSITORY=YourUsername/private-repo-name
```

---

### Q: How can I test without waiting for new articles?

**A:** Three testing approaches:

**Option 1: Manual Workflow Trigger (GitHub UI)**
1. Go to: https://github.com/OneStepAt4time/lolstonksrss/actions
2. Click "Publish News to GitHub Pages" workflow
3. Click "Run workflow" button
4. Fill in: `triggered_by` = "manual-test"
5. Click green "Run workflow" button

**Option 2: API Test Script**
```powershell
# Use the provided test scripts:
.\test-github-integration.ps1  # PowerShell
# OR
uv run python test_github_api.py  # Python
```

**Option 3: Force Update Endpoint**
```powershell
# Trigger manual update (doesn't trigger GitHub though)
curl -X POST http://localhost:8000/admin/update

# Wait for next scheduled check (max 5 minutes)
# If new articles found, GitHub will be triggered
```

**Option 4: Reduce Update Interval (Temporary)**
```env
# In .env file:
UPDATE_INTERVAL_MINUTES=1  # Check every 1 minute (temporary!)

# Restart container
docker-compose restart

# Remember to change back to 5 after testing!
```

---

### Q: What's the difference between `workflow_dispatch` and `push` events?

**A:**

| Aspect | `workflow_dispatch` (API trigger) | `push` (Git push) |
|--------|-----------------------------------|-------------------|
| **Trigger source** | API call from Windows app | Git commit pushed to main |
| **Frequency** | Every 5 min (when new articles) | Only when code changes |
| **Purpose** | Update news content | Update workflow/code |
| **Inputs supported** | Yes (`triggered_by`, `reason`, etc.) | No |
| **Use case** | Content updates (articles) | Code deployments |
| **Our implementation** | **Primary trigger** | Workflow file updates only |

Both can trigger the same workflow, but serve different purposes.

---

### Q: Can I customize the workflow inputs?

**A:** Currently, the workflow accepts:

**Standard inputs:**
```json
{
  "triggered_by": "windows-app",
  "reason": "new-articles-detected",
  "article_limit": "100"
}
```

**To add custom inputs:**

1. Edit `.github/workflows/publish-news.yml`:
```yaml
workflow_dispatch:
  inputs:
    triggered_by:
      description: 'Source that triggered this workflow'
      required: false
      default: 'manual'
      type: string

    # Add your custom input:
    custom_category:
      description: 'Filter by category'
      required: false
      default: 'all'
      type: string
```

2. Update Windows app code to pass custom input (requires code modification)

3. Use input in workflow steps:
```yaml
- name: Use custom input
  run: |
    echo "Category filter: ${{ github.event.inputs.custom_category }}"
```

**Note:** Requires modifying application source code (advanced).

---

## Performance Impact

### Windows Server Resource Usage

**Additional resources consumed by auto-sync feature:**

| Resource | Impact | Notes |
|----------|--------|-------|
| **Memory** | < 1 MB | HTTP client in memory |
| **CPU** | < 0.1% | Negligible, only during API call |
| **Network** | ~2 KB/request | HTTPS POST + response |
| **Disk I/O** | None | No additional disk operations |
| **Response time** | +200-500ms | Added to update cycle |

**Total impact:** Negligible for modern servers (< 0.1% resource overhead)

### GitHub Actions Impact

**Workflow execution:**

| Metric | Without Auto-Sync | With Auto-Sync | Change |
|--------|------------------|----------------|--------|
| **Workflow runs/hour** | 12 (cron only) | Up to 24 (cron + API) | +100% |
| **Average runs/hour** | 12 | ~15 (only triggers on new articles) | +25% |
| **Minutes consumed/hour** | 36 min (12 × 3 min) | ~45 min (15 × 3 min) | +25% |
| **Monthly minutes (public)** | FREE (unlimited) | FREE (unlimited) | No cost |
| **Monthly minutes (private)** | ~25,920 min | ~32,400 min | +25% |

**Conclusion:**
- Public repositories: No impact (unlimited free Actions)
- Private repositories: 25% increase in Actions minutes usage
- Still well within rate limits (using < 2% of 1000/hour limit)

### Network Latency Comparison

**Update cycle timeline:**

| Event | Cron Only | With Auto-Sync | Time Saved |
|-------|-----------|----------------|------------|
| Windows app finds new articles | 0:00 | 0:00 | - |
| GitHub workflow triggered | 0:00-5:00 (avg 2:30) | 0:00 (immediate) | ~2.5 min |
| Workflow completes | +3:00 | +3:00 | - |
| Pages updated | +0:30 | +0:30 | - |
| **Total latency** | **0:00-8:30** (avg 6:00) | **3:30** | **~2.5 min (42% faster)** |

**User-facing improvement:** Articles appear on live page **2-3 minutes faster** on average.

### Optimization Recommendations

**For Windows Server:**
```env
# Already optimized (no changes needed):
UPDATE_INTERVAL_MINUTES=5  # Good balance
CACHE_TTL_SECONDS=21600    # 6 hours
HTTP_TIMEOUT_SECONDS=30    # Reasonable
```

**For GitHub Actions:**
```yaml
# Already optimized in workflow:
- Uses caching (pip, UV dependencies)
- Parallel steps where possible
- Shallow git clone (fetch-depth: 1)
- Efficient Python 3.11
```

**If experiencing performance issues:**
1. **Increase update interval:** `UPDATE_INTERVAL_MINUTES=10` (reduces triggers)
2. **Reduce article limit:** `article_limit=50` (faster HTML generation)
3. **Monitor GitHub Status:** https://www.githubstatus.com/ (check for incidents)
4. **Check server resources:** `docker stats lolstonksrss`

---

## Rollback Procedure

If you need to disable the auto-sync feature or revert to cron-only updates:

### Step 1: Disable Feature

**Option A: Keep token, disable feature**
```powershell
cd D:\lolstonksrss
notepad .env

# Change:
ENABLE_GITHUB_PAGES_SYNC=false

# Save and close
```

**Option B: Remove token entirely**
```powershell
cd D:\lolstonksrss
notepad .env

# Delete or comment out lines:
# ENABLE_GITHUB_PAGES_SYNC=true
# GITHUB_TOKEN=ghp_xxxxx
# GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss

# Save and close
```

### Step 2: Restart Container

```powershell
# Stop container
docker-compose down

# Start container with new config
docker-compose up -d
```

### Step 3: Verify Rollback

```powershell
# Check logs (should NOT see GitHub trigger messages)
docker logs lolstonksrss --tail 50

# Expected: No "GitHub Pages update triggered" messages
# Expected: Application runs normally
```

### Step 4: (Optional) Revoke GitHub Token

If you're permanently disabling the feature:

1. **Go to GitHub Token Page:**
   - https://github.com/settings/tokens

2. **Find Your Token:**
   - Look for "LoL Stonks RSS - Windows Server" in "Personal access tokens (classic)"

3. **Delete Token:**
   - Click token name
   - Scroll down
   - Click "Delete" button (red)
   - Confirm deletion

4. **Verify Token Revoked:**
   - Token disappears from list
   - Any future API calls with this token will fail (expected)

### Step 5: Confirm Cron Schedule Still Working

The GitHub Actions cron schedule runs independently:

1. **Wait for next cron trigger** (max 5 minutes)

2. **Check GitHub Actions:**
   - https://github.com/OneStepAt4time/lolstonksrss/actions
   - Latest run should show: "Triggered by: schedule" (not "windows-app")

3. **Verify Pages Updated:**
   - https://OneStepAt4time.github.io/lolstonksrss/
   - Should still update every 5 minutes via cron

### Rollback Checklist

- [ ] `.env` file updated (`ENABLE_GITHUB_PAGES_SYNC=false` or lines removed)
- [ ] Docker container restarted (`docker-compose down && docker-compose up -d`)
- [ ] Logs verified (no "GitHub Pages update triggered" messages)
- [ ] (Optional) GitHub token revoked
- [ ] Cron schedule confirmed working (check GitHub Actions page)
- [ ] Live news page still updating (check https://OneStepAt4time.github.io/lolstonksrss/)

### Re-enabling Later

To re-enable the feature:

1. Generate new GitHub token (or use existing if not revoked)
2. Update `.env` file: `ENABLE_GITHUB_PAGES_SYNC=true`
3. Add `GITHUB_TOKEN=ghp_xxxxx`
4. Restart container: `docker-compose restart`
5. Verify in logs: "GitHub Pages sync enabled"

---

## Support

### Getting Help

**Documentation:**
- **This guide:** `docs/GITHUB_PAGES_INTEGRATION.md`
- **GitHub Pages setup:** `docs/SETUP_GITHUB_PAGES.md`
- **GitHub Pages automation:** `docs/GITHUB_PAGES_NEWS.md`
- **Windows deployment:** `docs/WINDOWS_DEPLOYMENT.md`
- **Main README:** `README.md`

**Community:**
- **GitHub Issues:** https://github.com/OneStepAt4time/lolstonksrss/issues
- **GitHub Discussions:** https://github.com/OneStepAt4time/lolstonksrss/discussions
- **GitHub Actions Status:** https://www.githubstatus.com/

### Reporting Issues

When reporting problems with GitHub Pages integration:

**Include this information:**

1. **Environment:**
   ```
   - Windows version: (e.g., Windows Server 2019)
   - Docker version: (run: docker --version)
   - Repository: OneStepAt4time/lolstonksrss
   - Feature enabled: true/false
   ```

2. **Configuration:**
   ```env
   # From .env file (REMOVE ACTUAL TOKEN):
   ENABLE_GITHUB_PAGES_SYNC=true
   GITHUB_TOKEN=ghp_xxxxx... (REDACTED)
   GITHUB_REPOSITORY=OneStepAt4time/lolstonksrss
   ```

3. **Error logs:**
   ```powershell
   # Run and paste output:
   docker logs lolstonksrss --tail 100 2>&1 | findstr /I "github error warning"
   ```

4. **GitHub workflow status:**
   - Latest workflow run URL from: https://github.com/OneStepAt4time/lolstonksrss/actions
   - Workflow status: In progress / Failed / Success
   - Error message from workflow logs (if failed)

5. **Steps to reproduce:**
   - What you did
   - What you expected to happen
   - What actually happened

**⚠️ SECURITY WARNING:** Never include your actual GitHub token in issue reports!

### Common Resources

**GitHub Documentation:**
- [Workflow dispatch events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch)
- [GitHub Pages deployment](https://docs.github.com/en/pages/getting-started-with-github-pages)
- [Personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [REST API reference](https://docs.github.com/en/rest/actions/workflows)

**Troubleshooting Tools:**
- **GitHub Status:** https://www.githubstatus.com/
- **Docker Status:** `docker ps`, `docker logs`, `docker stats`
- **Network Test:** `Test-NetConnection github.com -Port 443` (PowerShell)
- **API Test:** Use provided `test-github-integration.ps1` or `test_github_api.py` scripts

### Feature Requests

Have an idea to improve the GitHub Pages integration?

1. Check existing issues/discussions first
2. Open a new discussion: https://github.com/OneStepAt4time/lolstonksrss/discussions
3. Describe your use case and expected benefit
4. Tag with "enhancement" label

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-30 | Initial documentation release |

---

## Related Documentation

- [GitHub Pages Quick Start](../GITHUB_PAGES_QUICKSTART.md) - 5-minute setup guide
- [GitHub Pages Setup](SETUP_GITHUB_PAGES.md) - Step-by-step GitHub Pages configuration
- [GitHub Pages News Automation](GITHUB_PAGES_NEWS.md) - Complete automation documentation
- [Windows Deployment Guide](WINDOWS_DEPLOYMENT.md) - Full Windows Server deployment
- [Main README](../README.md) - Project overview

---

*Last Updated: 2025-12-30*
*Version: 1.0.0*
*Maintained by: LoL Stonks RSS Team*

---

**Built with ❤️ for the League of Legends community**
*Not affiliated with Riot Games*
