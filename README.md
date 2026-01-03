# LoL Stonks RSS

```
 _           _   ____  _              _          ____  ____ ____
| |    ___  | | / ___|| |_ ___  _ __ | | _____  |  _ \/ ___/ ___|
| |   / _ \ | | \___ \| __/ _ \| '_ \| |/ / __| | |_) \___ \___ \
| |__| (_) || |  ___) | || (_) | | | |   <\__ \ |  _ < ___) |__) |
|_____\___/ |_| |____/ \__\___/|_| |_|_|\_\___/ |_| \_\____/____/

```

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![Coverage](https://img.shields.io/badge/coverage-90%2B-brightgreen.svg)](docs/COVERAGE_REPORT.md)
[![Tests](https://img.shields.io/badge/tests-638%20passed-brightgreen.svg)](docs/TESTING_SUMMARY.md)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Live News](https://img.shields.io/badge/live-news%20page-gold.svg)](https://OneStepAt4time.github.io/lolstonksrss/)
[![News Updates](https://img.shields.io/github/actions/workflow/status/OneStepAt4time/lolstonksrss/publish-news.yml?label=news%20updates)](https://github.com/OneStepAt4time/lolstonksrss/actions/workflows/publish-news.yml)

> A production-ready, containerized RSS feed generator for League of Legends news. Automatically fetches official LoL news and generates RSS 2.0 compliant feeds with multi-language support. Designed for Windows Server deployment with Docker.

**[View Live News Page](https://OneStepAt4time.github.io/lolstonksrss/)** - Automatically updated every 5 minutes

---

## Overview

**LoL Stonks RSS** is a Python-based application that transforms League of Legends news into accessible RSS feeds. It scrapes official Riot Games news endpoints, stores articles in a local database, and serves them as standardized RSS 2.0 XML feeds via a FastAPI web server.

### Key Features

- **Automatic News Fetching** - Fetches latest LoL news from official Riot Games API
- **Live News Page** - [Beautiful HTML news page](https://OneStepAt4time.github.io/lolstonksrss/) updated every 5 minutes via GitHub Actions
- **RSS 2.0 Compliant** - Generates standards-compliant RSS feeds compatible with all readers
- **Multi-Language Support** - All 20 Riot locales (EN-US, EN-GB, ES-ES, ES-MX, FR-FR, DE-DE, IT-IT, PT-BR, RU-RU, TR-TR, PL-PL, JA-JP, KO-KR, ZH-CN, ZH-TW, AR-AE, VI-VN, TH-TH, ID-ID, PH-PH)
- **Smart Caching** - Intelligent caching strategy with configurable TTL for optimal performance
- **Periodic Updates** - Automatic background updates every 5 minutes (configurable)
- **Docker Deployment** - Fully containerized with multi-stage builds and health checks
- **Windows Server Ready** - Optimized for Windows Server with PowerShell automation scripts
- **High Test Coverage** - 90%+ test coverage with 638 passing tests (unit, integration, E2E, performance)
- **RESTful API** - Full-featured FastAPI server with interactive documentation
- **Production Hardened** - Non-root execution, health checks, graceful shutdown, error handling

### Live Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>League of Legends News</title>
    <link>https://www.leagueoflegends.com/news</link>
    <description>Latest League of Legends news and updates</description>
    <item>
      <title>New Champion: Briar, the Restrained Hunger</title>
      <link>https://www.leagueoflegends.com/en-us/news/...</link>
      <pubDate>Sat, 02 Sep 2023 14:00:00 +0000</pubDate>
      <guid>https://www.leagueoflegends.com/en-us/news/...</guid>
      <category>Champions</category>
      <category>Game Updates</category>
      <description>Meet Briar, a damaged, bloodthirsty monster...</description>
    </item>
  </channel>
</rss>
```

---

## Quick Start

### One-Command Deployment (Windows)

```powershell
# Clone repository
git clone https://github.com/OneStepAt4time/lolstonksrss.git
cd lolstonksrss

# Deploy with one command (requires Docker Desktop)
.\scripts\windows-deploy.ps1
```

Your RSS feed will be available at:
- **Main Feed**: http://localhost:8000/feed.xml (all locales, ~1500 articles)
- **Locale Feeds**: http://localhost:8000/rss/{locale}.xml (20 locales available)
- **Examples**:
  - EN-US: http://localhost:8000/rss/en-us.xml
  - IT-IT: http://localhost:8000/rss/it-it.xml
  - JA-JP: http://localhost:8000/rss/ja-jp.xml
  - KO-KR: http://localhost:8000/rss/ko-kr.xml
- **API Docs**: http://localhost:8000/docs
- **Live News Page**: [https://OneStepAt4time.github.io/lolstonksrss/](https://OneStepAt4time.github.io/lolstonksrss/) (auto-updated every 5 min)

### Docker Compose (Cross-Platform)

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Manual Docker

```bash
# Build image
docker build -t lolstonksrss:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -v ./data:/app/data \
  --name lolstonksrss \
  lolstonksrss:latest
```

### Native Python (Development)

```bash
# Install dependencies with UV (recommended)
uv sync

# Or use pip (legacy)
pip install -r requirements.txt

# Run server with UV
uv run python main.py

# Or run directly
python main.py
```

---

## Available Feeds

### RSS Feeds

The application provides feeds for all 20 Riot locales. Each locale fetches ~75 articles from official Riot Games sources.

| Feed URL | Description | Language | Articles |
|----------|-------------|----------|----------|
| `/feed.xml` | All articles (all locales) | Mixed | ~1500 |
| `/rss/en-us.xml` | English (US) | EN-US | ~75 |
| `/rss/en-gb.xml` | English (UK) | EN-GB | ~75 |
| `/rss/es-es.xml` | Spanish (Spain) | ES-ES | ~75 |
| `/rss/es-mx.xml` | Spanish (Latin America) | ES-MX | ~75 |
| `/rss/fr-fr.xml` | French | FR-FR | ~75 |
| `/rss/de-de.xml` | German | DE-DE | ~75 |
| `/rss/it-it.xml` | Italian | IT-IT | ~75 |
| `/rss/pt-br.xml` | Portuguese (Brazil) | PT-BR | ~75 |
| `/rss/ru-ru.xml` | Russian | RU-RU | ~75 |
| `/rss/tr-tr.xml` | Turkish | TR-TR | ~75 |
| `/rss/pl-pl.xml` | Polish | PL-PL | ~75 |
| `/rss/ja-jp.xml` | Japanese | JA-JP | ~75 |
| `/rss/ko-kr.xml` | Korean | KO-KR | ~75 |
| `/rss/zh-cn.xml` | Chinese (Simplified) | ZH-CN | ~75 |
| `/rss/zh-tw.xml` | Chinese (Traditional) | ZH-TW | ~75 |
| `/rss/ar-ae.xml` | Arabic | AR-AE | ~75 |
| `/rss/vi-vn.xml` | Vietnamese | VI-VN | ~75 |
| `/rss/th-th.xml` | Thai | TH-TH | ~75 |
| `/rss/id-id.xml` | Indonesian | ID-ID | ~75 |
| `/rss/ph-ph.xml` | Filipino | PH-PH | ~75 |

**Usage**: Replace `{locale}` in the URL pattern `/rss/{locale}.xml` with any of the locale codes above.

### Live News Page

**[Live News Page](https://OneStepAt4time.github.io/lolstonksrss/)** - Beautiful, responsive HTML page with:
- Latest 100 articles from all sources
- LoL-themed design with dark/light mode
- Real-time filtering by source, category, or search
- Auto-refresh every 5 minutes
- Mobile-friendly responsive layout
- Updated automatically via GitHub Actions every 5 minutes

[Learn more about the news page automation](docs/GITHUB_PAGES_NEWS.md)

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root (redirects to docs) |
| `/health` | GET | Health check (database, scheduler status) |
| `/feed.xml` | GET | Main RSS feed (all articles) |
| `/rss/{locale}.xml` | GET | Locale-specific RSS feed (20 locales) |
| `/api/articles` | GET | List all articles (JSON) |
| `/api/articles/{id}` | GET | Get specific article (JSON) |
| `/admin/scheduler/status` | GET | Scheduler status |
| `/admin/update` | POST | Force immediate update |
| `/docs` | GET | Interactive API documentation (Swagger) |
| `/redoc` | GET | Alternative API docs (ReDoc) |

---

## Installation

### Prerequisites

**For Docker Deployment (Recommended):**
- Windows Server 2019+ or Windows 10/11
- Docker Desktop for Windows
- 4GB RAM minimum (8GB recommended)
- 20GB disk space

**For Native Python Development:**
- Python 3.11 or higher
- UV package manager (recommended) or pip
- 2GB RAM minimum
- 10GB disk space

### Docker Installation (Recommended)

1. **Install Docker Desktop**
   ```powershell
   # Download from: https://www.docker.com/products/docker-desktop
   # Or use winget:
   winget install Docker.DockerDesktop
   ```

2. **Clone Repository**
   ```powershell
   git clone https://github.com/OneStepAt4time/lolstonksrss.git
   cd lolstonksrss
   ```

3. **Deploy**
   ```powershell
   .\scripts\windows-deploy.ps1
   ```

### Manual Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/OneStepAt4time/lolstonksrss.git
   cd lolstonksrss
   ```

2. **Install Dependencies**
   ```bash
   # Using UV (recommended)
   uv sync

   # Or using pip (legacy)
   pip install -r requirements.txt
   ```

3. **Configure Environment** (Optional)
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

4. **Run Application**
   ```bash
   python main.py
   ```

### Configuration

All settings are configured via environment variables or `.env` file:

```env
# Database
DATABASE_PATH=data/articles.db

# API Configuration
LOL_NEWS_BASE_URL=https://www.leagueoflegends.com
SUPPORTED_LOCALES=en-us,it-it

# Caching (in seconds)
CACHE_TTL_SECONDS=21600           # 6 hours
BUILD_ID_CACHE_SECONDS=86400      # 24 hours
FEED_CACHE_TTL=300                # 5 minutes

# RSS Feed Settings
RSS_FEED_TITLE=League of Legends News
RSS_FEED_DESCRIPTION=Latest League of Legends news and updates
RSS_MAX_ITEMS=50

# Server
BASE_URL=http://localhost:8000
HOST=0.0.0.0
PORT=8000
RELOAD=false                      # Set to true for development

# Security
ALLOWED_ORIGINS=http://localhost:8000  # Comma-separated CORS origins
HTTP_TIMEOUT_SECONDS=30                # Timeout for external requests

# Updates
UPDATE_INTERVAL_MINUTES=5        # How often to fetch new articles

# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
```

See `.env.example` for complete configuration reference.

---

## Security

### Built-in Security Features

- **CORS Protection**: Configurable allowed origins (default: localhost only)
- **Rate Limiting**: Admin endpoints limited to 5 requests/minute per IP
- **Input Validation**: Category parameters validated against injection attacks
- **HTTP Timeouts**: 30-second timeout on external requests prevents hangs
- **Non-root Docker**: Container runs as non-privileged user (UID 1000)
- **No Hardcoded Secrets**: All configuration via environment variables

### Production Security Checklist

Before deploying to production:

- [ ] Set `ALLOWED_ORIGINS` to your actual domain(s)
- [ ] Configure firewall rules to restrict access
- [ ] Enable HTTPS/TLS with reverse proxy (nginx, Traefik)
- [ ] Review and adjust rate limiting as needed
- [ ] Implement backup strategy for database
- [ ] Set up monitoring and alerting
- [ ] Review Docker security settings
- [ ] Configure log rotation

### CORS Configuration

**Development**:
```env
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:3000
```

**Production**:
```env
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Rate Limiting

Admin endpoints are rate-limited to prevent abuse:
- `/admin/refresh`: 5 requests/minute per IP
- `/admin/scheduler/trigger`: 5 requests/minute per IP

Exceeding the limit returns HTTP 429 (Too Many Requests).

### Reporting Security Issues

If you discover a security vulnerability, please email security@example.com (do not use public issues).

---

## Usage

### Starting the Server

**With Docker:**
```powershell
docker-compose up -d
```

**Native Python:**
```bash
# With UV
uv run python main.py

# Or directly
python main.py
```

Server starts on `http://localhost:8000` by default.

### Accessing Feeds

**RSS Readers (Feedly, Inoreader, etc.):**
```
http://your-server:8000/feed.xml
http://your-server:8000/rss/en-us.xml
http://your-server:8000/rss/it-it.xml
```

**Command Line:**
```bash
# View RSS feed
curl http://localhost:8000/feed.xml

# View JSON articles
curl http://localhost:8000/api/articles

# Health check
curl http://localhost:8000/health
```

### Admin Operations

**Force Update:**
```bash
curl -X POST http://localhost:8000/admin/update
```

**Check Scheduler Status:**
```bash
curl http://localhost:8000/admin/scheduler/status
```

**View Interactive Docs:**
Open browser to: http://localhost:8000/docs

### Health Monitoring

```powershell
# Start monitoring (PowerShell)
.\scripts\monitor.ps1

# Monitor with logging
.\scripts\monitor.ps1 -LogFile "C:\logs\lolrss.log"

# Custom interval (30 seconds)
.\scripts\monitor.ps1 -IntervalSeconds 30
```

---

## Documentation

### Quick References
- [Quick Start Guide](QUICKSTART.md) - Development setup and first steps
- [Deployment Quick Start](DEPLOYMENT_QUICKSTART.md) - Fast production deployment
- [GitHub Pages Quick Start](GITHUB_PAGES_QUICKSTART.md) - Live news page in 5 minutes
- [Project Summary](PROJECT_SUMMARY.md) - Complete project overview

### Comprehensive Guides
- [Windows Deployment Guide](docs/WINDOWS_DEPLOYMENT.md) - Complete Windows Server deployment
- [GitHub Pages Setup](docs/SETUP_GITHUB_PAGES.md) - Step-by-step GitHub Pages configuration
- [GitHub Pages Documentation](docs/GITHUB_PAGES_NEWS.md) - Complete automation documentation
- [Docker Reference](docs/DOCKER.md) - Docker configuration and commands
- [Production Checklist](docs/PRODUCTION_CHECKLIST.md) - Pre-deployment verification
- [Testing Guide](docs/TESTING_GUIDE.md) - Testing strategy and execution

### Technical Documentation
- [API Discovery Report](docs/api-discovery-report.md) - LoL News API research
- [Coverage Report](docs/COVERAGE_REPORT.md) - Test coverage details (92%)
- [Testing Summary](docs/TESTING_SUMMARY.md) - QA phase results (151 tests)
- [Scripts Documentation](scripts/README.md) - PowerShell automation scripts

### Phase Completion Reports
- [Phase 2: Foundation](docs/phase-2-foundation-complete.md) - Core models and database
- [Phase 3: API Client](docs/phase3-completion-report.md) - News fetching
- [Phase 4: RSS Generation](docs/PHASE4_RSS_GENERATION.md) - Feed generation
- [Phase 5: Server Integration](PHASE5_COMPLETE.md) - FastAPI server
- [Phase 6: Scheduler](docs/PHASE6_SCHEDULER.md) - Automated updates
- [Phase 7: Deployment](PHASE7_COMPLETE.md) - Docker and Windows
- [Phase 8: QA](docs/PHASE_8_QA_SUMMARY.md) - Testing and validation

---

## Technology Stack

### Core Technologies
- **Python 3.11+** - Modern Python with type hints
- **FastAPI 0.104.1** - High-performance async web framework
- **SQLite** - Embedded database with aiosqlite async driver
- **feedgen 1.0.0** - RSS 2.0 feed generation
- **APScheduler 3.10.4** - Background task scheduling
- **Docker** - Containerization and deployment

### Key Libraries
- **httpx 0.25.2** - Async HTTP client for API calls
- **pydantic 2.5.2** - Data validation and settings management
- **uvicorn 0.24.0** - ASGI server for FastAPI
- **feedparser 6.0.11** - RSS feed validation
- **python-dateutil 2.8.2** - Date/time utilities

### Development Tools
- **pytest 7.4.3** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **black 23.12.0** - Code formatting
- **mypy 1.7.1** - Static type checking
- **ruff 0.1.7** - Fast Python linter

---

## Architecture

### System Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌─────────────────┐            │
│  │ APScheduler  │─────>│ Update Service  │            │
│  │ (30 min)     │      │                 │            │
│  └──────────────┘      └────────┬────────┘            │
│                                  │                      │
│                                  v                      │
│  ┌──────────────┐      ┌─────────────────┐            │
│  │ LoL News API │<────>│  API Client     │            │
│  │ (Riot Games) │      │  (httpx)        │            │
│  └──────────────┘      └────────┬────────┘            │
│                                  │                      │
│                                  v                      │
│  ┌──────────────┐      ┌─────────────────┐            │
│  │  SQLite DB   │<────>│  Repository     │            │
│  │  (Articles)  │      │  (aiosqlite)    │            │
│  └──────────────┘      └────────┬────────┘            │
│                                  │                      │
│                                  v                      │
│  ┌──────────────┐      ┌─────────────────┐            │
│  │  TTL Cache   │<────>│  Feed Service   │            │
│  │  (5 min)     │      │  (feedgen)      │            │
│  └──────────────┘      └────────┬────────┘            │
│                                  │                      │
│                                  v                      │
│  ┌─────────────────────────────────────────┐          │
│  │         FastAPI Application             │          │
│  │  /feed.xml  /health  /api  /admin       │          │
│  └─────────────────┬───────────────────────┘          │
│                    │                                    │
└────────────────────┼────────────────────────────────────┘
                     │
                     v
              HTTP Port 8000
                     │
                     v
         ┌───────────────────────┐
         │    RSS Readers        │
         │   (Users/Services)    │
         └───────────────────────┘
```

### Component Responsibilities

- **APScheduler**: Triggers periodic updates (default: 5 minutes)
- **Update Service**: Orchestrates news fetching and storage
- **API Client**: Fetches news from Riot Games official endpoints
- **Repository**: Manages article persistence (SQLite with async)
- **Feed Service**: Generates RSS 2.0 XML feeds with caching
- **FastAPI App**: Serves HTTP endpoints and manages lifecycle
- **TTL Cache**: In-memory caching for improved performance

### Data Flow

1. **Scheduled Update** - APScheduler triggers update every 5 minutes
2. **API Fetch** - API Client fetches latest news from Riot Games
3. **Database Storage** - Articles saved to SQLite (upsert, no duplicates)
4. **RSS Generation** - Feed Service creates RSS XML from database
5. **Cache** - Generated feeds cached for 5 minutes
6. **HTTP Response** - FastAPI serves cached or fresh RSS to clients

---

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/OneStepAt4time/lolstonksrss.git
cd lolstonksrss

# Install dependencies with UV (recommended)
uv sync --all-extras

# Or use pip (legacy)
pip install -r requirements.txt

# Run tests with UV
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS/Linux
start htmlcov\index.html # Windows
```

### Code Quality Tools

```bash
# Format code with black
uv run black src/ tests/

# Type checking with mypy
uv run mypy src/

# Linting with ruff
uv run ruff check src/ tests/

# Fix linting issues
uv run ruff check --fix src/ tests/
```

### Running Tests

```bash
# All tests (245 tests, ~17 seconds)
uv run pytest

# Fast tests only (~6 seconds)
uv run pytest -m "not slow"

# Unit tests only
uv run pytest tests/ -k "not integration and not e2e and not performance"

# Integration tests
uv run pytest tests/integration/

# E2E tests
uv run pytest tests/e2e/

# Performance tests
uv run pytest tests/performance/

# Specific test file
uv run pytest tests/test_api.py -v

# With coverage report
uv run pytest --cov=src --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=src --cov-report=html
```

### Project Structure

```
lolstonksrss/
├── src/                           # Source code
│   ├── api/                       # FastAPI application
│   │   └── app.py                 # Endpoints and server
│   ├── rss/                       # RSS generation
│   │   ├── generator.py           # RSS XML builder
│   │   └── feed_service.py        # Feed business logic
│   ├── services/                  # Background services
│   │   ├── scheduler.py           # APScheduler wrapper
│   │   └── update_service.py      # Update orchestration
│   ├── utils/                     # Utilities
│   │   └── cache.py               # TTL cache
│   ├── api_client.py              # LoL News API client
│   ├── config.py                  # Configuration
│   ├── database.py                # SQLite repository
│   └── models.py                  # Data models
├── tests/                         # Test suite
│   ├── integration/               # Integration tests
│   ├── e2e/                       # End-to-end tests
│   ├── performance/               # Performance benchmarks
│   ├── validation/                # RSS compliance tests
│   └── test_*.py                  # Unit tests
├── docs/                          # Documentation
├── scripts/                       # Automation scripts
│   ├── windows-deploy.ps1         # Deployment automation
│   ├── monitor.ps1                # Health monitoring
│   └── backup.ps1                 # Backup automation
├── examples/                      # Usage examples
├── data/                          # Database storage (created at runtime)
├── main.py                        # Application entry point
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Docker image definition
├── docker-compose.yml             # Docker Compose config
├── .env.example                   # Environment template
└── README.md                      # This file
```

---

## Deployment

### Production Deployment (Windows Server)

**Complete guide**: [docs/WINDOWS_DEPLOYMENT.md](docs/WINDOWS_DEPLOYMENT.md)

```powershell
# 1. Install Docker Desktop for Windows
winget install Docker.DockerDesktop

# 2. Clone repository
git clone https://github.com/OneStepAt4time/lolstonksrss.git
cd lolstonksrss

# 3. Configure environment
cp .env.example .env
# Edit .env with production settings

# 4. Deploy with automation script
.\scripts\windows-deploy.ps1

# 5. Verify deployment
curl http://localhost:8000/health

# 6. Setup monitoring
.\scripts\monitor.ps1 -LogFile "C:\logs\lolrss.log"
```

### Docker Compose Deployment

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Update and redeploy
git pull
docker-compose up -d --build
```

### Manual Docker Deployment

```bash
# Build image
docker build -t lolstonksrss:latest .

# Run container
docker run -d \
  --name lolstonksrss \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e UPDATE_INTERVAL_MINUTES=5 \
  --restart unless-stopped \
  lolstonksrss:latest

# View logs
docker logs -f lolstonksrss

# Stop container
docker stop lolstonksrss

# Start container
docker start lolstonksrss
```

### Production Checklist

Before deploying to production, verify:

- [ ] Docker Desktop installed and running
- [ ] Port 8000 available (or configured differently)
- [ ] Firewall rules configured
- [ ] `.env` file configured with production values
- [ ] Data directory has proper permissions
- [ ] Health check endpoint accessible
- [ ] Backup strategy implemented
- [ ] Monitoring configured
- [ ] Log rotation setup
- [ ] SSL/TLS configured (if public-facing)

See [docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md) for complete checklist.

---

## Management & Maintenance

### Backup

```powershell
# Standard backup (stops container)
.\scripts\backup.ps1

# Hot backup (no downtime)
.\scripts\backup.ps1 -SkipStop

# Custom retention (keep 60 days)
.\scripts\backup.ps1 -KeepDays 60

# Custom backup location
.\scripts\backup.ps1 -BackupPath "E:\backups\lolrss"
```

### Monitoring

```powershell
# Start health monitoring
.\scripts\monitor.ps1

# Monitor with logging
.\scripts\monitor.ps1 -LogFile "C:\logs\health.log"

# Custom check interval (60 seconds)
.\scripts\monitor.ps1 -IntervalSeconds 60

# Email alerts on failure (requires configuration)
.\scripts\monitor.ps1 -AlertEmail admin@example.com
```

### Updates

```powershell
# Pull latest code
git pull origin main

# Rebuild and redeploy
docker-compose up -d --build

# Or use deployment script
.\scripts\windows-deploy.ps1
```

### Log Management

```bash
# View container logs
docker logs lolstonksrss

# Follow logs in real-time
docker logs -f lolstonksrss

# Last 100 lines
docker logs --tail 100 lolstonksrss

# Logs since specific time
docker logs --since "2025-12-29T10:00:00" lolstonksrss
```

---

## Performance

### Resource Usage

**Expected resource consumption:**
- **Memory**: 100-150MB
- **CPU**: <5% during normal operation
- **Disk**: ~500MB (Docker image + database)
- **Network**: Minimal (periodic API calls)

### Response Times

**Benchmarked performance:**
- **Health Check**: <100ms
- **RSS Feed (cached)**: <50ms
- **RSS Feed (fresh)**: <500ms
- **API Endpoints**: <100ms
- **Full Update Cycle**: ~3-5 seconds

### Optimization Tips

- Increase `FEED_CACHE_TTL` for better performance (trade-off: staleness)
- Reduce `UPDATE_INTERVAL_MINUTES` for fresher data (trade-off: more API calls)
- Adjust `RSS_MAX_ITEMS` based on your needs (50 is optimal for most cases)
- Use Redis for caching in high-traffic scenarios (requires code modification)

---

## Troubleshooting

### Common Issues

**Port 8000 already in use:**
```powershell
# Use different port
docker run -p 8001:8000 lolstonksrss:latest

# Or configure in .env
PORT=8001
```

**Database locked error:**
```bash
# Ensure only one instance is running
docker ps | grep lolstonksrss

# Stop all instances
docker stop $(docker ps -q --filter ancestor=lolstonksrss)
```

**Container won't start:**
```bash
# Check logs
docker logs lolstonksrss

# Verify Docker is running
docker info

# Remove and recreate container
docker rm -f lolstonksrss
docker-compose up -d
```

**Feed not updating:**
```bash
# Check scheduler status
curl http://localhost:8000/admin/scheduler/status

# Force manual update
curl -X POST http://localhost:8000/admin/update

# Check logs for errors
docker logs lolstonksrss | grep ERROR
```

**API rate limiting:**
```env
# Increase cache TTL to reduce API calls
CACHE_TTL_SECONDS=43200  # 12 hours
BUILD_ID_CACHE_SECONDS=86400  # 24 hours
```

See [docs/WINDOWS_DEPLOYMENT.md#troubleshooting](docs/WINDOWS_DEPLOYMENT.md#troubleshooting) for more solutions.

---

## Contributing

Contributions are welcome! This project follows standard open-source practices.

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
   - Write tests for new features
   - Ensure all tests pass (`pytest`)
   - Follow code style (`black`, `mypy`, `ruff`)
4. **Commit your changes**
   ```bash
   git commit -m "Add amazing feature"
   ```
5. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Code Standards

- **Python**: PEP 8 compliant, type hints required
- **Testing**: Maintain 90%+ coverage
- **Documentation**: Update relevant docs
- **Commits**: Clear, descriptive commit messages

### Development Workflow

```bash
# Setup development environment
pip install -r requirements.txt

# Run tests before committing
pytest

# Check code quality
black src/ tests/
mypy src/
ruff check src/ tests/

# Run full validation
pytest --cov=src --cov-report=term-missing
```

---

## Support

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/OneStepAt4time/lolstonksrss/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OneStepAt4time/lolstonksrss/discussions)
- **Documentation**: See [docs/](docs/) directory

### Reporting Bugs

When reporting bugs, please include:
- OS and version (Windows Server 2019, etc.)
- Docker version (`docker --version`)
- Python version (`python --version`)
- Error logs (`docker logs lolstonksrss`)
- Steps to reproduce
- Expected vs actual behavior

### Feature Requests

Feature requests are welcome! Please:
- Check existing issues first
- Describe the use case
- Explain the expected benefit
- Consider implementation complexity

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

### Third-Party Licenses

This project uses the following open-source libraries:
- **FastAPI** - MIT License
- **feedgen** - BSD License
- **httpx** - BSD License
- **pydantic** - MIT License
- **pytest** - MIT License

See individual package licenses in `requirements.txt`.

---

## Acknowledgments

### Credits

- **Riot Games** - For League of Legends and official news API
- **FastAPI** - Excellent async web framework
- **feedgen** - Robust RSS generation library
- **Python Community** - Amazing ecosystem and tools

### Inspiration

This project was inspired by the need for standardized RSS feeds for League of Legends news, making it easier for fans and content creators to stay updated.

### Contributors

Thanks to all contributors who have helped improve this project!

---

## Project Status

**Current Version**: 1.0.0
**Status**: Production Ready
**Last Updated**: 2025-12-29

### Completed Phases

- [x] Phase 1-2: Foundation (models, database, config)
- [x] Phase 3: API Client (news fetching)
- [x] Phase 4: RSS Generation (feedgen integration)
- [x] Phase 5: Server Integration (FastAPI, scheduler)
- [x] Phase 6: Testing (92% coverage, 151 tests)
- [x] Phase 7: Docker & Windows Deployment
- [x] Phase 8: QA & Validation

### Roadmap

**Future Enhancements:**
- [ ] Additional language support (ES, FR, DE, etc.)
- [ ] Category-based feed filtering
- [ ] ATOM feed format support
- [ ] Webhook notifications on new articles
- [ ] Admin dashboard UI
- [ ] Prometheus metrics export
- [ ] Redis caching for high-traffic deployments
- [ ] Multi-source aggregation (PBE news, esports, etc.)

---

## Statistics

- **Total Code**: ~3,500 lines of Python
- **Test Coverage**: 92.36%
- **Total Tests**: 151 (all passing)
- **Documentation**: 15+ comprehensive guides
- **Supported Languages**: 2 (EN-US, IT-IT)
- **API Endpoints**: 10+
- **Docker Image Size**: ~200MB (multi-stage build)
- **Average Response Time**: <100ms

---

<p align="center">
  <strong>Built with ❤️ for the League of Legends community</strong><br>
  <sub>Not affiliated with Riot Games</sub>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#deployment">Deployment</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#support">Support</a>
</p>
