# Configuration Guide

Complete reference for configuring the LoL Stonks RSS application.

## Table of Contents

- [Configuration Overview](#configuration-overview)
- [Environment Variables Reference](#environment-variables-reference)
- [Configuration File (.env)](#configuration-file-env)
- [Docker Configuration](#docker-configuration)
- [Production Configuration](#production-configuration)
- [Development Configuration](#development-configuration)
- [Advanced Configuration](#advanced-configuration)
- [Configuration Validation](#configuration-validation)
- [Configuration Examples](#configuration-examples)
- [Configuration Migration](#configuration-migration)
- [Troubleshooting](#troubleshooting)

---

## Configuration Overview

The application uses **pydantic-settings** for type-safe configuration management with support for environment variables and `.env` files.

### Configuration Methods

The application supports three configuration methods (in priority order):

1. **Environment Variables** (highest priority)
   - Set directly in the system or Docker container
   - Override all other configuration methods
   - Case-insensitive (e.g., `DATABASE_PATH` or `database_path`)

2. **.env File** (medium priority)
   - Located at project root: `D:\lolstonksrss\.env`
   - Loaded automatically on startup
   - UTF-8 encoding required

3. **Default Values** (lowest priority)
   - Defined in `src/config.py`
   - Used when no override is provided
   - Suitable for development

### Configuration Priority Example

```
DATABASE_PATH environment variable: /custom/path/db.sqlite
.env file: DATABASE_PATH=data/articles.db
Default value: data/articles.db

Result: /custom/path/db.sqlite (environment variable wins)
```

### Configuration Class

All configuration is managed by the `Settings` class in `src/config.py`:

```python
from src.config import get_settings

settings = get_settings()  # Returns cached Settings instance
print(settings.database_path)
```

The `get_settings()` function uses LRU cache to ensure only one Settings instance exists throughout the application lifecycle.

---

## Environment Variables Reference

### Application Settings

#### `BASE_URL`
- **Type**: String
- **Default**: `http://localhost:8000`
- **Description**: Base URL for generating RSS feed links and absolute URLs
- **Example**: `https://lol-rss.example.com`
- **Required**: No
- **Production**: Should be set to your domain/IP

#### `HOST`
- **Type**: String
- **Default**: `0.0.0.0`
- **Description**: Server bind address (0.0.0.0 = all interfaces)
- **Example**: `127.0.0.1` (localhost only)
- **Required**: No
- **Production**: Keep as `0.0.0.0` for Docker

#### `PORT`
- **Type**: Integer
- **Default**: `8000`
- **Description**: HTTP server port
- **Example**: `8080`, `3000`
- **Required**: No
- **Production**: Ensure port mapping matches Docker configuration

#### `LOG_LEVEL`
- **Type**: String
- **Default**: `INFO`
- **Description**: Logging verbosity level
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Required**: No
- **Production**: `INFO` or `WARNING`
- **Development**: `DEBUG`

#### `RELOAD`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable auto-reload on code changes (uvicorn hot reload)
- **Options**: `true`, `false`
- **Required**: No
- **Production**: `false` (performance overhead)
- **Development**: `true` (faster iteration)

---

### Database Settings

#### `DATABASE_PATH`
- **Type**: String
- **Default**: `data/articles.db`
- **Description**: Path to SQLite database file (relative or absolute)
- **Example**: `/app/data/articles.db`, `D:\data\lol.db`
- **Required**: No
- **Notes**:
  - Directory is created automatically if missing
  - Must be writable by application user
  - Use absolute paths in Docker containers

---

### API Settings

#### `LOL_NEWS_BASE_URL`
- **Type**: String
- **Default**: `https://www.leagueoflegends.com`
- **Description**: Base URL for League of Legends news website
- **Required**: No
- **Notes**: Should not be changed unless LoL website moves

#### `SUPPORTED_LOCALES`
- **Type**: Comma-separated list
- **Default**: `en-us,it-it`
- **Description**: List of locale codes to fetch news from
- **Example**: `en-us,it-it,fr-fr,de-de`
- **Required**: No
- **Available Locales**:
  - `en-us` - English (United States)
  - `it-it` - Italian (Italy)
  - `fr-fr` - French (France)
  - `de-de` - German (Germany)
  - `es-es` - Spanish (Spain)
  - `ko-kr` - Korean (South Korea)
  - `ja-jp` - Japanese (Japan)
  - And many more...
- **Notes**: More locales = longer update times

---

### Cache Settings

#### `CACHE_TTL_SECONDS`
- **Type**: Integer
- **Default**: `21600` (6 hours)
- **Description**: Cache TTL for article data
- **Example**: `3600` (1 hour), `86400` (24 hours)
- **Required**: No
- **Notes**: Longer TTL = less API calls, staler data

#### `BUILD_ID_CACHE_SECONDS`
- **Type**: Integer
- **Default**: `86400` (24 hours)
- **Description**: Cache TTL for Next.js build ID from LoL website
- **Example**: `43200` (12 hours)
- **Required**: No
- **Notes**: Build ID changes infrequently, safe to cache long-term

#### `FEED_CACHE_TTL`
- **Type**: Integer
- **Default**: `300` (5 minutes)
- **Description**: Cache TTL for generated RSS feeds (in seconds)
- **Example**: `60` (1 minute), `600` (10 minutes)
- **Required**: No
- **Notes**:
  - Shorter TTL = fresher feeds, more CPU usage
  - Longer TTL = faster responses, staler feeds
  - Recommended: 300-600 seconds

---

### Scheduler Settings

#### `UPDATE_INTERVAL_MINUTES`
- **Type**: Integer
- **Default**: `5`
- **Description**: Interval between automatic news updates (in minutes)
- **Example**: `10` (every 10 minutes), `15` (every 15 minutes), `30` (every 30 minutes)
- **Required**: No
- **Recommendations**:
  - Production: 5-15 minutes (default: 5)
  - Development: 5-10 minutes
  - High-traffic: 5-10 minutes
- **Notes**: Shorter intervals = more API load, fresher content

---

### RSS Feed Settings

#### `RSS_FEED_TITLE`
- **Type**: String
- **Default**: `League of Legends News`
- **Description**: Default RSS feed title (legacy, use locale-specific titles)
- **Required**: No

#### `RSS_FEED_DESCRIPTION`
- **Type**: String
- **Default**: `Latest League of Legends news and updates`
- **Description**: Default RSS feed description (legacy)
- **Required**: No

#### `RSS_FEED_LINK`
- **Type**: String
- **Default**: `https://www.leagueoflegends.com/news`
- **Description**: Feed's homepage link
- **Required**: No

#### `RSS_MAX_ITEMS`
- **Type**: Integer
- **Default**: `50`
- **Description**: Maximum articles in main RSS feed
- **Example**: `100`, `200`
- **Required**: No
- **Notes**: Higher values = larger feed file sizes

#### `FEED_TITLE_EN`
- **Type**: String
- **Default**: `League of Legends News`
- **Description**: English feed title
- **Required**: No

#### `FEED_TITLE_IT`
- **Type**: String
- **Default**: `Notizie League of Legends`
- **Description**: Italian feed title
- **Required**: No

#### `FEED_DESCRIPTION_EN`
- **Type**: String
- **Default**: `Latest League of Legends news and updates`
- **Description**: English feed description
- **Required**: No

#### `FEED_DESCRIPTION_IT`
- **Type**: String
- **Default**: `Ultime notizie e aggiornamenti di League of Legends`
- **Description**: Italian feed description
- **Required**: No

---

## Configuration File (.env)

### Creating .env File

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit with your preferred editor:
   ```bash
   notepad .env       # Windows
   nano .env          # Linux/Mac
   ```

### .env File Template

Complete annotated `.env.example`:

```bash
# ============================================================================
# LoL Stonks RSS - Configuration File
# ============================================================================
# This file contains all configuration options for the application.
# Copy this file to .env and customize as needed.
# Environment variables override these settings.
# ============================================================================

# ----------------------------------------------------------------------------
# Database Configuration
# ----------------------------------------------------------------------------
# Path to SQLite database file (relative or absolute)
# Directory is created automatically if missing
DATABASE_PATH=data/articles.db

# ----------------------------------------------------------------------------
# LoL News API Configuration
# ----------------------------------------------------------------------------
# Base URL for League of Legends news website
LOL_NEWS_BASE_URL=https://www.leagueoflegends.com

# Supported locales (comma-separated, no spaces)
# Available: en-us, it-it, fr-fr, de-de, es-es, ko-kr, ja-jp, etc.
SUPPORTED_LOCALES=en-us,it-it

# ----------------------------------------------------------------------------
# Caching Configuration (seconds)
# ----------------------------------------------------------------------------
# Cache TTL for article data (default: 6 hours)
CACHE_TTL_SECONDS=21600

# Cache TTL for Next.js build ID (default: 24 hours)
BUILD_ID_CACHE_SECONDS=86400

# Cache TTL for generated RSS feeds (default: 5 minutes)
FEED_CACHE_TTL=300

# ----------------------------------------------------------------------------
# RSS Feed Configuration
# ----------------------------------------------------------------------------
# Default feed metadata (legacy)
RSS_FEED_TITLE=League of Legends News
RSS_FEED_DESCRIPTION=Latest LoL news and updates
RSS_FEED_LINK=https://www.leagueoflegends.com/news

# Maximum number of items in RSS feed
RSS_MAX_ITEMS=50

# Multi-language feed titles
FEED_TITLE_EN=League of Legends News
FEED_TITLE_IT=Notizie League of Legends

# Multi-language feed descriptions
FEED_DESCRIPTION_EN=Latest League of Legends news and updates
FEED_DESCRIPTION_IT=Ultime notizie e aggiornamenti di League of Legends

# ----------------------------------------------------------------------------
# Server Configuration
# ----------------------------------------------------------------------------
# Base URL for generating RSS feed links (set to your domain in production)
BASE_URL=http://localhost:8000

# Server bind address (0.0.0.0 = all interfaces, 127.0.0.1 = localhost only)
HOST=0.0.0.0

# HTTP server port
PORT=8000

# Auto-reload on code changes (true for development, false for production)
RELOAD=false

# ----------------------------------------------------------------------------
# Update Scheduling
# ----------------------------------------------------------------------------
# Interval between automatic news updates (minutes)
# Recommended: 5-15 for production, 5-10 for development
UPDATE_INTERVAL_MINUTES=5

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
# DEBUG: Verbose logging for development
# INFO: Standard logging for production
# WARNING: Only warnings and errors
LOG_LEVEL=INFO
```

### .env File Best Practices

1. **Never commit .env to version control**
   - Already in `.gitignore`
   - Contains environment-specific settings
   - May contain sensitive data in the future

2. **Use comments liberally**
   - Document what each setting does
   - Provide example values
   - Note production vs development recommendations

3. **Keep .env.example up to date**
   - Update when adding new settings
   - Remove deprecated settings
   - Include helpful defaults

4. **Validate syntax**
   - No spaces around `=` sign
   - No quotes needed for simple values
   - Use quotes for values with spaces: `TITLE="My RSS Feed"`

---

## Docker Configuration

### Environment Variables in docker-compose.yml

The `docker-compose.yml` file includes environment variables for container configuration:

```yaml
services:
  lolstonksrss:
    environment:
      # Database
      - DATABASE_PATH=/app/data/articles.db

      # Server
      - HOST=0.0.0.0
      - PORT=8000
      - BASE_URL=http://localhost:8000
      - LOG_LEVEL=INFO

      # Scheduling
      - UPDATE_INTERVAL_MINUTES=5

      # RSS Configuration
      - RSS_FEED_TITLE=League of Legends News
      - RSS_FEED_DESCRIPTION=Latest LoL news and updates
      - RSS_MAX_ITEMS=50

      # Caching
      - CACHE_TTL_SECONDS=21600
      - BUILD_ID_CACHE_SECONDS=86400
      - FEED_CACHE_TTL=300

      # Locales
      - SUPPORTED_LOCALES=en-us,it-it
```

### Volume Configuration

The application requires a persistent volume for the database:

```yaml
volumes:
  # Windows-style volume mount
  - type: bind
    source: ./data
    target: /app/data
```

**Windows-specific notes:**
- Use `./data` (relative path) or `D:\lolstonksrss\data` (absolute path)
- Ensure directory exists before starting: `mkdir data`
- Directory must be writable by container user (UID 1000)

### Network Configuration

Default bridge network for container isolation:

```yaml
networks:
  lolrss_network:
    driver: bridge
```

### Resource Limits (Optional)

Add resource limits to prevent overconsumption:

```yaml
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

### Health Check Configuration

Built-in health check for monitoring:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Logging Configuration

JSON file logging with rotation:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

This keeps last 3 log files of max 10MB each (30MB total).

---

## Production Configuration

### Recommended Production Settings

Create a production `.env` file:

```bash
# Production Configuration

# Database
DATABASE_PATH=/app/data/articles.db

# Server (use your actual domain)
BASE_URL=https://lol-rss.example.com
HOST=0.0.0.0
PORT=8000
RELOAD=false

# Logging (less verbose)
LOG_LEVEL=WARNING

# Update schedule (balanced)
UPDATE_INTERVAL_MINUTES=5

# Caching (optimized for performance)
CACHE_TTL_SECONDS=21600
BUILD_ID_CACHE_SECONDS=86400
FEED_CACHE_TTL=300

# RSS (reasonable limits)
RSS_MAX_ITEMS=50

# Locales (add as needed)
SUPPORTED_LOCALES=en-us,it-it
```

### Security Considerations

1. **Use HTTPS for BASE_URL**
   ```bash
   BASE_URL=https://lol-rss.example.com
   ```

2. **Restrict host binding (if not using Docker)**
   ```bash
   HOST=127.0.0.1  # Only accept local connections
   ```

3. **Set appropriate log level**
   ```bash
   LOG_LEVEL=WARNING  # Avoid logging sensitive data
   ```

4. **Secure file permissions**
   ```bash
   chmod 600 .env
   chmod 755 data/
   chmod 644 data/articles.db
   ```

5. **Configure firewall**
   - Only expose PORT (8000) if needed
   - Use reverse proxy (nginx, Caddy) for HTTPS

### Performance Tuning

1. **Optimize cache TTLs**
   ```bash
   # Balance freshness vs performance
   FEED_CACHE_TTL=600          # 10 minutes (less frequent regeneration)
   CACHE_TTL_SECONDS=43200     # 12 hours (longer article cache)
   BUILD_ID_CACHE_SECONDS=86400 # 24 hours (build ID rarely changes)
   ```

2. **Adjust update interval**
   ```bash
   UPDATE_INTERVAL_MINUTES=15  # Less frequent updates (reduce API load)
   ```

3. **Limit RSS items**
   ```bash
   RSS_MAX_ITEMS=50  # Smaller feeds = faster generation
   ```

4. **Use specific locales only**
   ```bash
   SUPPORTED_LOCALES=en-us  # Only English (fastest updates)
   ```

### Monitoring Configuration

1. **Enable INFO logging for monitoring**
   ```bash
   LOG_LEVEL=INFO
   ```

2. **Set up health check monitoring**
   - Monitor `/health` endpoint
   - Alert if status != "healthy"

3. **Track metrics**
   - Response times
   - Cache hit rates
   - Update durations
   - Article counts

### Backup Configuration

1. **Database backup location**
   ```bash
   # Ensure data directory is backed up
   DATABASE_PATH=/app/data/articles.db
   ```

2. **Automated backup script**
   ```bash
   # Backup data directory daily
   cp -r ./data ./backups/data-$(date +%Y%m%d)
   ```

---

## Development Configuration

### Recommended Development Settings

Create a development `.env` file:

```bash
# Development Configuration

# Database
DATABASE_PATH=data/articles.db

# Server
BASE_URL=http://localhost:8000
HOST=0.0.0.0
PORT=8000
RELOAD=true  # Hot reload enabled

# Logging (verbose)
LOG_LEVEL=DEBUG

# Update schedule (default for development)
UPDATE_INTERVAL_MINUTES=5

# Caching (shorter TTLs for testing)
CACHE_TTL_SECONDS=3600         # 1 hour
BUILD_ID_CACHE_SECONDS=7200    # 2 hours
FEED_CACHE_TTL=60              # 1 minute

# RSS
RSS_MAX_ITEMS=50

# Locales (fewer for faster development)
SUPPORTED_LOCALES=en-us
```

### Development Features

1. **Hot Reload**
   ```bash
   RELOAD=true
   ```
   - Automatically restarts server on code changes
   - Faster development iteration
   - Uses more CPU (disabled in production)

2. **Debug Logging**
   ```bash
   LOG_LEVEL=DEBUG
   ```
   - Verbose output for troubleshooting
   - Shows cache hits/misses
   - Logs all HTTP requests
   - Performance overhead (disabled in production)

3. **Shorter Cache TTLs**
   ```bash
   FEED_CACHE_TTL=60  # Test cache expiration quickly
   ```

4. **Default Update Frequency**
   ```bash
   UPDATE_INTERVAL_MINUTES=5  # Test scheduler behavior with default
   ```

### Local Development Without Docker

Run directly with Python:

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit for local development
# Set DATABASE_PATH=data/articles.db
# Set RELOAD=true
# Set LOG_LEVEL=DEBUG

# Run server
python main.py
```

---

## Advanced Configuration

### Custom Locales

Add additional language support:

```bash
# Add French and German
SUPPORTED_LOCALES=en-us,it-it,fr-fr,de-de

# Asia-Pacific region
SUPPORTED_LOCALES=en-us,ko-kr,ja-jp,zh-tw

# All major regions
SUPPORTED_LOCALES=en-us,it-it,fr-fr,de-de,es-es,ko-kr,ja-jp
```

**Note**: Each locale requires a separate API call during updates. More locales = longer update times.

### Custom Feed Titles (Multi-language)

Add titles for new locales:

```bash
# Add French
FEED_TITLE_FR=Actualités League of Legends
FEED_DESCRIPTION_FR=Dernières nouvelles et mises à jour de League of Legends

# Add German
FEED_TITLE_DE=League of Legends Neuigkeiten
FEED_DESCRIPTION_DE=Neueste League of Legends Nachrichten und Updates
```

**Implementation Note**: Currently requires code changes in `src/rss/feed_service.py` to use these new variables. Future enhancement planned.

### Extended Caching Strategy

Fine-tune cache behavior:

```bash
# Aggressive caching (high traffic, tolerate stale data)
FEED_CACHE_TTL=900              # 15 minutes
CACHE_TTL_SECONDS=86400         # 24 hours
BUILD_ID_CACHE_SECONDS=172800   # 48 hours

# Minimal caching (low traffic, prefer freshness)
FEED_CACHE_TTL=60               # 1 minute
CACHE_TTL_SECONDS=3600          # 1 hour
BUILD_ID_CACHE_SECONDS=7200     # 2 hours
```

### Custom Database Location

Use external storage or specific paths:

```bash
# Windows absolute path
DATABASE_PATH=D:\data\lol-rss\articles.db

# Linux absolute path
DATABASE_PATH=/mnt/storage/lol-rss/articles.db

# Docker named volume
DATABASE_PATH=/app/data/articles.db
```

### Multiple Environments

Use environment-specific files:

```bash
# .env.development
cp .env.example .env.development
# Edit for development settings

# .env.production
cp .env.example .env.production
# Edit for production settings

# .env.staging
cp .env.example .env.staging
# Edit for staging settings
```

Load specific environment:

```bash
# Symlink approach
ln -s .env.production .env

# Or use docker-compose.override.yml
```

---

## Configuration Validation

### Validating Configuration

The application validates configuration on startup using Pydantic:

```python
from src.config import get_settings

try:
    settings = get_settings()
    print("Configuration valid!")
except Exception as e:
    print(f"Configuration error: {e}")
```

### Configuration Check Script

Create `check_config.py`:

```python
#!/usr/bin/env python3
"""Configuration validation script."""

import sys
from src.config import get_settings

def check_config():
    """Validate configuration and print summary."""
    try:
        settings = get_settings()

        print("Configuration Validation")
        print("=" * 50)
        print(f"Database Path: {settings.database_path}")
        print(f"Server: {settings.host}:{settings.port}")
        print(f"Base URL: {settings.base_url}")
        print(f"Log Level: {settings.log_level}")
        print(f"Locales: {', '.join(settings.supported_locales)}")
        print(f"Update Interval: {settings.update_interval_minutes} min")
        print(f"Feed Cache TTL: {settings.feed_cache_ttl}s")
        print("=" * 50)
        print("Configuration valid!")
        return 0

    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(check_config())
```

Run validation:

```bash
python check_config.py
```

### Common Configuration Errors

#### 1. Invalid Port Number

```bash
PORT=invalid  # Error: not an integer
```

**Solution**:
```bash
PORT=8000
```

#### 2. Invalid Log Level

```bash
LOG_LEVEL=VERBOSE  # Error: invalid level
```

**Solution**:
```bash
LOG_LEVEL=DEBUG  # Valid: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

#### 3. Invalid Locale Format

```bash
SUPPORTED_LOCALES=en-us it-it  # Error: comma-separated expected
```

**Solution**:
```bash
SUPPORTED_LOCALES=en-us,it-it
```

#### 4. Non-existent Database Path

```bash
DATABASE_PATH=/nonexistent/path/db.sqlite  # Error: directory doesn't exist
```

**Solution**: Application creates parent directories automatically, but ensure path is writable.

#### 5. Port Already in Use

```bash
PORT=8000  # Error: port already bound
```

**Solution**:
```bash
# Use different port
PORT=8001

# Or stop other service using port 8000
```

---

## Configuration Examples

### Example 1: Minimal Configuration

Minimal `.env` for quick start:

```bash
# Minimal configuration (uses mostly defaults)
BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
```

All other settings use defaults from `src/config.py`.

### Example 2: Production Configuration

Complete production setup:

```bash
# Production Configuration - lol-rss.example.com

# Database
DATABASE_PATH=/app/data/articles.db

# Server
BASE_URL=https://lol-rss.example.com
HOST=0.0.0.0
PORT=8000
RELOAD=false

# Logging
LOG_LEVEL=WARNING

# API
LOL_NEWS_BASE_URL=https://www.leagueoflegends.com
SUPPORTED_LOCALES=en-us,it-it,fr-fr,de-de

# Caching
CACHE_TTL_SECONDS=21600
BUILD_ID_CACHE_SECONDS=86400
FEED_CACHE_TTL=600

# RSS
RSS_MAX_ITEMS=50
FEED_TITLE_EN=League of Legends News
FEED_TITLE_IT=Notizie League of Legends
FEED_DESCRIPTION_EN=Latest League of Legends news and updates
FEED_DESCRIPTION_IT=Ultime notizie e aggiornamenti di League of Legends

# Scheduling
UPDATE_INTERVAL_MINUTES=5
```

### Example 3: High-Performance Configuration

Optimized for high traffic:

```bash
# High-Performance Configuration

# Aggressive caching
FEED_CACHE_TTL=900              # 15 minutes
CACHE_TTL_SECONDS=43200         # 12 hours
BUILD_ID_CACHE_SECONDS=86400    # 24 hours

# Minimal locales for faster updates
SUPPORTED_LOCALES=en-us

# Longer update intervals
UPDATE_INTERVAL_MINUTES=60

# Smaller feeds
RSS_MAX_ITEMS=30

# Less verbose logging
LOG_LEVEL=WARNING
```

### Example 4: Development Configuration

Full development setup:

```bash
# Development Configuration

# Database
DATABASE_PATH=data/articles.db

# Server
BASE_URL=http://localhost:8000
HOST=0.0.0.0
PORT=8000
RELOAD=true

# Logging
LOG_LEVEL=DEBUG

# API
LOL_NEWS_BASE_URL=https://www.leagueoflegends.com
SUPPORTED_LOCALES=en-us

# Caching (short TTLs for testing)
CACHE_TTL_SECONDS=3600
BUILD_ID_CACHE_SECONDS=7200
FEED_CACHE_TTL=60

# RSS
RSS_MAX_ITEMS=50

# Scheduling (default updates)
UPDATE_INTERVAL_MINUTES=5
```

### Example 5: Multi-Language Configuration

Support all major regions:

```bash
# Multi-Language Configuration

# All major locales
SUPPORTED_LOCALES=en-us,it-it,fr-fr,de-de,es-es,ko-kr,ja-jp

# Multi-language feed metadata
FEED_TITLE_EN=League of Legends News
FEED_TITLE_IT=Notizie League of Legends
FEED_DESCRIPTION_EN=Latest League of Legends news and updates
FEED_DESCRIPTION_IT=Ultime notizie e aggiornamenti di League of Legends

# Longer update intervals (more API calls)
UPDATE_INTERVAL_MINUTES=60

# Higher item limit
RSS_MAX_ITEMS=100
```

---

## Configuration Migration

### Upgrading Configuration

When upgrading the application, check for new configuration options:

1. **Compare .env with .env.example**
   ```bash
   diff .env .env.example
   ```

2. **Add new settings to .env**
   ```bash
   # Copy new settings from .env.example
   # Add with default values
   ```

3. **Remove deprecated settings**
   ```bash
   # Check changelog for deprecated options
   # Remove from .env
   ```

### Backwards Compatibility

The application maintains backwards compatibility for configuration:

- **Deprecated settings**: Warnings logged, old values still work
- **New settings**: Have sensible defaults, optional to set
- **Breaking changes**: Documented in changelog with migration guide

### Migration Example: v1.0 to v2.0

Hypothetical migration example:

```bash
# Old configuration (v1.0)
UPDATE_INTERVAL=1800  # seconds

# New configuration (v2.0)
UPDATE_INTERVAL_MINUTES=5  # minutes (default changed to 5)
```

Migration steps:
1. Convert seconds to minutes: `1800 / 60 = 30` (old default was 30, new is 5)
2. Update .env: `UPDATE_INTERVAL_MINUTES=5` (or your preferred value)
3. Remove old setting: `UPDATE_INTERVAL`

### Configuration Version Tracking

Document configuration version in .env:

```bash
# Configuration version: 1.0
# Last updated: 2025-12-29
# Application version: 1.0.0
```

---

## Troubleshooting

### Configuration Not Loading

**Symptom**: Settings use defaults despite .env file

**Checks**:
1. Verify .env file location (must be at project root)
2. Check .env file encoding (must be UTF-8)
3. Verify no syntax errors (run validation script)
4. Check environment variables aren't overriding
5. Restart application to reload configuration

**Debug**:
```python
from src.config import get_settings
settings = get_settings()
print(settings.model_dump())  # Print all settings
```

### Invalid Configuration Values

**Symptom**: Validation errors on startup

**Solution**:
1. Check error message for specific field
2. Verify value type (int vs string)
3. Ensure valid options (e.g., log levels)
4. Check for typos in variable names

**Example**:
```bash
# Error: LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL
LOG_LEVEL=VERBOSE

# Fix:
LOG_LEVEL=DEBUG
```

### Environment Variable Priority Issues

**Symptom**: .env changes not taking effect

**Cause**: Environment variables override .env file

**Solution**:
1. Check system environment variables
2. Check docker-compose.yml environment section
3. Unset or update environment variables

**Check environment**:
```bash
# Windows
echo %DATABASE_PATH%

# Linux/Mac
echo $DATABASE_PATH

# Unset
unset DATABASE_PATH  # Linux/Mac
set DATABASE_PATH=   # Windows
```

### Permission Issues

**Symptom**: Cannot write to database

**Solution**:
1. Check directory permissions
2. Ensure parent directories exist
3. Verify Docker user has write access

**Fix permissions**:
```bash
# Create directory
mkdir -p data

# Set permissions
chmod 755 data/

# Docker: ensure volume is writable
docker-compose down
rm -rf data/
mkdir data/
docker-compose up
```

### Port Already in Use

**Symptom**: Cannot bind to port

**Solution**:
1. Check what's using the port
2. Change PORT in configuration
3. Stop conflicting service

**Check port usage**:
```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000

# Use different port
PORT=8001
```

### Cache Not Working

**Symptom**: Feeds regenerating every request

**Solution**:
1. Check FEED_CACHE_TTL is set
2. Verify TTL is > 0
3. Check logs for cache errors

**Debug caching**:
```bash
# Enable debug logging
LOG_LEVEL=DEBUG

# Check logs for "Cache hit" or "Cache miss"
```

### Database Lock Errors

**Symptom**: Database is locked errors

**Solution**:
1. Ensure only one instance running
2. Check for zombie processes
3. Restart application

**Fix**:
```bash
# Stop all instances
docker-compose down

# Remove lock files
rm data/articles.db-journal

# Restart
docker-compose up
```

---

## Getting Help

### Configuration Resources

- **Source Code**: `src/config.py` - Configuration class definition
- **Example File**: `.env.example` - Complete configuration template
- **Docker Config**: `docker-compose.yml` - Container configuration
- **Documentation**: This file - Complete reference

### Reporting Configuration Issues

When reporting configuration issues, include:

1. **Environment**:
   - OS (Windows/Linux/Mac)
   - Docker version
   - Python version

2. **Configuration**:
   - Contents of .env (redact sensitive data)
   - Environment variables set
   - docker-compose.yml if modified

3. **Error**:
   - Full error message
   - Stack trace
   - Logs with DEBUG level

4. **Steps to Reproduce**:
   - What you changed
   - What you expected
   - What actually happened

---

## Summary

This configuration guide covers all aspects of configuring the LoL Stonks RSS application:

- **Configuration Methods**: Environment variables, .env file, defaults
- **All Settings**: Complete reference for every configuration option
- **Docker Integration**: Container-specific configuration
- **Environment-specific**: Production, development, and custom setups
- **Troubleshooting**: Common issues and solutions
- **Best Practices**: Security, performance, and maintenance

For quick start, copy `.env.example` to `.env` and adjust `BASE_URL` for your environment. Most defaults are suitable for development and small-scale production deployments.

For questions or issues, refer to the troubleshooting section or review the source code in `src/config.py`.
