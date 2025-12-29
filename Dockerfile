# Multi-stage build for smaller image size

# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Copy UV configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies using UV
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC \
    PATH=/app/.venv/bin:$PATH

# Create non-root user for security
RUN useradd -m -u 1000 lolrss && \
    mkdir -p /app/data && \
    chown -R lolrss:lolrss /app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=lolrss:lolrss /app/.venv /app/.venv

# Copy application code
COPY --chown=lolrss:lolrss src/ ./src/
COPY --chown=lolrss:lolrss main.py ./

# Switch to non-root user
USER lolrss

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run application
CMD ["python", "main.py"]
