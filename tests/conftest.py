"""
Pytest configuration and shared fixtures for the test suite.
"""
import asyncio
import os
import sys
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def base_url():
    """Base URL for E2E tests (configurable via environment)."""
    return os.getenv("TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture
def api_timeout():
    """Timeout for API requests in seconds."""
    return int(os.getenv("TEST_API_TIMEOUT", "30"))


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create test client for FastAPI app.

    Yields:
        AsyncClient instance for testing
    """
    from src.api.app import app

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "smoke: marks smoke tests (critical functionality)")
    config.addinivalue_line("markers", "slow: marks slow-running tests")
    config.addinivalue_line("markers", "unit: marks unit tests")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "api: marks API endpoint tests")
    config.addinivalue_line("markers", "rss: marks RSS validation tests")
