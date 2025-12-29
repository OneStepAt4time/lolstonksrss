"""
Generate HTML news page for GitHub Pages.

This script fetches articles from the database and generates a beautiful,
responsive HTML page with LoL branding for deployment to GitHub Pages.

Usage:
    python scripts/generate_news_page.py
    python scripts/generate_news_page.py --output news.html
    python scripts/generate_news_page.py --limit 100
    python scripts/generate_news_page.py --output custom.html --limit 75
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings  # noqa: E402
from src.database import ArticleRepository  # noqa: E402


async def fetch_articles(repository: ArticleRepository, limit: int) -> list[dict[str, Any]]:
    """
    Fetch articles from database and prepare for template.

    Args:
        repository: Article repository instance
        limit: Maximum number of articles to fetch

    Returns:
        List of article dictionaries with formatted data
    """
    articles = await repository.get_latest(limit=limit)

    # Prepare articles for template
    articles_data = []
    for article in articles:
        article_dict = article.to_dict()

        # Format publication date
        try:
            pub_date = datetime.fromisoformat(article_dict["pub_date"])
            article_dict["pub_date_formatted"] = pub_date.strftime("%B %d, %Y at %I:%M %p")
        except (ValueError, KeyError):
            article_dict["pub_date_formatted"] = "Unknown date"

        # Ensure categories is a list
        if isinstance(article_dict.get("categories"), str):
            article_dict["categories"] = [
                cat.strip() for cat in article_dict["categories"].split(",") if cat.strip()
            ]
        elif not article_dict.get("categories"):
            article_dict["categories"] = []

        articles_data.append(article_dict)

    return articles_data


def extract_unique_values(articles: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """
    Extract unique sources and categories from articles.

    Args:
        articles: List of article dictionaries

    Returns:
        Tuple of (sources, categories) lists
    """
    sources = set()
    categories = set()

    for article in articles:
        # Extract source
        source = article.get("source", "")
        if source:
            sources.add(source)

        # Extract categories
        article_categories = article.get("categories", [])
        if isinstance(article_categories, list):
            categories.update(article_categories)
        elif isinstance(article_categories, str) and article_categories:
            categories.update([cat.strip() for cat in article_categories.split(",") if cat.strip()])

    return sorted(sources), sorted(categories)


async def generate_news_page(output_path: str = "news.html", limit: int = 50) -> None:
    """
    Generate HTML news page from database articles.

    This function:
    1. Fetches latest articles from the database
    2. Renders them using the Jinja2 template
    3. Saves the result to an HTML file

    Args:
        output_path: Path where HTML file will be saved (default: news.html)
        limit: Maximum number of articles to include (default: 50)

    Raises:
        Exception: If database connection or template rendering fails
    """
    print(f"Generating news page with up to {limit} articles...")

    # Get settings and initialize repository
    settings = get_settings()
    repository = ArticleRepository(settings.database_path)
    await repository.initialize()

    # Fetch articles
    print(f"Fetching articles from database: {settings.database_path}")
    articles = await fetch_articles(repository, limit)
    print(f"Fetched {len(articles)} articles")

    if not articles:
        print("Warning: No articles found in database. Generating empty page.")

    # Extract unique sources and categories
    sources, categories = extract_unique_values(articles)
    print(f"Found {len(sources)} sources: {sources}")
    print(f"Found {len(categories)} categories: {categories}")

    # Setup Jinja2 environment
    templates_dir = project_root / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Load template
    template = env.get_template("news_page.html")

    # Prepare template context
    context = {
        "articles": articles,
        "sources": sources,
        "categories": categories,
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_articles": len(articles),
    }

    # Render template
    print("Rendering HTML template...")
    html_content = template.render(**context)

    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write to file
    output_file.write_text(html_content, encoding="utf-8")
    print(f"News page generated successfully: {output_file.absolute()}")
    print(f"File size: {output_file.stat().st_size / 1024:.2f} KB")

    # Close repository
    await repository.close()


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate HTML news page for League of Legends articles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate default news page:
    python scripts/generate_news_page.py

  Generate with custom output path:
    python scripts/generate_news_page.py --output docs/news.html

  Generate with more articles:
    python scripts/generate_news_page.py --limit 100

  Combine options:
    python scripts/generate_news_page.py --output public/index.html --limit 200
        """,
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="news.html",
        help="Output HTML file path (default: news.html)",
    )

    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=50,
        help="Maximum number of articles to include (default: 50, max: 500)",
    )

    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the script.

    Parses arguments and runs the async generator function.
    """
    args = parse_arguments()

    # Validate limit
    if args.limit < 1:
        print("Error: Limit must be at least 1", file=sys.stderr)
        sys.exit(1)

    if args.limit > 500:
        print("Warning: Limit capped at 500 articles for performance")
        args.limit = 500

    # Run async function
    try:
        asyncio.run(generate_news_page(output_path=args.output, limit=args.limit))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error generating news page: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
