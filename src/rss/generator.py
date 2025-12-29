"""
RSS 2.0 feed generator for League of Legends news.

This module provides the RSSFeedGenerator class which transforms Article objects
into RSS 2.0 compliant XML feeds using the feedgen library.
"""

import logging
from datetime import UTC, datetime

from feedgen.feed import FeedGenerator

from src.models import Article, ArticleSource

logger = logging.getLogger(__name__)


class RSSFeedGenerator:
    """
    RSS 2.0 feed generator for League of Legends news.

    Creates RSS feeds from Article objects with full RSS 2.0 compliance.
    Supports filtering by source and category, multiple languages, and
    all standard RSS elements including enclosures for images.

    Attributes:
        feed_title: Title of the RSS feed
        feed_link: Website URL associated with the feed
        feed_description: Description of the feed content
        language: Feed language code (e.g., 'en', 'it')
    """

    def __init__(
        self,
        feed_title: str = "League of Legends News",
        feed_link: str = "https://www.leagueoflegends.com/news",
        feed_description: str = "Latest news from League of Legends",
        language: str = "en",
    ) -> None:
        """
        Initialize RSS feed generator.

        Args:
            feed_title: Main feed title
            feed_link: Feed website URL
            feed_description: Feed description
            language: Feed language (en, it, etc.)
        """
        self.feed_title = feed_title
        self.feed_link = feed_link
        self.feed_description = feed_description
        self.language = language

    def generate_feed(self, articles: list[Article], feed_url: str) -> str:
        """
        Generate RSS 2.0 XML feed from articles.

        Creates a complete RSS 2.0 feed with channel metadata and items.
        The feed includes all required and recommended RSS elements.

        Args:
            articles: List of Article objects to include in the feed
            feed_url: Self URL of the feed (for rel='self' link)

        Returns:
            RSS 2.0 XML string with proper encoding and structure
        """
        fg = FeedGenerator()

        # Feed metadata (required channel elements)
        fg.id(feed_url)
        fg.title(self.feed_title)
        fg.link(href=self.feed_link, rel="alternate")
        fg.link(href=feed_url, rel="self")
        fg.description(self.feed_description)
        fg.language(self.language)

        # Optional channel elements
        fg.lastBuildDate(datetime.now(UTC))
        fg.generator("LoL Stonks RSS Generator")

        # Add articles as feed entries
        for article in articles:
            self._add_article_entry(fg, article)

        # Generate RSS 2.0 XML
        rss_bytes = fg.rss_str(pretty=True)

        logger.info(f"Generated RSS feed with {len(articles)} items")

        return rss_bytes.decode("utf-8")

    def _add_article_entry(self, fg: FeedGenerator, article: Article) -> None:
        """
        Add article as RSS feed entry.

        Creates a complete RSS item with all available metadata.

        RSS 2.0 item structure:
        <item>
          <title>Article Title</title>
          <link>https://...</link>
          <guid isPermaLink="true">unique-id</guid>
          <pubDate>Sat, 28 Dec 2025 10:00:00 +0000</pubDate>
          <description>Article description...</description>
          <content:encoded>Full HTML content</content:encoded>
          <author>author@example.com (Author Name)</author>
          <category>Category</category>
          <enclosure url="image.jpg" type="image/jpeg" length="0"/>
        </item>

        Args:
            fg: FeedGenerator instance to add entry to
            article: Article object to convert to RSS item
        """
        fe = fg.add_entry()

        # Required fields
        fe.id(article.guid)
        fe.title(article.title)
        fe.link(href=article.url)

        # Ensure pub_date is timezone-aware
        pub_date = article.pub_date
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=UTC)
        fe.pubDate(pub_date)

        # Optional fields
        if article.description:
            fe.description(article.description)

        if article.content:
            # Use content:encoded for full HTML content
            fe.content(article.content, type="html")

        if article.author:
            # RSS 2.0 author format: email (name)
            # Use generic email since we don't have real emails
            fe.author(name=article.author, email="noreply@riotgames.com")

        # Categories
        for category in article.categories:
            if category:  # Skip empty categories
                fe.category(term=category)

        # Add source as a category
        fe.category(term=article.source.value)

        # Enclosure (image)
        if article.image_url:
            # feedgen requires length parameter
            # Use '0' as placeholder (valid per RSS spec)
            fe.enclosure(
                url=article.image_url,
                length="0",
                type="image/jpeg",  # Assume JPEG, could be enhanced
            )

    def generate_feed_by_source(
        self, articles: list[Article], source: ArticleSource, feed_url: str
    ) -> str:
        """
        Generate RSS feed filtered by source.

        Filters articles by source and updates the feed title to reflect
        the filtering. Useful for language-specific feeds.

        Args:
            articles: All available articles
            source: Source to filter by (e.g., LOL_EN_US)
            feed_url: Self URL of the feed

        Returns:
            RSS 2.0 XML string with filtered articles
        """
        filtered = [a for a in articles if a.source == source]

        # Update feed title to include source
        original_title = self.feed_title
        self.feed_title = f"{original_title} - {source.value}"

        try:
            feed_xml = self.generate_feed(filtered, feed_url)
        finally:
            # Restore original title
            self.feed_title = original_title

        return feed_xml

    def generate_feed_by_category(
        self, articles: list[Article], category: str, feed_url: str
    ) -> str:
        """
        Generate RSS feed filtered by category.

        Filters articles by category and updates the feed title to reflect
        the filtering. Useful for topic-specific feeds.

        Args:
            articles: All available articles
            category: Category name to filter by
            feed_url: Self URL of the feed

        Returns:
            RSS 2.0 XML string with filtered articles
        """
        filtered = [a for a in articles if category in a.categories]

        # Update feed title to include category
        original_title = self.feed_title
        self.feed_title = f"{original_title} - {category}"

        try:
            feed_xml = self.generate_feed(filtered, feed_url)
        finally:
            # Restore original title
            self.feed_title = original_title

        return feed_xml
