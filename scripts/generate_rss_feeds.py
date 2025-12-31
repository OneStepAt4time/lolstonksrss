"""
Generate RSS 2.0 feeds for GitHub Pages deployment.

This script fetches articles from the database and generates three RSS feeds:
- feed.xml (all articles, all languages)
- feed/en-us.xml (English articles only)
- feed/it-it.xml (Italian articles only)

Usage:
    python scripts/generate_rss_feeds.py
    python scripts/generate_rss_feeds.py --output _site
    python scripts/generate_rss_feeds.py --limit 100
    python scripts/generate_rss_feeds.py --base-url https://example.com
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Final

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings  # noqa: E402
from src.database import ArticleRepository  # noqa: E402
from src.models import ArticleSource  # noqa: E402
from src.rss.generator import RSSFeedGenerator  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: Final[logging.Logger] = logging.getLogger(__name__)


# Feed configuration for GitHub Pages
FEED_CONFIGS: Final[dict[str, dict]] = {
    "all": {
        "filename": "feed.xml",
        "title": "League of Legends News",
        "description": "Latest League of Legends news and updates",
        "language": "en",
        "source": None,
    },
    "en-us": {
        "filename": "feed/en-us.xml",
        "title": "League of Legends News",
        "description": "Latest League of Legends news and updates (English)",
        "language": "en",
        "source": ArticleSource.LOL_EN_US,
    },
    "it-it": {
        "filename": "feed/it-it.xml",
        "title": "Notizie League of Legends",
        "description": "Ultime notizie e aggiornamenti di League of Legends (Italiano)",
        "language": "it",
        "source": ArticleSource.LOL_IT_IT,
    },
}


# GitHub Pages base URL
GITHUB_PAGES_URL = "https://onestepat4time.github.io/lolstonksrss"


def create_feed_generators() -> dict[str, RSSFeedGenerator]:
    """
    Create RSS feed generators for different languages.

    Returns:
        Dictionary mapping language codes to their generators
    """
    generators = {}

    # English generator
    generators["en"] = RSSFeedGenerator(
        feed_title="League of Legends News",
        feed_link="https://www.leagueoflegends.com/news",
        feed_description="Latest news and updates from League of Legends",
        language="en",
    )

    # Italian generator
    generators["it"] = RSSFeedGenerator(
        feed_title="Notizie League of Legends",
        feed_link="https://www.leagueoflegends.com/it-it/news/",
        feed_description="Ultime notizie e aggiornamenti di League of Legends",
        language="it",
    )

    return generators


async def generate_feeds(
    output_dir: str | Path = "_site",
    limit: int = 100,
    base_url: str | None = None,
) -> dict[str, int]:
    """
    Generate all RSS feeds from database articles.

    Args:
        output_dir: Directory where feed files will be saved
        limit: Maximum number of articles per feed
        base_url: Base URL for feed links (default: GITHUB_PAGES_URL)

    Returns:
        Dictionary mapping feed file paths to their sizes in bytes

    Raises:
        OSError: If directory creation or file write fails
        Exception: If database query fails or feed generation fails
    """
    logger.info("=" * 60)
    logger.info("RSS Feed Generator for GitHub Pages")
    logger.info("=" * 60)
    logger.info(f"Generating RSS feeds with up to {limit} articles per feed...")

    # Determine base URL
    feed_base_url = base_url or GITHUB_PAGES_URL
    logger.info(f"Using base URL: {feed_base_url}")

    # Get settings and initialize repository
    settings = get_settings()
    logger.info(f"Database path: {settings.database_path}")

    repository = ArticleRepository(settings.database_path)
    await repository.initialize()

    # Create output directory
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_path.absolute()}")
    except OSError as e:
        logger.error(f"Failed to create output directory: {e}")
        raise

    # Create feed subdirectory
    feed_dir = output_path / "feed"
    try:
        feed_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create feed subdirectory: {e}")
        raise

    # Get generators
    generators = create_feed_generators()

    # Track generated feeds
    generated = {}

    # Generate feeds according to FEED_CONFIGS
    for feed_key, config in FEED_CONFIGS.items():
        logger.info(f"Generating {feed_key} feed...")

        try:
            # Fetch articles
            source = config.get("source")
            if source:
                articles = await repository.get_latest(limit=limit, source=source.value)
                logger.info(f"Fetched {len(articles)} articles for {source.value}")
            else:
                articles = await repository.get_latest(limit=limit)
                logger.info(f"Fetched {len(articles)} total articles")

            # Select generator based on language
            generator = generators[config["language"]]

            # Build feed URL
            feed_url = f"{feed_base_url}/{config['filename']}"

            # Generate RSS XML (articles are already filtered by source if provided)
            feed_xml = generator.generate_feed(articles, feed_url)

            # Determine output path
            feed_path = output_path / config["filename"]

            # Write to file
            feed_path.write_text(feed_xml, encoding="utf-8")
            generated[str(feed_path)] = feed_path.stat().st_size

            logger.info(
                f"Feed saved: {feed_path.absolute()} " f"({feed_path.stat().st_size / 1024:.2f} KB)"
            )

        except Exception as e:
            logger.error(f"Failed to generate {feed_key} feed: {e}")
            raise

    # Close repository
    await repository.close()

    return generated


def validate_feeds(feeds: dict[str, int]) -> bool:
    """
    Validate generated RSS feeds.

    Args:
        feeds: Dictionary of feed file paths to sizes

    Returns:
        True if all feeds are valid, False otherwise
    """
    all_valid = True

    for feed_path, size in feeds.items():
        path = Path(feed_path)

        # Check file exists
        if not path.exists():
            print(f"ERROR: Feed file not found: {feed_path}")
            all_valid = False
            continue

        # Check file size
        if size == 0:
            print(f"WARNING: Feed file is empty: {feed_path}")
            all_valid = False
            continue

        # Check XML structure
        content = path.read_text(encoding="utf-8")

        # Basic RSS validation
        if not content.strip().startswith("<?xml"):
            print(f"WARNING: Feed doesn't start with XML declaration: {feed_path}")
        if "<rss" not in content:
            print(f"ERROR: Feed missing <rss> tag: {feed_path}")
            all_valid = False
        if "<channel>" not in content:
            print(f"ERROR: Feed missing <channel> tag: {feed_path}")
            all_valid = False

        if all_valid:
            print(f"Feed validated: {feed_path}")

    return all_valid


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate RSS 2.0 feeds for GitHub Pages deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate feeds with default settings:
    python scripts/generate_rss_feeds.py

  Generate feeds to custom output directory:
    python scripts/generate_rss_feeds.py --output _site

  Generate feeds with more articles:
    python scripts/generate_rss_feeds.py --limit 100

  Generate feeds with custom base URL:
    python scripts/generate_rss_feeds.py --base-url https://example.com

  Combine options:
    python scripts/generate_rss_feeds.py --output public --limit 200 --base-url https://example.com

Generated feeds:
  - feed.xml       (all articles, all languages)
  - feed/en-us.xml (English articles only)
  - feed/it-it.xml (Italian articles only)
        """,
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="_site",
        help="Output directory for RSS feeds (default: _site)",
    )

    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=50,
        help="Maximum number of articles per feed (default: 50, max: 500)",
    )

    parser.add_argument(
        "--base-url",
        "-b",
        type=str,
        default=None,
        help="Base URL for feed links (default: from GITHUB_PAGES_URL)",
    )

    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip feed validation after generation",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the script.

    Parses arguments, configures logging, and runs the async generator.
    """
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate limit
    if args.limit < 1:
        logger.error("Limit must be at least 1")
        sys.exit(1)

    if args.limit > 500:
        logger.warning("Limit capped at 500 articles for performance")
        args.limit = 500

    # Validate output path
    try:
        output_path = Path(args.output)
        # Test if we can create the directory
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Cannot create output directory '{args.output}': {e}")
        sys.exit(1)

    # Run async function
    try:
        feeds = asyncio.run(
            generate_feeds(
                output_dir=args.output,
                limit=args.limit,
                base_url=args.base_url,
            )
        )

        # Validate feeds
        if not args.no_validate:
            logger.info("Validating feeds...")
            valid = validate_feeds(feeds)

            if not valid:
                logger.warning("Some feeds failed validation")
                sys.exit(1)

        # Print summary
        logger.info("=" * 60)
        logger.info("RSS Feed Generation Complete")
        logger.info("=" * 60)
        logger.info(f"Total feeds generated: {len(feeds)}")
        logger.info(f"Output directory: {Path(args.output).absolute()}")

        # Use base URL for public URLs
        feed_base_url = args.base_url or GITHUB_PAGES_URL

        logger.info("Generated feeds:")
        for feed_path, size in feeds.items():
            rel_path = Path(feed_path).relative_to(project_root)
            logger.info(f"  - {rel_path} ({size / 1024:.2f} KB)")

        logger.info("Public URLs:")
        logger.info(f"  - {feed_base_url}/feed.xml")
        logger.info(f"  - {feed_base_url}/feed/en-us.xml")
        logger.info(f"  - {feed_base_url}/feed/it-it.xml")

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error generating RSS feeds: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
