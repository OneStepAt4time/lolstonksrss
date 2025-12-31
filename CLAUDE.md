# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ CRITICAL: GITFLOW IS MANDATORY

**NEVER PUSH DIRECTLY TO MASTER/MAIN BRANCH**

This repository follows strict GitHub Flow. **ALL code changes MUST**:

1. ✅ **Create a feature branch** (feature/, fix/, docs/, etc.)
2. ✅ **Make changes on the branch**
3. ✅ **Commit following Conventional Commits**
4. ✅ **Push the feature branch** (NOT master)
5. ✅ **Create a Pull Request**
6. ✅ **Wait for CI/CD checks to pass**
7. ✅ **Get approval from maintainer**
8. ✅ **Merge via GitHub PR interface**

**VIOLATION OF GITFLOW IS UNACCEPTABLE**

### Pre-push Hook Protection

The `.githooks/pre-push` hook **BLOCKS** direct pushes to master/main:
- Hook will **FAIL** if pushing to master/main
- Only bypass with `--no-verify` is for **emergency hotfixes**
- **NEVER** use `--no-verify` for regular development

### Consequences of Bypassing Gitflow

Using `git push --no-verify` to bypass hooks:
- ❌ Breaks SDLC compliance
- ❌ Skips mandatory CI/CD checks
- ❌ Bypasses code review process
- ❌ Creates untracked technical debt
- ❌ Violates team agreements

**DO NOT bypass hooks without explicit user approval**

## Project Overview

This is a Python application that generates an RSS feed for League of Legends news. The application is containerized with Docker and designed for deployment on a Windows server.

## Project Requirements

- **Language**: Python
- **Containerization**: Docker
- **Target Deployment**: Windows server
- **Functionality**: Fetch League of Legends news and generate an RSS feed

## Development Commands

### Docker Commands

```bash
# Build the Docker image
docker build -t lolstonksrss .

# Run the container
docker run -p 8000:8000 lolstonksrss

# Run with docker-compose (if available)
docker-compose up

# Stop containers
docker-compose down
```

### Python Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application locally
python main.py

# Run tests (if test framework is added)
pytest

# Run single test
pytest tests/test_specific.py
```

## Architecture Notes

### RSS Feed Generation
- The application fetches League of Legends news from official sources or APIs
- News items are formatted into RSS 2.0 compatible XML format
- The RSS feed should be served via HTTP endpoint

### Docker Deployment
- Application runs as a containerized service
- Exposes HTTP port for RSS feed access
- Configuration should be handled via environment variables for flexibility on Windows deployment

### Data Flow
1. News fetching component retrieves latest LoL news
2. Parser/formatter converts news to RSS format
3. Web server exposes RSS feed at an endpoint
4. Feed updates periodically to show new content

## Windows Deployment Considerations

- Docker Desktop for Windows should be used on the target server
- Volume mounts may need Windows-style paths
- Port mappings should avoid conflicts with existing services
- Consider using environment variables for configuration rather than hardcoded paths

---

## 📁 Temporary File Management

### The `tmp/` Directory

Use the `tmp/` directory for **temporary AI-generated files** that should NOT be committed to the repository. This directory is excluded from git via `.gitignore`.

#### What to Put in `tmp/`

**DO put in `tmp/`:**
- Implementation plans and design notes
- Research notes and exploratory analysis
- Debug logs and troubleshooting notes
- Draft code snippets or experiments
- Temporary test outputs
- Agent coordination notes
- Any file that is part of your working process, not the final deliverable

**DO NOT put in `tmp/`:**
- Production code (should go in `src/`)
- Tests (should go in `tests/`)
- Documentation (should go in `docs/`)
- Configuration files (should go in project root)

#### Examples of `tmp/` Usage

```bash
tmp/
├── plan-oauth-implementation.md       # Temporary implementation plan
├── research-api-designs.md            # Research notes during exploration
├── debug-cache-issue.md               # Debugging notes
├── draft-rate-limiter.py              # Draft code being developed
└── agent-task-notes.md                # Notes during agent coordination
```

#### Workflow: From `tmp/` to Repository

1. **Create plan/research in `tmp/`** - Work through your implementation plan
2. **Implement based on plan** - Write actual code/tests in proper locations
3. **Move relevant documentation** - If `tmp/` content should be preserved, move to `docs/`
4. **Leave `tmp/` uncommitted** - The working files stay in `tmp/`, never committed

```bash
# Example workflow
echo "# Plan: OAuth2 Implementation" > tmp/plan-oauth.md
# Edit plan, add details...
# Implement the feature in src/
# Move final docs if needed: mv tmp/plan-oauth.md docs/oauth-plan.md
# Or just leave in tmp/ - it won't be committed anyway
```

#### Why This Matters

- **Clean repository history**: Only final, reviewed content is committed
- **Safe experimentation**: `tmp/` is a sandbox for ideas
- **Reduced noise**: No endless drafts in commit history
- **Better collaboration**: Team sees polished deliverables, not working drafts

#### Special Case: Plan Mode

When Claude Code enters **plan mode**, it automatically saves plans to a special location (managed by the system). You can also manually save working plans to `tmp/` for reference during implementation.

#### Cleanup

The `tmp/` directory can be cleaned periodically:
```bash
# Occasionally clean old tmp files (safe, they're not in git)
rm -rf tmp/*.md
```

---

## 📋 GITFLOW: Detailed Workflow (MANDATORY)

### Step-by-Step Process

#### 1. Before Starting ANY Work

```bash
# Ensure you're on master and it's up to date
git checkout master
git pull origin master

# Verify no uncommitted changes
git status  # Should show "working tree clean"
```

#### 2. Create Feature Branch

**Branch Naming Convention (STRICT)**:
- `feature/description` - New features
- `fix/bug-description` - Bug fixes
- `docs/topic` - Documentation changes
- `refactor/component` - Code refactoring
- `perf/optimization` - Performance improvements
- `test/component` - Test additions

**Examples**:
```bash
# Good branch names
git checkout -b feature/github-pages-auto-sync
git checkout -b fix/rss-xml-escaping
git checkout -b docs/deployment-guide

# Bad branch names (DON'T USE)
git checkout -b new-feature        # Too vague
git checkout -b fix                # No description
git checkout -b my-changes         # Not descriptive
```

#### 3. Make Changes and Commit

**Conventional Commits Format (REQUIRED)**:
```
type(scope): subject

body (optional)

footer (optional)
```

**Types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting
- `refactor` - Code refactoring
- `perf` - Performance
- `test` - Tests
- `build` - Build system
- `ci` - CI/CD changes
- `chore` - Maintenance

**Scopes** (optional but recommended):
- `api`, `rss`, `database`, `config`, `docker`, `ci`, `docs`, `tests`

**Examples**:
```bash
# Feature
git commit -m "feat(api): add GitHub Pages auto-sync integration"

# Bug fix
git commit -m "fix(docker): use env_file instead of hardcoded secrets"

# Documentation
git commit -m "docs(claude): add mandatory gitflow instructions"

# Breaking change
git commit -m "feat(api): redesign RSS endpoint structure

BREAKING CHANGE: RSS endpoint moved from /feed to /api/v2/feed"
```

#### 4. Push Feature Branch

```bash
# Push YOUR feature branch (NOT master!)
git push origin feature/your-feature-name

# If first push on branch
git push -u origin feature/your-feature-name
```

**⚠️ NEVER** do:
```bash
git push origin master        # ❌ FORBIDDEN
git push origin main          # ❌ FORBIDDEN
git push --no-verify          # ❌ ONLY for emergencies with user approval
```

#### 5. Create Pull Request

**Using GitHub CLI** (recommended):
```bash
gh pr create --title "feat: Add GitHub Pages auto-sync" --body "Description..."
```

**Using GitHub Web**:
1. Go to: https://github.com/OneStepAt4time/lolstonksrss/pulls
2. Click "New pull request"
3. Select your feature branch
4. Fill in PR template
5. Create PR

**PR Must Include**:
- Clear description of changes
- List of specific changes made
- Testing checklist completed
- Documentation updates noted

#### 6. Wait for CI/CD Checks

**Mandatory Checks** (must ALL pass):
- ✅ Unit tests (151+ tests)
- ✅ Integration tests
- ✅ Code coverage ≥90%
- ✅ Black formatting
- ✅ Ruff linting
- ✅ Mypy type checking
- ✅ Docker build
- ✅ Security scanning

**If checks fail**:
1. Review failure logs
2. Fix issues locally
3. Commit fixes
4. Push to same branch (PR updates automatically)

#### 7. Code Review Process

1. **Reviewer** examines code
2. **Feedback** provided via PR comments
3. **Author** addresses feedback
4. **Author** pushes fixes to same branch
5. **Reviewer** approves when satisfied

#### 8. Merge (Via GitHub Interface ONLY)

**NEVER** merge locally:
```bash
# ❌ DON'T DO THIS
git checkout master
git merge feature/your-feature
git push
```

**✅ DO THIS**:
- Use GitHub "Squash and merge" or "Merge pull request" button
- Delete branch after merge (automatic option)

---

## 🚨 Emergency Hotfix Procedure

**ONLY for production-breaking bugs requiring immediate fix**:

1. Ask user for explicit approval: "Emergency hotfix needed?"
2. If approved:
   ```bash
   git checkout master
   git pull origin master
   git checkout -b hotfix/critical-bug-description
   # Make minimal fix
   git commit -m "fix: critical bug description"
   git push origin hotfix/critical-bug-description
   # Create PR immediately
   gh pr create --title "HOTFIX: Critical bug" --body "..."
   ```
3. Wait for fast-track review
4. Merge via PR

**NEVER** push hotfixes directly to master, even in emergencies.

---

## 🤖 Agent-Specific Instructions

When delegating work to agents (python-pro, devops-engineer, etc.):

### Before Delegation

1. ✅ Verify you're on a feature branch (NOT master)
2. ✅ If on master, create feature branch FIRST
3. ✅ Inform agents they're working on feature branch

### After Agent Completes Work

1. ✅ Review agent's changes
2. ✅ Stage and commit changes (Conventional Commits)
3. ✅ Push to feature branch
4. ✅ Create PR
5. ✅ NEVER use `--no-verify`

### Agent Delegation Template

```
I'm delegating to [agent-name] to [task description].

IMPORTANT: We are on feature branch [branch-name].
ALL changes will be committed to this feature branch.
DO NOT mention master branch or pushing to master.
```

---

## 📊 SDLC Compliance Checklist

Before ANY code push, verify:

- [ ] Working on feature branch (NOT master)
- [ ] Changes committed with Conventional Commits format
- [ ] Pre-commit hooks passed (Black, Ruff, Mypy)
- [ ] All tests pass locally (`uv run pytest`)
- [ ] Coverage ≥90%
- [ ] Documentation updated
- [ ] Ready to push feature branch (NOT master)
- [ ] PR will be created after push

---

## ⛔ Violations and Remediation

### If You Accidentally Push to Master

**Immediate Actions**:
1. **DO NOT PANIC**
2. Inform user immediately
3. Options:
   - **Revert commit**: `git revert HEAD && git push`
   - **Force reset** (requires coordination): `git reset --hard HEAD~1 && git push --force`
   - **Leave and document**: Add to technical debt log

### If You Use `--no-verify` Inappropriately

1. Acknowledge the violation
2. Explain to user what happened
3. Create follow-up PR to fix any issues
4. Document in incident log

---

## 📚 Required Reading

- **CONTRIBUTING.md** - Complete contribution guidelines (lines 150-284)
- **Pre-push hook** - `.githooks/pre-push` (lines 32-37)
- **Conventional Commits** - https://www.conventionalcommits.org/

---

## 🎓 Summary for Claude

**ABSOLUTE RULES** (NEVER break these):

1. **NEVER** push to master/main directly
2. **NEVER** use `git push --no-verify` without explicit user approval
3. **ALWAYS** create feature branch before starting work
4. **ALWAYS** follow Conventional Commits format
5. **ALWAYS** create PR for code changes
6. **ALWAYS** wait for CI/CD checks before merging
7. **ALWAYS** ask user if uncertain about gitflow

**Default Response** when asked to commit/push:
```
I've prepared the changes. Following our gitflow:
1. I'll create a feature branch
2. Commit changes with Conventional Commits format
3. Push the feature branch
4. Create a Pull Request

Shall I proceed?
```

---

**Remember**: Gitflow compliance is NOT optional. It's a core requirement of professional SDLC.
