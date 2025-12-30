"""
Integration tests for LoL News API client.

These tests make real API calls to verify the implementation works with live data.
They are marked as 'slow' and can be run with: pytest -m slow
"""

import pytest

from src.api_client import LoLNewsAPIClient
from src.models import Article, ArticleSource


@pytest.mark.slow
@pytest.mark.asyncio
async def test_fetch_real_en_us_news() -> None:
    """
    Integration test: Fetch real English news from LoL API.

    This test makes real HTTP requests and validates:
    - BuildID extraction works
    - API response parsing works
    - Article transformation works
    - Returns expected number of articles
    """
    client = LoLNewsAPIClient()

    articles = await client.fetch_news("en-us")

    # Validate results
    assert len(articles) > 0, "Should fetch at least one article"
    assert len(articles) <= 100, "Should not fetch more than 100 articles"

    # Validate all articles
    for article in articles:
        assert isinstance(article, Article)
        assert article.title, "Article should have a title"
        assert article.url, "Article should have a URL"
        assert article.pub_date, "Article should have a publication date"
        assert article.guid, "Article should have a GUID"
        assert article.source == ArticleSource.LOL_EN_US
        assert article.author == "Riot Games"

    print(f"Successfully fetched {len(articles)} English articles")


@pytest.mark.slow
@pytest.mark.asyncio
async def test_fetch_real_it_it_news() -> None:
    """
    Integration test: Fetch real Italian news from LoL API.

    This test validates Italian locale support.
    """
    client = LoLNewsAPIClient()

    articles = await client.fetch_news("it-it")

    # Validate results
    assert len(articles) > 0, "Should fetch at least one article"

    # Validate all articles have Italian source
    for article in articles:
        assert article.source == ArticleSource.LOL_IT_IT

    print(f"Successfully fetched {len(articles)} Italian articles")


@pytest.mark.slow
@pytest.mark.asyncio
async def test_buildid_caching() -> None:
    """
    Integration test: Verify buildID is cached across multiple calls.

    This test validates the caching mechanism works correctly.
    """
    client = LoLNewsAPIClient()

    # First call - should fetch buildID from HTML
    build_id_1 = await client.get_build_id("en-us")
    assert build_id_1, "BuildID should be extracted"

    # Second call - should use cached buildID
    build_id_2 = await client.get_build_id("en-us")
    assert build_id_2 == build_id_1, "BuildID should be cached"

    print(f"BuildID: {build_id_1}")


@pytest.mark.slow
@pytest.mark.asyncio
async def test_multiple_locales() -> None:
    """
    Integration test: Fetch news from multiple locales.

    This test validates that different locales work correctly and
    are cached independently.
    """
    client = LoLNewsAPIClient()

    # Fetch English articles
    en_articles = await client.fetch_news("en-us")
    assert len(en_articles) > 0

    # Fetch Italian articles
    it_articles = await client.fetch_news("it-it")
    assert len(it_articles) > 0

    # Verify sources are correct
    assert all(a.source == ArticleSource.LOL_EN_US for a in en_articles)
    assert all(a.source == ArticleSource.LOL_IT_IT for a in it_articles)

    print(f"Fetched {len(en_articles)} EN articles and {len(it_articles)} IT articles")


if __name__ == "__main__":
    # Run integration tests when executed directly
    import asyncio

    async def run_tests():
        print("Running integration tests...")
        print("\n1. Testing English news fetch...")
        await test_fetch_real_en_us_news()

        print("\n2. Testing Italian news fetch...")
        await test_fetch_real_it_it_news()

        print("\n3. Testing buildID caching...")
        await test_buildid_caching()

        print("\n4. Testing multiple locales...")
        await test_multiple_locales()

        print("\nAll integration tests passed!")

    asyncio.run(run_tests())
