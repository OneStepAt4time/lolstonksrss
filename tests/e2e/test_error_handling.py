# E2E Error Handling Tests

from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app, app_state
from src.database import ArticleRepository


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_articles.db")


@pytest.fixture
async def test_repository(temp_db_path):
    repo = ArticleRepository(temp_db_path)
    await repo.initialize()
    yield repo
    await repo.close()


@pytest.fixture
def mock_feed_service():
    service = AsyncMock()
    service.get_main_feed = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')
    service.get_supported_locales = Mock(return_value=["en-us", "it-it"])
    service.get_feed_by_locale = AsyncMock(return_value='<?xml version="1.0"?><rss></rss>')
    app_state["feed_service"] = service
    app_state["feed_service_v2"] = service
    return service
