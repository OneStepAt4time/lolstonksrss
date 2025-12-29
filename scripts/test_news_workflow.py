"""
Test script for GitHub Pages news publishing workflow.

This script simulates the workflow steps locally to verify everything works
before pushing to GitHub Actions.

Usage:
    python scripts/test_news_workflow.py
    python scripts/test_news_workflow.py --limit 50
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings  # noqa: E402
from src.database import ArticleRepository  # noqa: E402
from src.services.update_service import UpdateService  # noqa: E402


async def test_workflow(article_limit: int = 100) -> bool:
    """
    Test all workflow steps locally.

    Args:
        article_limit: Number of articles to include in the page

    Returns:
        True if all steps pass, False otherwise
    """
    print("=" * 70)
    print("Testing GitHub Pages News Publishing Workflow")
    print("=" * 70)
    print()

    success = True

    # Step 1: Initialize database
    print("[1/4] Initializing database...")
    try:
        settings = get_settings()
        repo = ArticleRepository(settings.database_path)
        await repo.initialize()
        print("  ✓ Database initialized successfully")
    except Exception as e:
        print(f"  ✗ Database initialization failed: {e}")
        return False

    # Step 2: Fetch latest news
    print("\n[2/4] Fetching latest news from LoL API...")
    try:
        update_service = UpdateService(repo)
        stats = await update_service.update_all_sources()

        print("  ✓ Update complete:")
        print(f"    - Total fetched: {stats['total_fetched']}")
        print(f"    - New articles: {stats['total_new']}")
        print(f"    - Duplicates: {stats['total_duplicates']}")
        print(f"    - Errors: {len(stats['errors'])}")

        if stats["errors"]:
            print("  ⚠ Errors encountered:")
            for error in stats["errors"]:
                print(f"    - {error}")

    except Exception as e:
        print(f"  ✗ News fetch failed: {e}")
        success = False

    # Step 3: Generate HTML page
    print(f"\n[3/4] Generating news HTML page (limit: {article_limit})...")
    try:
        from scripts.generate_news_page import generate_news_page

        output_path = project_root / "news.html"
        await generate_news_page(output_path=str(output_path), limit=article_limit)
        print(f"  ✓ News page generated: {output_path}")

        # Check file size
        file_size = output_path.stat().st_size / 1024
        print(f"    - File size: {file_size:.2f} KB")

        if file_size < 10:
            print("  ⚠ Warning: File size is very small, may be empty")
            success = False

    except Exception as e:
        print(f"  ✗ HTML generation failed: {e}")
        import traceback

        traceback.print_exc()
        success = False

    # Step 4: Create GitHub Pages structure
    print("\n[4/4] Creating GitHub Pages directory structure...")
    try:
        site_dir = project_root / "_site"
        site_dir.mkdir(exist_ok=True)

        # Copy news.html to index.html
        news_file = project_root / "news.html"
        index_file = site_dir / "index.html"

        if news_file.exists():
            import shutil

            shutil.copy(news_file, index_file)
            print(f"  ✓ Copied {news_file} to {index_file}")
        else:
            print(f"  ✗ Source file not found: {news_file}")
            success = False

        # Create redirect for news.html
        redirect_file = site_dir / "news.html"
        redirect_content = (
            "<!DOCTYPE html><html><head>"
            '<meta http-equiv="refresh" content="0; url=index.html">'
            "</head><body>Redirecting...</body></html>"
        )
        redirect_file.write_text(redirect_content)
        print(f"  ✓ Created redirect: {redirect_file}")

        # Create .nojekyll
        nojekyll_file = site_dir / ".nojekyll"
        nojekyll_file.touch()
        print("  ✓ Created .nojekyll file")

        print(f"\n  ✓ GitHub Pages structure created in {site_dir}")

    except Exception as e:
        print(f"  ✗ Directory structure creation failed: {e}")
        success = False

    # Cleanup
    await repo.close()

    # Summary
    print("\n" + "=" * 70)
    if success:
        print("✓ All workflow steps completed successfully!")
        print("\nNext steps:")
        print("  1. Review the generated news.html file")
        print("  2. Open _site/index.html in a browser to preview")
        print("  3. Push .github/workflows/publish-news.yml to GitHub")
        print("  4. Enable GitHub Pages in repository settings")
        print("\nDocumentation:")
        print("  - Quick start: GITHUB_PAGES_QUICKSTART.md")
        print("  - Setup guide: docs/SETUP_GITHUB_PAGES.md")
        print("  - Full docs: docs/GITHUB_PAGES_NEWS.md")
    else:
        print("✗ Some steps failed. Review the errors above.")
        print("\nTroubleshooting:")
        print("  1. Check that dependencies are installed")
        print("  2. Verify database path is writable")
        print("  3. Test LoL API connectivity")
        print("  4. Review error messages and stack traces")

    print("=" * 70)

    return success


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test GitHub Pages news publishing workflow locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=100,
        help="Number of articles to include (default: 100)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_arguments()

    print(f"\nTesting workflow with article limit: {args.limit}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        success = asyncio.run(test_workflow(article_limit=args.limit))
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
