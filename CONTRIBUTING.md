# Contributing to LoL Stonks RSS

Thank you for considering contributing to LoL Stonks RSS! This project provides an RSS feed for League of Legends news, helping players stay informed about game updates, patches, and announcements.

Your contributions help make this tool more reliable, feature-rich, and accessible to the League of Legends community.

## Table of Contents

- [Ways to Contribute](#ways-to-contribute)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Contributions](#code-contributions)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation Requirements](#documentation-requirements)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Code Review](#code-review)
- [Release Process](#release-process)
- [Community Guidelines](#community-guidelines)
- [Recognition](#recognition)
- [License](#license)

## Ways to Contribute

There are many ways to contribute to LoL Stonks RSS:

### Report Bugs
Found a bug? Help us improve by reporting it:
- RSS feed parsing errors
- Scraping failures
- Docker deployment issues
- Windows-specific problems

### Suggest Features
Have ideas for improvements?
- New RSS feed features
- Additional news sources
- Performance optimizations
- Deployment enhancements

### Improve Documentation
Documentation is crucial:
- Fix typos or clarify instructions
- Add usage examples
- Improve setup guides
- Write tutorials

### Submit Code
Contribute code improvements:
- Fix bugs
- Implement new features
- Optimize performance
- Improve error handling

### Review Pull Requests
Help review code from other contributors:
- Test proposed changes
- Provide constructive feedback
- Suggest improvements

### Help Users
Support the community:
- Answer questions in issues
- Share deployment experiences
- Help troubleshoot problems

## Getting Started

### Prerequisites

- **Python 3.11 or higher**
- **UV** package manager (recommended) or pip
- **Git** for version control
- **Docker Desktop** (for Windows deployment testing)
- **Basic understanding** of Python, async/await, RSS feeds

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:

```bash
git clone https://github.com/YOUR_USERNAME/lolstonksrss.git
cd lolstonksrss
```

3. **Add upstream remote**:

```bash
git remote add upstream https://github.com/ORIGINAL_OWNER/lolstonksrss.git
```

## Development Setup

### 1. Install Dependencies

```bash
# Using UV (recommended) - creates venv automatically
uv sync --all-extras

# Or using pip with virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies with pip
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings (optional for development)
```

### 3. Verify Installation

```bash
# Run all tests with UV
uv run pytest

# Check coverage
uv run pytest --cov=src --cov-report=html

# Verify imports
uv run python -c "from src.models import Article; print('OK')"
```

### 4. Run the Application

```bash
# Start the FastAPI server with UV
uv run python -m uvicorn src.api.app:app --reload

# Or run directly
python -m uvicorn src.api.app:app --reload

# Access the RSS feed
# Open http://localhost:8000/feed in your browser
```

## Code Contributions

### Before You Start

1. **Check existing issues** - Someone might already be working on it
2. **Discuss major changes** - Open an issue first to discuss significant changes
3. **Review architecture** - Read `docs/` files to understand system design
4. **Read coding standards** - Follow the guidelines below

### Development Process

#### 1. Create a Branch

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `perf/` - Performance improvements
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

#### 2. Make Changes

- Write clear, self-documenting code
- Add comments for complex logic
- Follow existing code style
- Keep changes focused and atomic

#### 3. Write Tests

**Every code change must include tests:**

```bash
# Run tests frequently during development with UV
uv run pytest -v

# Run specific test file
uv run pytest tests/test_your_feature.py -v

# Skip slow integration tests during development
uv run pytest -m "not slow"
```

See [Testing Requirements](#testing-requirements) for details.

#### 4. Update Documentation

- Add docstrings to new functions/classes
- Update README.md if needed
- Add examples for new features
- Update relevant docs/ files

#### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message following Conventional Commits
git commit -m "feat(rss): add RSS item limit configuration"
```

**Conventional Commits Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Commit Types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style changes (formatting, etc)
- `refactor` - Code refactoring
- `perf` - Performance improvements
- `test` - Test additions or corrections
- `build` - Build system or dependency changes
- `ci` - CI/CD configuration changes
- `chore` - Other changes (maintenance)
- `revert` - Revert a previous commit

**Scopes** (optional):
- `api`, `rss`, `database`, `config`, `docker`, `ci`, `docs`, `tests`, `deployment`

**Subject Rules**:
- Use imperative, present tense: "add" not "added" nor "adds"
- Don't capitalize first letter
- No period (.) at the end
- Maximum 72 characters

**Examples**:
```bash
# Feature with scope
git commit -m "feat(rss): add configurable item limit

- Add max_items parameter to RSSGenerator
- Update configuration to support item limit
- Add validation for limit range (1-100)

Closes #123"

# Bug fix
git commit -m "fix(api): resolve database connection leak"

# Documentation
git commit -m "docs: update deployment guide for Windows Server"

# Breaking change
git commit -m "feat(api): redesign RSS endpoint structure

BREAKING CHANGE: RSS endpoint moved from /feed to /api/v2/feed
Migration guide in docs/migration/v2.md"
```

**Validation**: Commit messages are automatically validated by the `commit-msg` hook.

#### 6. Submit Pull Request

See [Pull Request Process](#pull-request-process) below.

## Coding Standards

### Python Style (PEP 8)

**We follow PEP 8** with some adjustments:

```bash
# Format code with Black (line length: 100)
uv run black src/ tests/

# Check formatting
uv run black --check src/ tests/

# Lint with Ruff
uv run ruff check src/ tests/

# Fix auto-fixable issues
uv run ruff check --fix src/ tests/
```

### Type Hints (Required)

**All functions must have type hints:**

```python
# Good
def get_articles(limit: int, source: str | None = None) -> list[Article]:
    """Fetch articles with optional filtering."""
    pass

# Bad - missing type hints
def get_articles(limit, source=None):
    pass
```

**Type check your code:**

```bash
uv run mypy src/
```

Configuration in `pyproject.toml`:
- `disallow_untyped_defs = true`
- `disallow_incomplete_defs = true`

### Docstrings (Google Style)

**All public functions/classes need docstrings:**

```python
def fetch_articles(source: str, limit: int = 50) -> list[Article]:
    """Fetch articles from the specified source.

    Args:
        source: Article source identifier (e.g., "lol-en-us")
        limit: Maximum number of articles to fetch (default: 50)

    Returns:
        List of Article objects ordered by publication date

    Raises:
        APIClientError: If the API request fails
        ValidationError: If article data is invalid

    Example:
        >>> articles = await fetch_articles("lol-en-us", limit=10)
        >>> print(len(articles))
        10
    """
    pass
```

### Async/Await Patterns

**Use async/await for I/O operations:**

```python
# Good - async database operations
async def save_article(article: Article) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(query, params)
        await db.commit()

# Bad - blocking I/O
def save_article(article: Article) -> None:
    with sqlite3.connect(db_path) as db:
        db.execute(query, params)
        db.commit()
```

### Error Handling

**Explicit error handling with custom exceptions:**

```python
# Good - specific exceptions
try:
    articles = await api_client.fetch_articles()
except APIClientError as e:
    logger.error(f"Failed to fetch articles: {e}")
    return []
except ValidationError as e:
    logger.error(f"Invalid article data: {e}")
    raise

# Bad - catching all exceptions
try:
    articles = await api_client.fetch_articles()
except Exception:
    return []
```

### Logging

**Use structured logging:**

```python
import logging

logger = logging.getLogger(__name__)

# Good
logger.info(f"Fetched {len(articles)} articles from {source}")
logger.error(f"API request failed: {error}", exc_info=True)

# Bad
print(f"Fetched {len(articles)} articles")
```

### Code Organization

**Keep functions small and focused:**

```python
# Good - single responsibility
async def fetch_articles(source: str) -> list[dict]:
    """Fetch raw article data from API."""
    pass

async def parse_articles(raw_data: list[dict]) -> list[Article]:
    """Parse raw data into Article objects."""
    pass

# Bad - doing too much
async def fetch_and_parse_and_save_articles(source: str) -> None:
    """Fetch, parse, and save articles."""
    # 100 lines of mixed concerns
    pass
```

## Testing Requirements

### Test Coverage Target: ≥90%

**Current coverage: 92.36%** - Let's maintain this!

```bash
# Run all tests with coverage using UV
uv run pytest --cov=src --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

### Unit Tests (Required)

**Every new function needs unit tests:**

```python
# tests/test_your_module.py
import pytest
from src.your_module import your_function

def test_your_function_success():
    """Test successful execution."""
    result = your_function(valid_input)
    assert result == expected_output

def test_your_function_validation_error():
    """Test validation error handling."""
    with pytest.raises(ValidationError):
        your_function(invalid_input)

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Integration Tests

**Test component interactions:**

```python
# tests/integration/test_feature_integration.py
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_article_fetch_and_save():
    """Test fetching and saving articles end-to-end."""
    # Fetch from API
    articles = await api_client.fetch_articles("lol-en-us")

    # Save to database
    await repository.save_many(articles)

    # Verify saved
    saved = await repository.get_latest(limit=len(articles))
    assert len(saved) == len(articles)
```

### Performance Tests

**Test performance for critical paths:**

```python
# tests/performance/test_performance.py
import time
import pytest

@pytest.mark.performance
@pytest.mark.asyncio
async def test_rss_generation_performance():
    """RSS generation should complete within 200ms."""
    start = time.time()
    feed = await generator.generate_feed(articles)
    duration = time.time() - start

    assert duration < 0.2  # 200ms
```

### RSS Validation Tests

**Validate RSS 2.0 compliance:**

```python
# tests/validation/test_rss_compliance.py
import feedparser
import pytest

@pytest.mark.validation
def test_rss_valid_xml(rss_xml: str):
    """Generated RSS must be valid XML."""
    parsed = feedparser.parse(rss_xml)
    assert parsed.bozo == 0  # No parsing errors
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit          # Fast, isolated unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.slow          # Tests making real API calls
@pytest.mark.e2e           # End-to-end workflow tests
@pytest.mark.performance   # Performance benchmarks
@pytest.mark.validation    # RSS validation tests
```

Run specific test categories:

```bash
pytest -m unit                    # Unit tests only
pytest -m "not slow"              # Skip slow tests
pytest -m "integration or e2e"    # Integration and E2E tests
```

### All Tests Must Pass

```bash
# This must succeed before submitting PR
uv run pytest

# Expected output:
# ====== 245 passed in 17.23s ======
```

## Documentation Requirements

### Update Relevant Documentation

When making changes, update:

1. **Code Docstrings** - Document all new functions/classes
2. **README.md** - Update if features/setup changes
3. **CLAUDE.md** - Update if development commands change
4. **docs/** files - Update architecture/deployment docs
5. **CHANGELOG.md** - Add entry for your change (if exists)

### Add Code Examples

**Show how to use new features:**

```markdown
## Using the New Feature

\```python
from src.new_module import new_function

# Example usage
result = new_function(param1, param2)
print(result)
\```
```

### Update API Reference

If you add/modify public APIs, document them:

```python
class RSSGenerator:
    """Generate RSS 2.0 feeds from articles.

    This generator creates valid RSS 2.0 XML feeds with support for:
    - Custom channel metadata
    - Article filtering and limiting
    - Automatic GUID generation
    - Publication date formatting

    Example:
        >>> generator = RSSGenerator(config)
        >>> feed = await generator.generate_feed(articles)
        >>> print(feed[:100])
        <?xml version="1.0" encoding="UTF-8"?>...
    """
```

## Pull Request Process

### PR Template

When creating a pull request, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Specific change 1
- Specific change 2

## Testing
- [ ] All existing tests pass
- [ ] Added new tests for changes
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed code
- [ ] Commented complex code
- [ ] Updated documentation
- [ ] No breaking changes (or documented)
- [ ] Tests added/updated
- [ ] All tests pass
```

### Code Review Checklist

Before submitting, verify:

- [ ] **Tests pass**: `uv run pytest` succeeds
- [ ] **Coverage maintained**: Coverage ≥90%
- [ ] **Type checking**: `uv run mypy src/` passes
- [ ] **Linting**: `uv run ruff check src/` passes
- [ ] **Formatting**: `uv run black --check src/` passes
- [ ] **Documentation updated**
- [ ] **Commits are clean** (squash if needed)
- [ ] **No secrets in code** (API keys, passwords)

### CI/CD Checks

Your PR must pass automated checks:

- **Tests**: All 151+ tests pass
- **Coverage**: Code coverage ≥90%
- **Type Checking**: No mypy errors
- **Linting**: No ruff violations
- **Formatting**: Black formatting compliant

### Merge Requirements

PRs are merged when:

1. ✅ All CI/CD checks pass
2. ✅ At least one approving review
3. ✅ No unresolved comments
4. ✅ Up to date with main branch
5. ✅ Clean commit history

## Issue Guidelines

### Bug Reports

Use this template for bug reports:

```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: Windows 10/11, Linux, macOS
- Python version: 3.10/3.11
- Docker version (if applicable):
- Installation method: pip, Docker

## Logs/Screenshots
Paste relevant logs or add screenshots

## Additional Context
Any other relevant information
```

### Feature Requests

Use this template for feature requests:

```markdown
## Feature Description
Clear description of the proposed feature

## Use Case
Why is this feature needed? What problem does it solve?

## Proposed Solution
How should this feature work?

## Alternatives Considered
What other approaches did you consider?

## Additional Context
Any other relevant information, mockups, examples
```

### Issue Labels

We use these labels:

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Documentation improvements
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `question` - Further information requested
- `wontfix` - This will not be worked on
- `duplicate` - This issue already exists
- `priority-high` - High priority
- `priority-low` - Low priority

### Response Expectations

- **Bug reports**: Response within 48 hours
- **Feature requests**: Discussion within 1 week
- **Questions**: Answer within 24-48 hours
- **Pull requests**: Review within 3-5 days

## Code Review

### What Reviewers Look For

When reviewing your PR, we check:

**Correctness**
- Does the code work as intended?
- Are edge cases handled?
- Is error handling appropriate?

**Testing**
- Are there sufficient tests?
- Do tests cover edge cases?
- Do all tests pass?

**Code Quality**
- Is code readable and maintainable?
- Are functions/classes well-designed?
- Is there unnecessary complexity?

**Style**
- Does it follow PEP 8?
- Are type hints present?
- Are docstrings complete?

**Documentation**
- Is documentation updated?
- Are changes explained?
- Are examples provided?

**Performance**
- Are there performance concerns?
- Is async/await used appropriately?
- Are there memory leaks?

**Security**
- Are there security vulnerabilities?
- Is user input validated?
- Are secrets properly handled?

### How to Respond to Feedback

**Be receptive to feedback:**

```markdown
# Good Response
Thanks for the review! You're right about the error handling.
I'll add a try-except block and update the tests.

# Bad Response
That's not a real issue. My code is fine.
```

**Ask for clarification if needed:**

```markdown
I'm not sure I understand your concern about the async implementation.
Could you provide an example of what you'd prefer?
```

**Address all comments:**
- Fix issues or explain why you disagree
- Mark conversations as resolved when fixed
- Update the PR with requested changes

### Approval Process

1. **Reviewer requests changes** - Address feedback and update PR
2. **Reviewer approves** - PR is ready to merge
3. **Maintainer merges** - Changes are merged to main branch

## Release Process

### Versioning (Semantic Versioning)

We follow [SemVer](https://semver.org/): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

Examples:
- `1.0.0` → `1.0.1` - Bug fix
- `1.0.0` → `1.1.0` - New feature
- `1.0.0` → `2.0.0` - Breaking change

### Changelog Updates

Maintain CHANGELOG.md with each release:

```markdown
## [1.2.0] - 2025-01-15

### Added
- RSS feed item limit configuration (#123)
- Performance metrics endpoint (#124)

### Fixed
- Database connection leak (#125)
- RSS XML escaping issue (#126)

### Changed
- Updated feedgen to 1.1.0 (#127)
```

### Release Notes

Each release includes:
- Version number
- Release date
- Summary of changes
- Breaking changes (if any)
- Migration guide (if needed)
- Contributors

## Community Guidelines

### Code of Conduct

**Be respectful and inclusive:**

- Use welcoming and inclusive language
- Respect differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

**Unacceptable behavior:**

- Harassment or discriminatory language
- Trolling or insulting comments
- Personal attacks
- Publishing others' private information
- Other unprofessional conduct

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **Pull Requests**: Code discussions
- **GitHub Discussions**: General questions, ideas

### Getting Help

**Need help contributing?**

1. Check existing documentation
2. Search closed issues for similar problems
3. Open a new issue with your question
4. Tag with `question` label

**Common questions:**

- Setup issues → Check QUICKSTART.md
- Testing help → Check docs/TESTING_GUIDE.md
- Docker issues → Check docs/DOCKER.md
- Deployment → Check docs/WINDOWS_DEPLOYMENT.md

## Recognition

### Contributors

All contributors are recognized in:

- GitHub contributors page
- CONTRIBUTORS.md file (if created)
- Release notes (for significant contributions)

### Acknowledgments

Special recognition for:

- **First-time contributors**
- **Major features** implemented
- **Bug fixes** for critical issues
- **Documentation** improvements
- **Long-term** maintainers

**We appreciate every contribution**, no matter how small!

## License

By contributing to LoL Stonks RSS, you agree that your contributions will be licensed under the same license as the project (see LICENSE file, if exists).

### Contributor Agreement

By submitting a pull request, you represent that:

- You have the right to submit the code
- Your contribution is your original work
- You grant the project a perpetual, worldwide, non-exclusive, royalty-free license to use your contribution

---

## Quick Reference

### Development Commands

```bash
# Setup
uv sync --all-extras                      # Install all dependencies

# Testing
uv run pytest                             # All tests
uv run pytest -m "not slow"               # Skip slow tests
uv run pytest --cov=src --cov-report=html # With coverage

# Code Quality
uv run black src/ tests/                  # Format
uv run mypy src/                          # Type check
uv run ruff check src/ tests/             # Lint

# Run Application
uv run python -m uvicorn src.api.app:app --reload
```

### Commit Message Format

```
type: brief description

Detailed explanation (optional)

Types: feat, fix, docs, test, refactor, perf, chore
```

### Branch Naming

```
feature/description
fix/description
docs/description
```

### Need Help?

- Read the docs in `docs/`
- Check QUICKSTART.md
- Open an issue with `question` label

---

**Thank you for contributing to LoL Stonks RSS!**

Your efforts help the League of Legends community stay informed and up-to-date.

Happy coding! 🎮
