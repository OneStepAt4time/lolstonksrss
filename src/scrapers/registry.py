"""
Scraper registry and factory for managing all news source configurations.

This module provides a central registry of all scrapable news sources with
their configurations, and a factory function to create appropriate scraper
instances based on source ID and locale.

Sources are organized by category (community hub, analytics, regional, etc.)
and difficulty level (EASY for RSS, MEDIUM for HTML, HARD for Selenium).
"""

import logging
from typing import Final

from src.models import SourceCategory
from src.scrapers.base import BaseScraper, ScrapingConfig, ScrapingDifficulty
from src.scrapers.html import HTMLScraper
from src.scrapers.rss import RSSScraper
from src.scrapers.selenium import SeleniumScraper

logger = logging.getLogger(__name__)

# =============================================================================
# Source Configurations
# =============================================================================

# Community Hubs - Major gaming news websites
_COMMUNITY_HUB_CONFIGS: Final[dict[str, ScrapingConfig]] = {
    "dexerto": ScrapingConfig(
        source_id="dexerto",
        base_url="https://www.dexerto.com/league-of-legends",
        difficulty=ScrapingDifficulty.EASY,
        rate_limit_seconds=2.0,
        timeout_seconds=30,
        rss_feed_url="https://www.dexerto.com/league-of-legends/feed",
    ),
    # NOTE: League-specific feed blocked by Cloudflare (403). Using main feed which contains LoL content.
    "dotesports": ScrapingConfig(
        source_id="dotesports",
        base_url="https://dotesports.com/league-of-legends",
        difficulty=ScrapingDifficulty.EASY,
        rate_limit_seconds=2.0,
        timeout_seconds=30,
        rss_feed_url="https://dotesports.com/feed",
    ),
    "esportsgg": ScrapingConfig(
        source_id="esportsgg",
        base_url="https://esports.gg/news/league-of-legends",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=2.5,
        timeout_seconds=30,
    ),
    "ggrecon": ScrapingConfig(
        source_id="ggrecon",
        base_url="https://www.ggrecon.com/games/league-of-legends",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=2.0,
        timeout_seconds=30,
    ),
    # REMOVED: nme - League-specific feed returns 404 (verified 2025-01-02).
    # Main gaming feed also returns 404. Site no longer provides working RSS feeds.
    # See Bug #6 investigation in tmp/test-feeds.py for details.
    "pcgamesn": ScrapingConfig(
        source_id="pcgamesn",
        base_url="https://www.pcgamesn.com/league-of-legends",
        difficulty=ScrapingDifficulty.EASY,
        rate_limit_seconds=2.0,
        timeout_seconds=30,
        rss_feed_url="https://www.pcgamesn.com/league-of-legends/feed",
    ),
    # REMOVED: thegamer - League-specific feed returns 404 (verified 2025-01-02).
    # Main site feed exists but contains 0% League of Legends content.
    # See Bug #6 investigation in tmp/inspect-feeds.py for details.
    # REMOVED: upcomer - League-specific feed returns 404 (verified 2025-01-02).
    # Main site feed exists but contains 0% League of Legends content.
    # See Bug #6 investigation in tmp/inspect-feeds.py for details.
}

# Analytics Sources - Statistics and data sites
_ANALYTICS_CONFIGS: Final[dict[str, ScrapingConfig]] = {
    "mobalytics": ScrapingConfig(
        source_id="mobalytics",
        base_url="https://app.mobalytics.gg/league-of-legends/news",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=2.5,
        timeout_seconds=30,
    ),
    "u-gg": ScrapingConfig(
        source_id="u-gg",
        base_url="https://u.gg/news",
        difficulty=ScrapingDifficulty.HARD,
        rate_limit_seconds=3.0,
        timeout_seconds=30,
        requires_selenium=True,
    ),
    "blitz-gg": ScrapingConfig(
        source_id="blitz-gg",
        base_url="https://blitz.gg/lol/news",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=2.5,
        timeout_seconds=30,
    ),
    "porofessor": ScrapingConfig(
        source_id="porofessor",
        base_url="https://www.porofessor.gg/news",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=2.5,
        timeout_seconds=30,
    ),
}

# Regional Sources - Non-English community sites
_REGIONAL_CONFIGS: Final[dict[str, ScrapingConfig]] = {
    "inven": ScrapingConfig(
        source_id="inven",
        base_url="https://www.inven.co.kr/webzine/news/?site=lol",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=3.0,
        timeout_seconds=30,
    ),
    "opgg": ScrapingConfig(
        source_id="opgg",
        base_url="https://www.op.gg/news",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=2.5,
        timeout_seconds=30,
    ),
    "3djuegos": ScrapingConfig(
        source_id="3djuegos",
        base_url="https://www.3djuegos.com/league-of-legends",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=2.0,
        timeout_seconds=30,
    ),
    "earlygame": ScrapingConfig(
        source_id="earlygame",
        base_url="https://www.earlygame.com/league-of-legends",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=2.0,
        timeout_seconds=30,
    ),
}

# TFT Sources - Teamfight Tactics news
_TFT_CONFIGS: Final[dict[str, ScrapingConfig]] = {
    "bunnymuffins": ScrapingConfig(
        source_id="bunnymuffins",
        base_url="https://bunnymuffins.lol/news",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=2.5,
        timeout_seconds=30,
    ),
    "tftactics": ScrapingConfig(
        source_id="tftactics",
        base_url="https://tftactics.gg/news",
        difficulty=ScrapingDifficulty.MEDIUM,
        rate_limit_seconds=2.5,
        timeout_seconds=30,
    ),
}

# Social Media Sources
_SOCIAL_CONFIGS: Final[dict[str, ScrapingConfig]] = {
    "twitter": ScrapingConfig(
        source_id="twitter",
        base_url="https://twitter.com/LeagueOfLegends",
        difficulty=ScrapingDifficulty.HARD,
        rate_limit_seconds=5.0,
        timeout_seconds=30,
        requires_selenium=True,
    ),
    "reddit": ScrapingConfig(
        source_id="reddit",
        base_url="https://www.reddit.com/r/leagueoflegends",
        difficulty=ScrapingDifficulty.HARD,
        rate_limit_seconds=5.0,
        timeout_seconds=30,
        requires_selenium=True,
    ),
    "youtube": ScrapingConfig(
        source_id="youtube",
        base_url="https://www.youtube.com/@LeagueOfLegends/videos",
        difficulty=ScrapingDifficulty.HARD,
        rate_limit_seconds=5.0,
        timeout_seconds=30,
        requires_selenium=True,
    ),
}

# Esports Sources
_ESPORTS_CONFIGS: Final[dict[str, ScrapingConfig]] = {
    "lolesports": ScrapingConfig(
        source_id="lolesports",
        base_url="https://lolesports.com/news",
        difficulty=ScrapingDifficulty.HARD,
        rate_limit_seconds=3.0,
        timeout_seconds=30,
        requires_selenium=True,
    ),
    "dexerto-esports": ScrapingConfig(
        source_id="dexerto-esports",
        base_url="https://www.dexerto.com/esports/league-of-legends",
        difficulty=ScrapingDifficulty.EASY,
        rate_limit_seconds=2.0,
        timeout_seconds=30,
        rss_feed_url="https://www.dexerto.com/esports/league-of-legends/feed",
    ),
}

# =============================================================================
# Combined Registry
# =============================================================================

SCRAPER_CONFIGS: Final[dict[str, ScrapingConfig]] = {
    **_COMMUNITY_HUB_CONFIGS,
    **_ANALYTICS_CONFIGS,
    **_REGIONAL_CONFIGS,
    **_TFT_CONFIGS,
    **_SOCIAL_CONFIGS,
    **_ESPORTS_CONFIGS,
}

# =============================================================================
# Scraper Class Mapping
# =============================================================================

SCRAPER_CLASSES: Final[dict[ScrapingDifficulty, type[BaseScraper]]] = {
    ScrapingDifficulty.EASY: RSSScraper,
    ScrapingDifficulty.MEDIUM: HTMLScraper,
    ScrapingDifficulty.HARD: SeleniumScraper,
}

# =============================================================================
# Source Categories Mapping
# =============================================================================

SOURCE_CATEGORY_MAP: Final[dict[str, SourceCategory]] = {
    # Community hubs
    "dexerto": SourceCategory.COMMUNITY_HUB,
    "dotesports": SourceCategory.COMMUNITY_HUB,
    "esportsgg": SourceCategory.COMMUNITY_HUB,
    "ggrecon": SourceCategory.COMMUNITY_HUB,
    # REMOVED: nme, thegamer, upcomer - broken RSS feeds (404) with no viable alternatives
    # See Bug #6 investigation in tmp/ directory for verification details
    "pcgamesn": SourceCategory.COMMUNITY_HUB,
    # Analytics
    "mobalytics": SourceCategory.ANALYTICS,
    "u-gg": SourceCategory.ANALYTICS,
    "blitz-gg": SourceCategory.ANALYTICS,
    "porofessor": SourceCategory.ANALYTICS,
    # Regional
    "inven": SourceCategory.REGIONAL,
    "opgg": SourceCategory.REGIONAL,
    "3djuegos": SourceCategory.REGIONAL,
    "earlygame": SourceCategory.REGIONAL,
    # TFT
    "bunnymuffins": SourceCategory.TFT,
    "tftactics": SourceCategory.TFT,
    # Social
    "twitter": SourceCategory.SOCIAL,
    "reddit": SourceCategory.SOCIAL,
    "youtube": SourceCategory.SOCIAL,
    # Esports
    "lolesports": SourceCategory.ESPORTS,
    "dexerto-esports": SourceCategory.ESPORTS,
}

# =============================================================================
# Lists for Easy Access
# =============================================================================

ALL_SCRAPER_SOURCES: Final[list[str]] = list(SCRAPER_CONFIGS.keys())

COMMUNITY_HUB_SOURCES: Final[list[str]] = list(_COMMUNITY_HUB_CONFIGS.keys())

ANALYTICS_SOURCES: Final[list[str]] = list(_ANALYTICS_CONFIGS.keys())

REGIONAL_SOURCES: Final[list[str]] = list(_REGIONAL_CONFIGS.keys())

TFT_SOURCES: Final[list[str]] = list(_TFT_CONFIGS.keys())

SOCIAL_SOURCES: Final[list[str]] = list(_SOCIAL_CONFIGS.keys())

ESPORTS_SOURCES: Final[list[str]] = list(_ESPORTS_CONFIGS.keys())


# =============================================================================
# Factory Function
# =============================================================================


def get_scraper(source_id: str, locale: str = "en-us") -> BaseScraper:
    """
    Factory function to create a scraper instance for a given source.

    This function looks up the source configuration, determines the
    appropriate scraper class based on difficulty, and returns an
    instantiated scraper ready for use.

    Args:
        source_id: Unique identifier for the source (e.g., "dexerto", "inven")
        locale: Locale code for articles (e.g., "en-us", "ko-kr")

    Returns:
        Instantiated scraper object (RSSScraper, HTMLScraper, or SeleniumScraper)

    Raises:
        ValueError: If source_id is not found in SCRAPER_CONFIGS

    Examples:
        >>> scraper = get_scraper("dexerto", "en-us")
        >>> articles = await scraper.fetch_articles()

        >>> scraper = get_scraper("inven", "ko-kr")
        >>> articles = await scraper.fetch_articles()

        >>> scraper = get_scraper("twitter", "en-us")
        >>> articles = await scraper.fetch_articles()
    """
    if source_id not in SCRAPER_CONFIGS:
        available = ", ".join(ALL_SCRAPER_SOURCES)
        raise ValueError(f"Unknown scraper source: {source_id}. " f"Available sources: {available}")

    config = SCRAPER_CONFIGS[source_id]
    scraper_class = SCRAPER_CLASSES[config.difficulty]

    logger.info(f"Creating {scraper_class.__name__} for {source_id} (locale: {locale})")

    return scraper_class(config, locale)


def get_sources_by_category(category: SourceCategory) -> list[str]:
    """
    Get all source IDs belonging to a specific category.

    Args:
        category: Source category to filter by

    Returns:
        List of source IDs in the specified category

    Examples:
        >>> get_sources_by_category(SourceCategory.COMMUNITY_HUB)
        ['dexerto', 'dotesports', 'esportsgg', ...]

        >>> get_sources_by_category(SourceCategory.ANALYTICS)
        ['mobalytics', 'u-gg', 'blitz-gg', 'porofessor']
    """
    return [source_id for source_id, cat in SOURCE_CATEGORY_MAP.items() if cat == category]


def get_sources_by_difficulty(difficulty: ScrapingDifficulty) -> list[str]:
    """
    Get all source IDs requiring a specific difficulty level.

    Args:
        difficulty: Scraping difficulty level

    Returns:
        List of source IDs with the specified difficulty

    Examples:
        >>> get_sources_by_difficulty(ScrapingDifficulty.EASY)
        ['dexerto', 'dotesports', 'nme', ...]

        >>> get_sources_by_difficulty(ScrapingDifficulty.HARD)
        ['twitter', 'reddit', 'youtube']
    """
    return [
        source_id
        for source_id, config in SCRAPER_CONFIGS.items()
        if config.difficulty == difficulty
    ]


def is_selenium_required(source_id: str) -> bool:
    """
    Check if a source requires Selenium for scraping.

    Args:
        source_id: Source identifier to check

    Returns:
        True if source requires Selenium, False otherwise

    Raises:
        ValueError: If source_id is not found in registry
    """
    if source_id not in SCRAPER_CONFIGS:
        raise ValueError(f"Unknown source: {source_id}")

    return SCRAPER_CONFIGS[source_id].requires_selenium
