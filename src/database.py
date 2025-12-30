"""
Database repository for article storage using SQLite.

This module provides an async SQLite repository for storing and retrieving
news articles. It handles schema creation, CRUD operations, and indexing.
"""

import logging
from pathlib import Path

import aiosqlite

from src.models import Article

logger = logging.getLogger(__name__)


class ArticleRepository:
    """
    Async SQLite repository for articles.

    This class provides all database operations for articles, including
    saving, retrieving, and querying articles with proper indexing and
    async support for optimal performance.

    Attributes:
        db_path: Path to the SQLite database file
    """

    def __init__(self, db_path: str = "data/articles.db") -> None:
        """
        Initialize the article repository.

        Args:
            db_path: Path to SQLite database file (created if doesn't exist)
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """
        Create database schema and indexes.

        This method creates the articles table if it doesn't exist and
        sets up indexes for optimal query performance.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guid TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    pub_date DATETIME NOT NULL,
                    description TEXT,
                    content TEXT,
                    image_url TEXT,
                    author TEXT,
                    categories TEXT,
                    source TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for better query performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pub_date ON articles(pub_date DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_guid ON articles(guid)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_source ON articles(source)")

            await db.commit()
            logger.info(f"Database initialized at {self.db_path}")

    async def save(self, article: Article) -> bool:
        """
        Save a single article to the database.

        Args:
            article: Article instance to save

        Returns:
            True if article was saved, False if duplicate (already exists)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                data = article.to_dict()
                await db.execute(
                    """
                    INSERT INTO articles (guid, title, url, pub_date, description,
                                        content, image_url, author, categories, source)
                    VALUES (:guid, :title, :url, :pub_date, :description,
                            :content, :image_url, :author, :categories, :source)
                """,
                    data,
                )
                await db.commit()
                logger.info(f"Saved article: {article.title}")
                return True
        except aiosqlite.IntegrityError:
            logger.debug(f"Duplicate article skipped: {article.guid}")
            return False

    async def save_many(self, articles: list[Article]) -> int:
        """
        Save multiple articles to the database.

        Args:
            articles: List of Article instances to save

        Returns:
            Count of new articles saved (excludes duplicates)
        """
        count = 0
        for article in articles:
            if await self.save(article):
                count += 1
        return count

    async def get_latest(self, limit: int = 50, source: str | None = None) -> list[Article]:
        """
        Get latest articles, optionally filtered by source.

        Args:
            limit: Maximum number of articles to return
            source: Optional source filter (e.g., "lol-en-us")

        Returns:
            List of Article instances, ordered by publication date (newest first)
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if source:
                cursor = await db.execute(
                    """
                    SELECT * FROM articles
                    WHERE source = ?
                    ORDER BY pub_date DESC
                    LIMIT ?
                """,
                    (source, limit),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM articles
                    ORDER BY pub_date DESC
                    LIMIT ?
                """,
                    (limit,),
                )

            rows = await cursor.fetchall()
            return [Article.from_dict(dict(row)) for row in rows]

    async def get_by_guid(self, guid: str) -> Article | None:
        """
        Get article by its unique GUID.

        Args:
            guid: Globally unique identifier for the article

        Returns:
            Article instance if found, None otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM articles WHERE guid = ?", (guid,))
            row = await cursor.fetchone()
            return Article.from_dict(dict(row)) if row else None

    async def count(self) -> int:
        """
        Get total count of articles in database.

        Returns:
            Total number of articles stored
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM articles")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    async def close(self) -> None:
        """
        Close database connections.

        This method is called during application shutdown.
        Since we use context managers for all DB operations,
        no explicit cleanup is needed.
        """
        logger.info("Database repository closed")
