"""
Core data models for the LoL Stonks RSS application.

This module defines the data structures used throughout the application,
including Article and ArticleSource models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ArticleSource(str, Enum):
    """Supported news sources for RSS feed aggregation."""

    LOL_EN_US = "lol-en-us"
    LOL_IT_IT = "lol-it-it"
    # Future sources can be added here
    # RIOT_BLOG = "riot-blog"


@dataclass
class Article:
    """
    Represents a news article for RSS feed.

    This is the core data structure that holds all information about a news
    article, including metadata for RSS generation and database storage.

    Attributes:
        title: Article headline/title
        url: Full URL to the article
        pub_date: Publication date and time
        guid: Globally unique identifier for the article
        source: Source of the article (e.g., lol-en-us)
        description: Short description or summary
        content: Full article content (optional)
        image_url: URL to article's featured image
        author: Article author (defaults to "Riot Games")
        categories: List of article categories/tags
        created_at: Timestamp when article was added to database
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
            "source": self.source.value,
            "description": self.description,
            "content": self.content,
            "image_url": self.image_url,
            "author": self.author,
            "categories": ",".join(self.categories),  # Store as CSV
            "created_at": self.created_at.isoformat(),
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
        return cls(
            title=data["title"],
            url=data["url"],
            pub_date=datetime.fromisoformat(data["pub_date"]),
            guid=data["guid"],
            source=ArticleSource(data["source"]),
            description=data.get("description", ""),
            content=data.get("content", ""),
            image_url=data.get("image_url"),
            author=data.get("author", "Riot Games"),
            categories=data.get("categories", "").split(",") if data.get("categories") else [],
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else datetime.utcnow(),
        )
