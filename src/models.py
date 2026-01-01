"""
Core data models for the LoL Stonks RSS application.

This module defines the data structures used throughout the application,
including Article and ArticleSource models with factory pattern for
multi-source, multi-locale support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import lru_cache


class SourceCategory(str, Enum):
    """Categories of news sources for organization and filtering."""

    OFFICIAL_RIOT = "official_riot"  # Official Riot Games sources
    COMMUNITY_HUB = "community_hub"  # Community-driven content hubs
    ANALYTICS = "analytics"  # Analytics and statistics sources
    REGIONAL = "regional"  # Regional Riot sites
    ESPORTS = "esports"  # Esports news and coverage
    SOCIAL = "social"  # Social media aggregators
    AGGREGATOR = "aggregator"  # News aggregators
    PBE = "pbe"  # Public Beta Environment news
    TFT = "tft"  # Teamfight Tactics news


class ArticleSource:
    """
    Represents a news source with factory pattern for multi-locale support.

    Sources are identified by a string in the format "source-id:locale".
    This allows tracking the same source across different locales.
    Uses LRU caching to avoid recreating the same source instances.
    """

    # Official Riot Games sources
    RIOT_SOURCES: dict[str, dict] = {
        "lol": {"name": "League of Legends", "category": SourceCategory.OFFICIAL_RIOT},
        "riot-games": {"name": "Riot Games", "category": SourceCategory.OFFICIAL_RIOT},
        "playvalorant": {"name": "VALORANT", "category": SourceCategory.OFFICIAL_RIOT},
        "wildrift": {"name": "Wild Rift", "category": SourceCategory.OFFICIAL_RIOT},
    }

    # Community-driven content hubs
    COMMUNITY_SOURCES: dict[str, dict] = {
        "sur-monkey-ape": {
            "name": "Sur.monkey.ape",
            "category": SourceCategory.COMMUNITY_HUB,
            "base_url": "https://sur.monkey.ape",
        },
        "league-of-comics": {
            "name": "League of Comics",
            "category": SourceCategory.COMMUNITY_HUB,
            "base_url": "https://leagueofcomics.com",
        },
    }

    # Analytics and statistics sources
    ANALYTICS_SOURCES: dict[str, dict] = {
        "u-gg": {"name": "U.GG", "category": SourceCategory.ANALYTICS},
        "op-gg": {"name": "OP.GG", "category": SourceCategory.ANALYTICS},
        "mobalytics": {"name": "Mobalytics", "category": SourceCategory.ANALYTICS},
        "blitz-gg": {"name": "Blitz.GG", "category": SourceCategory.ANALYTICS},
        "porofessor": {"name": "Porofessor", "category": SourceCategory.ANALYTICS},
        "analytics": {
            "name": "Riot Games Developer Portal",
            "category": SourceCategory.ANALYTICS,
        },
    }

    # Regional Riot sites (with locale-specific base URLs)
    REGIONAL_SOURCES: dict[str, dict] = {
        "lol-eu": {"name": "LoL EU", "category": SourceCategory.REGIONAL},
        "lol-latam": {"name": "LoL LATAM", "category": SourceCategory.REGIONAL},
        "lol-jp": {"name": "LoL Japan", "category": SourceCategory.REGIONAL},
        "lol-kr": {"name": "LoL Korea", "category": SourceCategory.REGIONAL},
        "lol-sea": {"name": "LoL SEA", "category": SourceCategory.REGIONAL},
    }

    # Esports sources
    ESPORTS_SOURCES: dict[str, dict] = {
        "lolesports": {
            "name": "LoL Esports",
            "category": SourceCategory.ESPORTS,
            "base_url": "https://lolesports.com",
        },
        "dexerto": {
            "name": "Dexerto",
            "category": SourceCategory.ESPORTS,
            "base_url": "https://dexerto.com",
        },
        "dotesports": {
            "name": "Dot Esports",
            "category": SourceCategory.ESPORTS,
            "base_url": "https://dotesports.com",
        },
        "esportsgg": {
            "name": "Esports.gg",
            "category": SourceCategory.ESPORTS,
            "base_url": "https://esports.gg",
        },
        "ggrecon": {
            "name": "GGRecon",
            "category": SourceCategory.ESPORTS,
            "base_url": "https://www.ggrecon.com",
        },
        "nme": {
            "name": "NME",
            "category": SourceCategory.COMMUNITY_HUB,
            "base_url": "https://www.nme.com",
        },
        "pcgamesn": {
            "name": "PC Gamer",
            "category": SourceCategory.COMMUNITY_HUB,
            "base_url": "https://www.pcgamesn.com",
        },
        "thegamer": {
            "name": "TheGamer",
            "category": SourceCategory.COMMUNITY_HUB,
            "base_url": "https://www.thegamer.com",
        },
        "upcomer": {
            "name": "Upcomer",
            "category": SourceCategory.COMMUNITY_HUB,
            "base_url": "https://www.upcomer.com",
        },
    }

    # Social media aggregators
    SOCIAL_SOURCES: dict[str, dict] = {
        "twitter": {"name": "Twitter/X", "category": SourceCategory.SOCIAL},
        "reddit": {"name": "Reddit", "category": SourceCategory.SOCIAL},
    }

    # Combined source registry
    ALL_SOURCES: dict[str, dict] = {
        **RIOT_SOURCES,
        **COMMUNITY_SOURCES,
        **ANALYTICS_SOURCES,
        **REGIONAL_SOURCES,
        **ESPORTS_SOURCES,
        **SOCIAL_SOURCES,
    }

    def __init__(self, source_id: str, locale: str = "en-us") -> None:
        """
        Initialize an ArticleSource.

        Args:
            source_id: The source identifier (e.g., "lol", "u-gg")
            locale: Locale code (e.g., "en-us", "it-it")

        Raises:
            ValueError: If source_id is not recognized
        """
        if source_id not in self.ALL_SOURCES:
            raise ValueError(f"Unknown source: {source_id}")

        self._source_id = source_id
        self._locale = locale
        self._metadata = self.ALL_SOURCES[source_id]

    @classmethod
    @lru_cache(maxsize=512)
    def create(cls, source_id: str, locale: str = "en-us") -> "ArticleSource":
        """
        Factory method to create ArticleSource instances with caching.

        Args:
            source_id: The source identifier (e.g., "lol", "u-gg")
            locale: Locale code (e.g., "en-us", "it-it")

        Returns:
            ArticleSource instance

        Raises:
            ValueError: If source_id is not recognized
        """
        return cls(source_id, locale)

    @property
    def source_id(self) -> str:
        """Get the source identifier without locale."""
        return self._source_id

    @property
    def locale(self) -> str:
        """Get the locale code."""
        return self._locale

    @property
    def category(self) -> SourceCategory:
        """Get the source category."""
        return self._metadata["category"]  # type: ignore

    @property
    def name(self) -> str:
        """Get the human-readable source name."""
        return self._metadata["name"]  # type: ignore

    @property
    def base_url(self) -> str | None:
        """Get the base URL if available."""
        return self._metadata.get("base_url")

    def __str__(self) -> str:
        """String representation in 'source-id:locale' format."""
        return f"{self._source_id}:{self._locale}"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"ArticleSource({self._source_id!r}, {self._locale!r})"

    def __eq__(self, other: object) -> bool:
        """Equality check based on source_id and locale."""
        if not isinstance(other, ArticleSource):
            return NotImplemented
        return self._source_id == other._source_id and self._locale == other._locale

    def __hash__(self) -> int:
        """Hash for use in sets and as dict keys."""
        return hash((self._source_id, self._locale))

    @classmethod
    def from_string(cls, source_str: str) -> "ArticleSource":
        """
        Create ArticleSource from string representation.

        Args:
            source_str: String in format "source-id:locale" or legacy format like "lol-en-us"

        Returns:
            ArticleSource instance

        Raises:
            ValueError: If source_str is invalid

        Examples:
            >>> ArticleSource.from_string("lol:en-us")
            ArticleSource('lol', 'en-us')
            >>> ArticleSource.from_string("lol-en-us")  # Legacy format
            ArticleSource('lol', 'en-us')
        """
        # Try new format first
        if ":" in source_str:
            parts = source_str.split(":", 1)
            if len(parts) == 2:
                source_id, locale = parts
                return cls.create(source_id, locale)

        # Try legacy format (e.g., "lol-en-us", "riot-games:en-us")
        # Source IDs may contain hyphens, so we need to be careful
        for known_source in cls.ALL_SOURCES:
            if source_str.startswith(f"{known_source}-"):
                locale = source_str[len(known_source) + 1 :]
                return cls.create(known_source, locale)
            if source_str.startswith(f"{known_source}:"):
                locale = source_str[len(known_source) + 1 :]
                return cls.create(known_source, locale)

        raise ValueError(f"Invalid source string format: {source_str}")


@dataclass
class Article:
    """
    Represents a news article for RSS feed.

    This is the core data structure that holds all information about a news
    article, including metadata for RSS generation and database storage.
    Supports multi-source and multi-locale aggregation.

    Attributes:
        title: Article headline/title
        url: Full URL to the article
        pub_date: Publication date and time
        guid: Globally unique identifier for the article
        source: Source of the article (ArticleSource instance)
        description: Short description or summary
        content: Full article content (optional)
        image_url: URL to article's featured image
        author: Article author (defaults to "Riot Games")
        categories: List of article categories/tags
        created_at: Timestamp when article was added to database
        locale: Locale code for the article (e.g., "en-us", "it-it")
        source_category: Category of the source (for filtering/grouping)
        canonical_url: Primary URL for deduplication across sources
    """

    # Required fields
    title: str
    url: str
    pub_date: datetime
    guid: str
    source: ArticleSource

    # Optional fields
    description: str = ""
    content: str = ""
    image_url: str | None = None
    author: str = "Riot Games"
    categories: list[str] = field(default_factory=list)

    # Internal fields
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Multi-language/multi-source fields
    locale: str = "en-us"
    source_category: str | None = None
    canonical_url: str | None = None

    def __post_init__(self) -> None:
        """
        Validate article data after initialization.

        Raises:
            ValueError: If required fields are empty or invalid
        """
        if not self.title:
            raise ValueError("Article title cannot be empty")
        if not self.url:
            raise ValueError("Article URL cannot be empty")
        if not self.guid:
            raise ValueError("Article GUID cannot be empty")

        # Auto-populate source_category if not set
        if self.source_category is None and isinstance(self.source, ArticleSource):
            self.source_category = self.source.category.value

        # Auto-populate locale if not set
        if self.locale == "en-us" and isinstance(self.source, ArticleSource):
            self.locale = self.source.locale

        # Use canonical_url for deduplication if provided
        if self.canonical_url is None:
            self.canonical_url = self.url

    def to_dict(self) -> dict:
        """
        Convert article to dictionary for database storage.

        Returns:
            Dictionary representation of the article with serialized fields
        """
        return {
            "title": self.title,
            "url": self.url,
            "pub_date": self.pub_date.isoformat(),
            "guid": self.guid,
            "source": str(self.source),
            "description": self.description,
            "content": self.content,
            "image_url": self.image_url,
            "author": self.author,
            "categories": ",".join(self.categories),  # Store as CSV
            "created_at": self.created_at.isoformat(),
            "locale": self.locale,
            "source_category": self.source_category,
            "canonical_url": self.canonical_url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """
        Create Article instance from dictionary.

        This is the inverse of to_dict() and is used when loading
        articles from the database.

        Args:
            data: Dictionary containing article data

        Returns:
            Article instance constructed from the dictionary
        """
        # Parse source string to ArticleSource
        source_str = data.get("source", "lol:en-us")
        try:
            source = ArticleSource.from_string(source_str)
        except ValueError:
            # Fallback for legacy data
            source = ArticleSource.create("lol", data.get("locale", "en-us"))

        return cls(
            title=data["title"],
            url=data["url"],
            pub_date=datetime.fromisoformat(data["pub_date"]),
            guid=data["guid"],
            source=source,
            description=data.get("description", ""),
            content=data.get("content", ""),
            image_url=data.get("image_url"),
            author=data.get("author", "Riot Games"),
            categories=data.get("categories", "").split(",") if data.get("categories") else [],
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else datetime.utcnow(),
            locale=data.get("locale", "en-us"),
            source_category=data.get("source_category"),
            canonical_url=data.get("canonical_url"),
        )
