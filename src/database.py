"""
Database repository for article storage using SQLite.

This module provides an async SQLite repository for storing and retrieving
news articles. It handles schema creation, CRUD operations, indexing,
and database migrations for multi-source, multi-locale support.
"""

import logging
from pathlib import Path
from typing import Any

import aiosqlite

from src.models import Article

logger = logging.getLogger(__name__)


class ArticleRepository:
    """
    Async SQLite repository for articles.

    This class provides all database operations for articles, including
    saving, retrieving, and querying articles with proper indexing and
    async support for optimal performance. Supports multi-source and
    multi-locale queries with migration support.

    Attributes:
        db_path: Path to the SQLite database file
    """

    # Current database schema version
    SCHEMA_VERSION = 2

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
        sets up indexes for optimal query performance. Automatically
        runs migrations if needed.
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Create schema_version table FIRST (needed by migrate_to_v2)
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """
            )

            # Create articles table
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
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    locale TEXT DEFAULT 'en-us',
                    source_category TEXT,
                    canonical_url TEXT
                )
            """
            )

        # Run migration if needed (handles existing tables with old schema)
        # This must run outside the connection block above since migrate_to_v2 opens its own connection
        await self.migrate_to_v2()

        # Now create indexes in a new connection
        async with aiosqlite.connect(self.db_path) as db:
            # Create indexes for better query performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pub_date ON articles(pub_date DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_guid ON articles(guid)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_source ON articles(source)")

            # Multi-language/multi-source indexes (these will succeed after migrate_to_v2)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_locale ON articles(locale)")
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_locale ON articles(source, locale)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_pub_date_locale ON articles(pub_date DESC, locale)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_category ON articles(source_category)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_canonical_url ON articles(canonical_url)"
            )

            # Check if we need to insert initial version
            cursor = await db.execute("SELECT MAX(version) as v FROM schema_version")
            row = await cursor.fetchone()
            current_version = row[0] if row and row[0] else 0

            if current_version < self.SCHEMA_VERSION:
                await db.execute(
                    "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                    (self.SCHEMA_VERSION,),
                )
                await db.commit()

            await db.commit()
            logger.info(f"Database initialized at {self.db_path} (schema v{self.SCHEMA_VERSION})")

    async def migrate_to_v2(self) -> None:
        """
        Migrate database from v1 to v2 for multi-source, multi-locale support.

        This method adds new columns for locale tracking, source categorization,
        and deduplication across sources. Idempotent - can be run multiple times.
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Check if migration is needed
            cursor = await db.execute("PRAGMA table_info(articles)")
            columns = [row[1] for row in await cursor.fetchall()]

            # Add locale column if missing
            if "locale" not in columns:
                await db.execute(
                    """
                    ALTER TABLE articles ADD COLUMN locale TEXT DEFAULT 'en-us'
                """
                )
                logger.info("Added locale column to articles table")

            # Add source_category column if missing
            if "source_category" not in columns:
                await db.execute(
                    """
                    ALTER TABLE articles ADD COLUMN source_category TEXT
                """
                )
                logger.info("Added source_category column to articles table")

            # Add canonical_url column if missing
            if "canonical_url" not in columns:
                await db.execute(
                    """
                    ALTER TABLE articles ADD COLUMN canonical_url TEXT
                """
                )
                logger.info("Added canonical_url column to articles table")

            # Create new indexes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_locale ON articles(locale)")
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_locale ON articles(source, locale)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_pub_date_locale ON articles(pub_date DESC, locale)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_category ON articles(source_category)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_canonical_url ON articles(canonical_url)"
            )

            # Update schema version
            await db.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,)
            )

            await db.commit()
            logger.info("Database migrated to v2 (multi-source, multi-locale support)")

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
                    INSERT INTO articles (
                        guid, title, url, pub_date, description,
                        content, image_url, author, categories, source,
                        created_at, locale, source_category, canonical_url
                    )
                    VALUES (
                        :guid, :title, :url, :pub_date, :description,
                        :content, :image_url, :author, :categories, :source,
                        :created_at, :locale, :source_category, :canonical_url
                    )
                """,
                    data,
                )
                await db.commit()
                logger.info(f"Saved article: {article.title[:50]}...")
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

    async def get_latest(
        self, limit: int = 50, source: str | None = None, locale: str | None = None
    ) -> list[Article]:
        """
        Get latest articles, optionally filtered by source and/or locale.

        Args:
            limit: Maximum number of articles to return
            source: Optional source filter (e.g., "lol:en-us")
            locale: Optional locale filter (e.g., "en-us", "it-it")

        Returns:
            List of Article instances, ordered by publication date (newest first)
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            query = "SELECT * FROM articles WHERE 1=1"
            params: list[Any] = []

            if source:
                query += " AND source = ?"
                params.append(source)

            if locale:
                query += " AND locale = ?"
                params.append(locale)

            query += " ORDER BY pub_date DESC LIMIT ?"
            params.append(limit)

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [Article.from_dict(dict(row)) for row in rows]

    async def get_latest_by_locale(
        self,
        locale: str,
        limit: int = 50,
        source_category: str | None = None,
    ) -> list[Article]:
        """
        Get latest articles for a specific locale, optionally filtered by source category.

        Args:
            locale: Locale code (e.g., "en-us", "it-it")
            limit: Maximum number of articles to return
            source_category: Optional source category filter (e.g., "official_riot", "analytics")

        Returns:
            List of Article instances for the locale, ordered by publication date
        """
        query = """
            SELECT * FROM articles
            WHERE locale = ?
        """
        params: list[Any] = [locale]

        if source_category:
            query += " AND source_category = ?"
            params.append(source_category)

        query += " ORDER BY pub_date DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [Article.from_dict(dict(row)) for row in rows]

    async def get_by_locale_group(
        self,
        locale_group: list[str],
        limit: int = 50,
        source_category: str | None = None,
    ) -> list[Article]:
        """
        Get latest articles for a group of locales.

        Args:
            locale_group: List of locale codes (e.g., ["en-us", "en-gb"])
            limit: Maximum number of articles to return
            source_category: Optional source category filter

        Returns:
            List of Article instances for the locale group
        """
        placeholders = ",".join("?" * len(locale_group))
        # nosec B608 - safe: placeholders only contains ? characters
        query = f"""
            SELECT * FROM articles
            WHERE locale IN ({placeholders})
        """
        params: list[Any] = list(locale_group)

        if source_category:
            query += " AND source_category = ?"
            params.append(source_category)

        query += " ORDER BY pub_date DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [Article.from_dict(dict(row)) for row in rows]

    async def get_by_source_category(
        self,
        source_category: str,
        locale: str | None = None,
        limit: int = 50,
    ) -> list[Article]:
        """
        Get latest articles by source category.

        Args:
            source_category: Category to filter by (e.g., "official_riot", "analytics")
            locale: Optional locale filter
            limit: Maximum number of articles to return

        Returns:
            List of Article instances matching the category
        """
        query = """
            SELECT * FROM articles
            WHERE source_category = ?
        """
        params: list[Any] = [source_category]

        if locale:
            query += " AND locale = ?"
            params.append(locale)

        query += " ORDER BY pub_date DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
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

    async def get_by_canonical_url(self, canonical_url: str) -> Article | None:
        """
        Get article by canonical URL (for deduplication across sources).

        Args:
            canonical_url: Primary URL to search for

        Returns:
            Article instance if found, None otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM articles WHERE canonical_url = ?", (canonical_url,)
            )
            row = await cursor.fetchone()
            return Article.from_dict(dict(row)) if row else None

    async def count(self, locale: str | None = None) -> int:
        """
        Get total count of articles in database, optionally filtered by locale.

        Args:
            locale: Optional locale filter

        Returns:
            Total number of articles stored
        """
        async with aiosqlite.connect(self.db_path) as db:
            if locale:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM articles WHERE locale = ?", (locale,)
                )
            else:
                cursor = await db.execute("SELECT COUNT(*) FROM articles")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    async def get_locales(self) -> list[str]:
        """
        Get list of all locales that have articles.

        Returns:
            List of locale codes
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT DISTINCT locale FROM articles ORDER BY locale")
            rows = await cursor.fetchall()
            return [row[0] for row in rows if row[0]]

    async def get_source_categories(self) -> list[str]:
        """
        Get list of all source categories that have articles.

        Returns:
            List of source category names
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT DISTINCT source_category FROM articles WHERE source_category IS NOT NULL ORDER BY source_category"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows if row[0]]

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> aiosqlite.Cursor:
        """
        Execute a raw SQL statement.

        Args:
            sql: SQL statement to execute
            params: Optional parameters for the SQL statement

        Returns:
            aiosqlite cursor
        """
        async with aiosqlite.connect(self.db_path) as db:
            return await db.execute(sql, params)

    async def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[Any]:
        """
        Execute SQL and fetch all results.

        Args:
            sql: SQL query to execute
            params: Optional parameters for the SQL query

        Returns:
            List of result rows
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            return list(rows)

    async def close(self) -> None:
        """
        Close database connections.

        This method is called during application shutdown.
        Since we use context managers for all DB operations,
        no explicit cleanup is needed.
        """
        logger.info("Database repository closed")
