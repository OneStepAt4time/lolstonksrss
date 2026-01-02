# Monitoring Guide

This guide covers monitoring and alerting for the LoL Stonks RSS application using Prometheus and Grafana.

## Overview

The application exposes Prometheus metrics at the `/metrics` endpoint for monitoring and alerting. Key metrics include:

- Article fetch counts
- Scraping duration and latency
- Cache hit rates and sizes
- Circuit breaker states
- Feed generation performance

## Quick Start

### 1. Start Monitoring Stack

```bash
# Start Prometheus and Grafana
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Access Dashboards

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### 3. View Metrics

The built-in dashboard "LoL Stonks RSS - Overview" provides visualization of key metrics.

## Available Metrics

### Counter Metrics

#### `articles_fetched_total{source, locale}`

Total number of articles fetched from each source/locale combination.

**Example:**
```promql
# Rate of articles fetched
rate(articles_fetched_total[5m])

# Total articles per source
sum(articles_fetched_total) by (source)
```

#### `scraping_requests_total{source, locale, status}`

Total number of scraping requests with status labels (success, error, circuit_breaker_open, unknown_source).

**Example:**
```promql
# Error rate
rate(scraping_requests_total{status="error"}[5m])

# Success rate
rate(scraping_requests_total{status="success"}[5m])
```

#### `feed_generation_requests_total{locale, status}`

Total number of feed generation requests.

#### `cache_operations_total{operation, status}`

Total number of cache operations (get, set, delete) with hit/miss tracking.

### Histogram Metrics

#### `scraping_duration_seconds{source, locale}`

Distribution of scraping durations. Use for latency analysis (p50, p95, p99).

**Example:**
```promql
# p95 latency
histogram_quantile(0.95, rate(scraping_duration_seconds_bucket[5m]))

# Average scraping time
rate(scraping_duration_seconds_sum[5m]) / rate(scraping_duration_seconds_count[5m])
```

#### `feed_generation_duration_seconds{locale, type}`

Distribution of feed generation durations by locale and feed type (main, source, category).

#### `database_operation_duration_seconds{operation}`

Distribution of database operation durations.

### Gauge Metrics

#### `cache_hit_rate{cache_name}`

Current cache hit rate (0.0 to 1.0).

#### `cache_size_bytes{cache_name}`

Estimated cache size in bytes.

#### `cache_entries{cache_name}`

Number of entries in cache.

#### `scraper_last_success_timestamp{source, locale}`

Unix timestamp of last successful scrape for each source/locale.

**Example:**
```promql
# Time since last successful scrape (seconds)
time() - scraper_last_success_timestamp

# Sources that haven't scraped in 10 minutes
scraper_last_success_timestamp < time() - 600
```

#### `circuit_breaker_state{source}`

Circuit breaker state (0=closed, 1=half_open, 2=open).

#### `circuit_breaker_failure_count{source}`

Current circuit breaker failure count.

#### `active_update_tasks`

Current number of active update tasks.

### Info Metrics

#### `build_info{version, commit, build_date}`

Build information for the application.

## Alerting Examples

### High Error Rate

Alert when scraping error rate exceeds 10%:

```yaml
- alert: HighScrapingErrorRate
  expr: |
    rate(scraping_requests_total{status="error"}[5m])
    /
    rate(scraping_requests_total[5m])
    > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High scraping error rate for {{ $labels.source }}/{{ $labels.locale }}"
```

### Circuit Breaker Open

Alert when circuit breaker opens:

```yaml
- alert: CircuitBreakerOpen
  expr: circuit_breaker_state == 2
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Circuit breaker OPEN for {{ $labels.source }}"
```

### Low Cache Hit Rate

Alert when cache hit rate drops below 50%:

```yaml
- alert: LowCacheHitRate
  expr: cache_hit_rate < 0.5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Low cache hit rate for {{ $labels.cache_name }}"
```

### Stale Scraper

Alert when scraper hasn't successfully fetched in 30 minutes:

```yaml
- alert: StaleScraper
  expr: |
    time() - scraper_last_success_timestamp > 1800
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Scraper {{ $labels.source }}/{{ $labels.locale }} hasn't fetched in 30 minutes"
```

### High Scraping Latency

Alert when p95 scraping latency exceeds 5 seconds:

```yaml
- alert: HighScrapingLatency
  expr: |
    histogram_quantile(0.95, rate(scraping_duration_seconds_bucket[5m])) > 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High scraping latency for {{ $labels.source }}/{{ $labels.locale }}"
```

## Grafana Dashboard

The included dashboard provides panels for:

1. **Articles Fetched Rate**: Rate of articles fetched per source/locale
2. **Cache Hit Rate**: Current cache hit rate gauge
3. **Scraping Duration**: p95 and p99 latency percentiles
4. **Successful Scraping Requests**: Stacked bar chart of successful requests
5. **Circuit Breaker States**: Current state of all circuit breakers
6. **Circuit Breaker Failure Counts**: Time series of failure counts

## Configuration

### Prometheus Configuration

Located at `config/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "lolstonksrss"
    scrape_interval: 30s
    metrics_path: "/metrics"
    static_configs:
      - targets: ["host.docker.internal:8000"]
```

### Grafana Provisioning

Datasources and dashboards are automatically provisioned from:

- `config/grafana/provisioning/datasources/`
- `config/grafana/provisioning/dashboards/`
- `config/grafana/dashboards/`

## Troubleshooting

### Metrics Not Appearing

1. Check if the application is running:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Verify Prometheus target status:
   - Go to http://localhost:9090/targets
   - Check if the lolstonksrss target is "UP"

3. Check Prometheus logs:
   ```bash
   docker logs lolstonksrss-prometheus
   ```

### Dashboard Not Loading

1. Verify datasource connection in Grafana:
   - Configuration > Data Sources > Prometheus
   - Click "Test" button

2. Check dashboard provisioning logs:
   ```bash
   docker logs lolstonksrss-grafana
   ```

## Advanced Queries

### Find slowest scrapers

```promql
topk(10, histogram_quantile(0.99, rate(scraping_duration_seconds_bucket[5m])))
```

### Compare article rates across sources

```promql
rate(articles_fetched_total[5m]) * 3600
```

### Identify sources with failing scrapers

```promql
rate(scraping_requests_total{status="error"}[5m]) > 0
```

### Cache effectiveness

```promql
sum(rate(cache_operations_total{status="hit"}[5m])) /
sum(rate(cache_operations_total{operation="get"}[5m]))
```

## Production Considerations

### Metrics Retention

Default Prometheus retention is 30 days. Adjust in `docker-compose.monitoring.yml`:

```yaml
command:
  - "--storage.tsdb.retention.time=90d"  # 90 days
```

### Alertmanager Integration

To enable alerting, uncomment and configure the alertmanager section in `prometheus.yml`.

### Authentication

For production, enable authentication on the `/metrics` endpoint:

1. Configure basic auth in FastAPI
2. Update Prometheus scrape config with credentials

## See Also

- [Prometheus Querying Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Reference](https://grafana.com/docs/grafana/latest/dashboards/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
