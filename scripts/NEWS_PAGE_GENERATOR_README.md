# News Page Generator Documentation

## Overview

The News Page Generator creates a beautiful, responsive HTML page displaying the latest League of Legends news articles from the LoL Stonks RSS database. The page is designed for deployment to GitHub Pages or any static hosting service.

## Features

### Design Features
- **LoL Branding**: Uses official League of Legends colors (gold #C89B3C, blue #0AC8B9)
- **Responsive Design**: Mobile-friendly layout with grid system
- **Dark/Light Mode**: Theme toggle with localStorage persistence
- **Auto-refresh**: Page refreshes every 5 minutes to show latest content

### Functionality
- **Search**: Real-time search across article titles and descriptions
- **Filters**: Filter by source (EN-US, IT-IT, etc.) and category
- **Latest News**: Displays up to 500 articles (configurable)
- **Rich Metadata**: Shows source badges, category tags, publication dates
- **Images**: Article thumbnails with fallback gradients
- **External Links**: All articles link to original sources

## Usage

### Basic Usage

Generate a news page with default settings (50 articles, output to `news.html`):

```bash
python scripts/generate_news_page.py
```

### Advanced Usage

#### Custom Output Path

```bash
python scripts/generate_news_page.py --output docs/index.html
```

#### Custom Article Limit

```bash
python scripts/generate_news_page.py --limit 100
```

#### Combined Options

```bash
python scripts/generate_news_page.py --output public/news.html --limit 200
```

### Command Line Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | `news.html` | Output HTML file path |
| `--limit` | `-l` | `50` | Maximum articles (1-500) |
| `--help` | `-h` | - | Show help message |

## GitHub Pages Deployment

### Option 1: Manual Deployment

1. Generate the news page:
   ```bash
   python scripts/generate_news_page.py --output docs/index.html
   ```

2. Commit and push:
   ```bash
   git add docs/index.html
   git commit -m "Update news page"
   git push
   ```

3. Configure GitHub Pages:
   - Go to repository Settings > Pages
   - Select source: "Deploy from branch"
   - Select branch: `main` (or your default branch)
   - Select folder: `/docs`
   - Save

### Option 2: GitHub Actions Automation

Create `.github/workflows/update-news-page.yml`:

```yaml
name: Update News Page

on:
  schedule:
    - cron: '*/5 * * * *'  # Every 5 minutes
  workflow_dispatch:  # Manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Generate news page
        run: |
          python scripts/generate_news_page.py --output docs/index.html --limit 100

      - name: Commit and push
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add docs/index.html
          git diff --quiet && git diff --staged --quiet || git commit -m "Update news page [automated]"
          git push
```

## Output Structure

The generated HTML file includes:

### Header Section
- Logo and branding
- Dark/Light theme toggle
- Link to RSS feed

### Controls Section
- Search box for filtering articles
- Source filters (All, EN-US, IT-IT, etc.)
- Category filters (Champions, Patches, Media, etc.)
- Statistics (article count, last updated)

### News Grid
- Responsive card layout
- Article thumbnails
- Source and category badges
- Title and description
- Author and publication date
- Links to original articles

### Footer
- Links to RSS feeds (main, English, Italian)
- API health endpoint
- Official LoL website link
- Copyright information

## Technical Details

### Dependencies

The generator requires:
- `jinja2>=3.1.2` - HTML templating
- `aiosqlite>=0.19.0` - Database access
- `pydantic>=2.5.2` - Configuration management

These are included in `pyproject.toml` dependencies.

### Template System

The generator uses Jinja2 templates located in `templates/news_page.html`. The template includes:

- Full CSS styling with CSS variables for theming
- Responsive grid layout
- JavaScript for search and filtering
- Theme persistence with localStorage
- SEO meta tags

### Database Integration

The generator:
1. Connects to the SQLite database at `data/articles.db`
2. Fetches latest articles using `ArticleRepository`
3. Formats dates and categories
4. Extracts unique sources and categories for filters
5. Renders template with article data

### Performance Considerations

- **Lazy Loading**: Images use `loading="lazy"` attribute
- **Efficient Filtering**: Client-side JavaScript filtering (no page reload)
- **Caching**: Browser caching enabled for static assets
- **File Size**: Generated HTML typically 200-500 KB for 50 articles

## Customization

### Modifying the Template

Edit `templates/news_page.html` to customize:

- **Colors**: Modify CSS variables in `:root`
- **Layout**: Adjust grid columns in `.news-grid`
- **Branding**: Change logo and title in `.header`
- **Filters**: Add custom filter buttons
- **Styling**: Update any CSS rules

### Adding Custom Fields

To display additional article fields:

1. Ensure field exists in database schema (`src/database.py`)
2. Update `Article` model (`src/models.py`)
3. Modify template to display the field
4. Regenerate the page

## Troubleshooting

### No Articles Found

**Problem**: Generator outputs "No articles found in database"

**Solutions**:
- Ensure the application has run and fetched articles
- Check database path in config: `data/articles.db`
- Manually trigger update: `POST /admin/scheduler/trigger`

### Template Not Found

**Problem**: `jinja2.exceptions.TemplateNotFound: news_page.html`

**Solutions**:
- Verify `templates/` directory exists in project root
- Ensure `news_page.html` exists in `templates/`
- Check file permissions

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'jinja2'`

**Solutions**:
```bash
# Using uv
uv sync

# Using pip
pip install -r requirements.txt

# Or install directly
pip install jinja2
```

### Permission Errors

**Problem**: Cannot write output file

**Solutions**:
- Check write permissions for output directory
- Ensure directory exists or will be created
- Run with appropriate permissions

## Examples

### Example 1: Generate for GitHub Pages

```bash
# Generate to docs/ for GitHub Pages
python scripts/generate_news_page.py --output docs/index.html --limit 100

# Verify output
ls -lh docs/index.html
```

### Example 2: Generate Multiple Versions

```bash
# Full version
python scripts/generate_news_page.py --output news-full.html --limit 200

# Recent only
python scripts/generate_news_page.py --output news-recent.html --limit 20
```

### Example 3: Automated Updates

Create a cron job (Linux/Mac):

```bash
# Update every 5 minutes
*/5 * * * * cd /path/to/lolstonksrss && python scripts/generate_news_page.py
```

Or Windows Task Scheduler:

```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute 'python' -Argument 'D:\lolstonksrss\scripts\generate_news_page.py'
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "LoL News Update" -Action $action -Trigger $trigger
```

## API Integration

The generated page can also be served via the FastAPI application. Add to `src/api/app.py`:

```python
from fastapi.responses import FileResponse

@app.get("/news", response_class=FileResponse)
async def serve_news_page() -> FileResponse:
    """Serve the generated news page."""
    return FileResponse("news.html")
```

## Testing

Test the generator:

```bash
# Run with verbose output
python scripts/generate_news_page.py --output test-news.html --limit 10

# Verify output exists
test -f test-news.html && echo "Success" || echo "Failed"

# Check file size
ls -lh test-news.html

# Open in browser (Linux)
xdg-open test-news.html

# Open in browser (Mac)
open test-news.html

# Open in browser (Windows)
start test-news.html
```

## Future Enhancements

Potential improvements:

- [ ] Add pagination for large article sets
- [ ] Include article statistics and charts
- [ ] Add social sharing buttons
- [ ] Implement service worker for offline support
- [ ] Add RSS feed auto-discovery meta tags
- [ ] Generate sitemap.xml for SEO
- [ ] Add JSON-LD structured data
- [ ] Support for more languages
- [ ] Custom themes/skins
- [ ] Export to PDF functionality

## License

This generator is part of the LoL Stonks RSS project and is licensed under the MIT License.

## Support

For issues or questions:
- Check existing GitHub issues
- Create new issue with "news-page-generator" label
- Include error messages and system info
