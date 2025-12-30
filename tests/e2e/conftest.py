"""E2E test configuration."""
import os

import pytest


@pytest.fixture(scope="session")
def base_url():
    """Get the base URL for testing."""
    return os.environ.get("TEST_BASE_URL", "http://localhost:8001")


@pytest.fixture(scope="session")
def BASE_URL(base_url):
    """Get the base URL for testing (alias)."""
    return base_url
