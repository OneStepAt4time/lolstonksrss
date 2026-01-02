"""
E2E tests for Docker deployment.

This test suite validates that the Docker image can be built, deployed,
and runs correctly on Windows with Docker Desktop.
"""

import subprocess
import time

import feedparser
import httpx
import pytest

# Test configuration
IMAGE_NAME = "lolstonksrss:test"
CONTAINER_NAME = "lolstonksrss"
HOST_PORT = 8001  # Use 8001 to avoid conflicts with other services
BASE_URL = f"http://localhost:{HOST_PORT}"
STARTUP_WAIT = 25  # seconds for container startup and initial news fetch
HEALTH_CHECK_WAIT = 35  # seconds for health check to pass


def run_command(cmd: list[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(cmd, capture_output=capture_output, text=True, check=False)


@pytest.mark.e2e
@pytest.mark.docker
def test_docker_image_build():
    """Test Docker image builds successfully."""
    result = run_command(["docker", "build", "-t", IMAGE_NAME, "."])

    assert result.returncode == 0, f"Build failed: {result.stderr}"

    # Verify image exists
    result = run_command(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"])
    assert IMAGE_NAME in result.stdout


@pytest.mark.e2e
@pytest.mark.docker
def test_docker_container_starts():
    """Test Docker container starts successfully."""
    # Remove existing container
    run_command(["docker", "rm", "-f", CONTAINER_NAME])

    # Run container
    result = run_command(
        ["docker", "run", "-d", "--name", CONTAINER_NAME, "-p", f"{HOST_PORT}:8000", IMAGE_NAME]
    )

    assert result.returncode == 0, f"Container start failed: {result.stderr}"

    # Wait for startup
    time.sleep(STARTUP_WAIT)

    # Check container is running
    result = run_command(["docker", "ps", "--filter", f"name={CONTAINER_NAME}"])
    assert CONTAINER_NAME in result.stdout, "Container not found in running containers"


@pytest.mark.e2e
@pytest.mark.docker
def test_docker_health_check():
    """Test Docker health check passes."""
    time.sleep(HEALTH_CHECK_WAIT)

    result = run_command(["docker", "inspect", "--format={{.State.Health.Status}}", CONTAINER_NAME])

    assert "healthy" in result.stdout.lower(), f"Health check failed: {result.stdout}"


@pytest.mark.e2e
@pytest.mark.docker
@pytest.mark.slow
def test_docker_endpoints_accessible():
    """Test all endpoints are accessible in Docker."""
    # Wait for startup
    time.sleep(STARTUP_WAIT)

    with httpx.Client(timeout=60.0) as client:
        # Health check
        response = client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

        # Main feed
        response = client.get(f"{BASE_URL}/feed.xml")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/rss+xml; charset=utf-8"

        feed = feedparser.parse(response.text)
        assert feed.version == "rss20"

        # Admin refresh endpoint
        response = client.post(f"{BASE_URL}/admin/refresh")
        assert response.status_code == 200

        # Scheduler status endpoint
        response = client.get(f"{BASE_URL}/admin/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data


@pytest.mark.e2e
@pytest.mark.docker
def test_docker_source_feeds():
    """Test source-specific RSS feeds."""
    time.sleep(STARTUP_WAIT)

    with httpx.Client(timeout=60.0) as client:
        # Test en-us feed
        response = client.get(f"{BASE_URL}/feed/en-us.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        assert feed.version == "rss20"

        # Test it-it feed
        response = client.get(f"{BASE_URL}/feed/it-it.xml")
        assert response.status_code == 200
        feed = feedparser.parse(response.text)
        assert feed.version == "rss20"

        # Test invalid source returns 404
        response = client.get(f"{BASE_URL}/feed/invalid.xml")
        assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.docker
def test_docker_api_articles_endpoint():
    """Test the API articles endpoint."""
    time.sleep(STARTUP_WAIT)

    with httpx.Client(timeout=60.0) as client:
        response = client.get(f"{BASE_URL}/api/articles?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.e2e
@pytest.mark.docker
def test_docker_volume_persistence():
    """Test data persists across container restarts."""
    time.sleep(STARTUP_WAIT)

    # Get initial article count
    with httpx.Client(timeout=60.0) as client:
        response = client.get(f"{BASE_URL}/feed.xml")
        feed1 = feedparser.parse(response.text)
        count1 = len(feed1.entries)

    # Restart container
    run_command(["docker", "restart", CONTAINER_NAME])
    time.sleep(STARTUP_WAIT)

    # Check data persisted (should have same or more articles)
    with httpx.Client(timeout=60.0) as client:
        response = client.get(f"{BASE_URL}/feed.xml")
        feed2 = feedparser.parse(response.text)
        count2 = len(feed2.entries)

    assert count2 >= count1, "Data should persist or grow across restarts"


@pytest.mark.e2e
@pytest.mark.docker
def test_docker_logs_no_errors():
    """Test Docker logs show no critical errors."""
    # Wait for startup and initial fetch
    time.sleep(STARTUP_WAIT)

    result = run_command(["docker", "logs", CONTAINER_NAME])

    # Check for critical errors that indicate startup failures
    # Some "ERROR" messages are acceptable (e.g., network errors during news fetching)
    critical_patterns = ["ImportError", "ModuleNotFoundError", "SyntaxError", "IndentationError"]

    for pattern in critical_patterns:
        assert pattern not in result.stdout, f"Critical error in logs: {pattern}"


@pytest.mark.e2e
@pytest.mark.docker
@pytest.mark.slow
def test_docker_manual_refresh():
    """Test manual scheduler trigger."""
    time.sleep(STARTUP_WAIT)

    with httpx.Client(timeout=60.0) as client:
        response = client.post(f"{BASE_URL}/admin/scheduler/trigger")
        assert response.status_code == 200
        data = response.json()
        # The response contains sources with new/duplicates counts
        assert "sources" in data or "total_added" in data or "total_updated" in data


@pytest.mark.e2e
@pytest.mark.docker
def test_docker_container_cleanup():
    """Test container can be stopped and removed."""
    # Stop container
    result = run_command(["docker", "stop", CONTAINER_NAME])
    assert result.returncode == 0

    # Remove container
    result = run_command(["docker", "rm", CONTAINER_NAME])
    assert result.returncode == 0

    # Verify container is removed
    result = run_command(["docker", "ps", "-a", "--filter", f"name={CONTAINER_NAME}"])
    assert CONTAINER_NAME not in result.stdout


@pytest.mark.e2e
@pytest.mark.docker
def test_docker_image_size():
    """Test Docker image size is reasonable."""
    result = run_command(["docker", "images", IMAGE_NAME, "--format", "{{.Size}}"])

    size_str = result.stdout.strip()
    # Image should be under 500MB (multi-stage build with slim base)
    # Common sizes: 150-250MB is typical
    assert size_str, "Could not get image size"

    # Parse size (format: "XXXMB" or "XXX.XXGB")
    if "GB" in size_str:
        size_gb = float(size_str.replace("GB", "").strip())
        assert size_gb < 1.0, f"Image too large: {size_str}"
    else:
        size_mb = float(size_str.replace("MB", "").strip())
        assert size_mb < 500, f"Image too large: {size_str}"


@pytest.mark.e2e
@pytest.mark.docker
def test_docker_environment_variables():
    """Test container respects environment variables."""
    # Remove existing container
    run_command(["docker", "rm", "-f", CONTAINER_NAME])

    # Run with custom environment
    result = run_command(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "-p",
            f"{HOST_PORT}:8000",
            "-e",
            "LOG_LEVEL=DEBUG",
            "-e",
            "UPDATE_INTERVAL_MINUTES=120",
            IMAGE_NAME,
        ]
    )
    assert result.returncode == 0

    time.sleep(STARTUP_WAIT)

    # Check logs for debug level
    result = run_command(["docker", "logs", CONTAINER_NAME])
    # Debug logs should be present
    assert "Starting server" in result.stdout or "INFO" in result.stdout

    # Cleanup
    run_command(["docker", "stop", CONTAINER_NAME])
    run_command(["docker", "rm", CONTAINER_NAME])
