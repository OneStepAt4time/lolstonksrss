# GitFlow Workflow Guide

This document describes the GitFlow branching strategy used in the LoL Stonks RSS project.

## Table of Contents

- [Overview](#overview)
- [Branch Structure](#branch-structure)
- [Branch Naming Conventions](#branch-naming-conventions)
- [Workflow Examples](#workflow-examples)
- [Release Process](#release-process)
- [Hotfix Process](#hotfix-process)
- [Quality Gates](#quality-gates)
- [Best Practices](#best-practices)

## Overview

GitFlow is a branching model that defines a strict branching structure designed around project releases. It provides a robust framework for managing larger projects and enables parallel development.

### Why GitFlow?

- **Organized development**: Clear separation between development and production code
- **Parallel development**: Multiple features can be developed simultaneously
- **Release management**: Structured release preparation and deployment
- **Hotfix support**: Quick fixes to production without disrupting development
- **Quality assurance**: Quality gates ensure only tested code reaches production

## Branch Structure

### Main Branches

These branches exist throughout the project lifecycle:

#### `main` (or `master`)
- **Purpose**: Production-ready code
- **Protection**: Fully protected
- **Deployment**: Automatically deploys to production
- **Source**: Merges from `release/*` and `hotfix/*` branches only
- **Never commit directly**: Always use pull requests

#### `develop`
- **Purpose**: Integration branch for features
- **Protection**: Protected with required reviews
- **Deployment**: Automatically deploys to staging/development environment
- **Source**: Merges from `feature/*` branches
- **Base for**: New feature branches

### Supporting Branches

These branches are temporary and deleted after merging:

#### `feature/*`
- **Purpose**: Develop new features
- **Lifetime**: Until feature is complete and merged
- **Base**: Created from `develop`
- **Merge to**: `develop` via pull request
- **Examples**:
  - `feature/rss-item-limit`
  - `feature/article-caching`
  - `feature/api-rate-limiting`

#### `release/*`
- **Purpose**: Prepare for production release
- **Lifetime**: Until release is deployed and merged
- **Base**: Created from `develop`
- **Merge to**: `main` and back to `develop`
- **Examples**:
  - `release/1.2.0`
  - `release/2.0.0-beta`

#### `hotfix/*`
- **Purpose**: Quick fixes to production
- **Lifetime**: Until fix is deployed and merged
- **Base**: Created from `main`
- **Merge to**: `main` and `develop`
- **Examples**:
  - `hotfix/1.1.1-critical-bug`
  - `hotfix/1.2.1-security-fix`

#### `docs`
- **Purpose**: Documentation-only changes
- **Lifetime**: Permanent branch
- **Base**: Created from `main`
- **Merge to**: `main` or `develop` depending on documentation type
- **Use**: For documentation that doesn't require full release cycle

## Branch Naming Conventions

### Format

```
<type>/<description>
```

### Types

- `feature/` - New features or enhancements
- `release/` - Release preparation
- `hotfix/` - Production bug fixes
- `bugfix/` - Non-critical bug fixes (use `feature/` prefix)
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test improvements
- `perf/` - Performance improvements

### Description Guidelines

- Use lowercase with hyphens
- Be descriptive but concise
- Include issue number if applicable
- Maximum 50 characters

### Examples

Good:
```
feature/add-rss-pagination
feature/123-api-authentication
release/2.1.0
hotfix/1.0.1-database-leak
docs/update-deployment-guide
```

Bad:
```
my-feature
feature/NewFeature
fix-bug
temp
```

## Workflow Examples

### Feature Development Workflow

Complete workflow for developing a new feature:

#### 1. Create Feature Branch

```bash
# Ensure develop is up to date
git checkout develop
git pull origin develop

# Create and checkout feature branch
git checkout -b feature/rss-item-limit

# Push branch to remote
git push -u origin feature/rss-item-limit
```

#### 2. Develop Feature

```bash
# Make changes
# Edit files...

# Stage changes
git add .

# Commit with conventional commit message
git commit -m "feat(rss): add configurable RSS item limit

- Add max_items parameter to RSSGenerator
- Update configuration to support item limit
- Add validation for limit range (1-100)

Closes #123"

# Push changes
git push origin feature/rss-item-limit
```

#### 3. Keep Branch Updated

```bash
# Regularly sync with develop
git checkout develop
git pull origin develop
git checkout feature/rss-item-limit
git merge develop

# Or use rebase (if no conflicts expected)
git checkout feature/rss-item-limit
git rebase develop
```

#### 4. Create Pull Request

```bash
# Push final changes
git push origin feature/rss-item-limit

# Create PR via GitHub CLI (optional)
gh pr create --base develop --head feature/rss-item-limit \
  --title "feat(rss): add configurable RSS item limit" \
  --body "Closes #123

## Summary
- Adds configurable item limit to RSS feed
- Validates limit range (1-100)
- Updates documentation

## Testing
- All unit tests pass
- Added integration tests
- Manual testing completed"
```

#### 5. After PR Merge

```bash
# Delete local branch
git checkout develop
git branch -d feature/rss-item-limit

# Delete remote branch (if not auto-deleted)
git push origin --delete feature/rss-item-limit
```

### Starting a New Feature

```bash
# Update develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature-name

# Make initial commit
git commit --allow-empty -m "feat: initialize feature branch"

# Push to remote
git push -u origin feature/your-feature-name
```

### Working on Existing Feature

```bash
# Checkout feature branch
git checkout feature/existing-feature

# Update from remote
git pull origin feature/existing-feature

# Update from develop
git fetch origin develop
git merge origin/develop

# Or rebase onto develop
git rebase origin/develop
```

## Release Process

### Creating a Release

#### 1. Create Release Branch

```bash
# Ensure develop is ready for release
git checkout develop
git pull origin develop

# Create release branch
git checkout -b release/1.2.0

# Push to remote
git push -u origin release/1.2.0
```

#### 2. Prepare Release

```bash
# Update version in pyproject.toml
# Update CHANGELOG.md
# Update documentation

# Commit release preparation
git add .
git commit -m "chore(release): prepare version 1.2.0

- Update version to 1.2.0
- Update CHANGELOG.md
- Update documentation"

# Push changes
git push origin release/1.2.0
```

#### 3. Release Testing

- Run full test suite
- Perform integration testing
- Test in staging environment
- Verify documentation
- Security scan
- Performance testing

#### 4. Merge to Main

```bash
# Create PR to main
gh pr create --base main --head release/1.2.0 \
  --title "Release v1.2.0" \
  --body "Release notes...

## Changes
- Feature 1
- Feature 2
- Bug fix 1

## Testing
- All tests pass
- Staging deployment successful
- Documentation updated"

# After PR approval and merge, tag the release
git checkout main
git pull origin main
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

#### 5. Merge Back to Develop

```bash
# Merge release changes back to develop
git checkout develop
git pull origin develop
git merge release/1.2.0
git push origin develop

# Delete release branch
git branch -d release/1.2.0
git push origin --delete release/1.2.0
```

### Release Checklist

Before creating a release:

- [ ] All planned features merged to develop
- [ ] All tests passing (100%)
- [ ] Code coverage >= 90%
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version numbers updated
- [ ] No known critical bugs
- [ ] Security scan passed
- [ ] Performance benchmarks met
- [ ] Staging deployment successful

## Hotfix Process

For critical production bugs that need immediate attention:

### 1. Create Hotfix Branch

```bash
# Create from main
git checkout main
git pull origin main

# Create hotfix branch with version number
git checkout -b hotfix/1.1.1-critical-bug

# Push to remote
git push -u origin hotfix/1.1.1-critical-bug
```

### 2. Fix the Issue

```bash
# Make the fix
# Edit files...

# Commit the fix
git add .
git commit -m "fix(api): resolve critical database connection leak

- Fix connection pool not being released
- Add proper connection cleanup
- Add regression test

Fixes #456"

# Push changes
git push origin hotfix/1.1.1-critical-bug
```

### 3. Test Hotfix

- Run full test suite
- Test the specific fix
- Verify no side effects
- Test in staging environment

### 4. Merge to Main

```bash
# Create PR to main
gh pr create --base main --head hotfix/1.1.1-critical-bug \
  --title "Hotfix v1.1.1: Fix critical database leak" \
  --body "Critical hotfix for production issue

## Issue
Database connections not being released

## Fix
- Proper connection cleanup
- Added regression test

## Testing
- All tests pass
- Tested in staging
- Verified fix"

# After merge, tag the hotfix
git checkout main
git pull origin main
git tag -a v1.1.1 -m "Hotfix version 1.1.1"
git push origin v1.1.1
```

### 5. Merge to Develop

```bash
# Merge hotfix to develop
git checkout develop
git pull origin develop
git merge hotfix/1.1.1-critical-bug
git push origin develop

# Delete hotfix branch
git branch -d hotfix/1.1.1-critical-bug
git push origin --delete hotfix/1.1.1-critical-bug
```

### Hotfix Checklist

- [ ] Issue identified and verified
- [ ] Hotfix branch created from main
- [ ] Fix implemented and tested
- [ ] Regression test added
- [ ] All tests pass
- [ ] PR reviewed and approved
- [ ] Merged to main
- [ ] Tagged with new version
- [ ] Deployed to production
- [ ] Merged back to develop
- [ ] Issue closed

## Parallel Development with Worktrees

### Overview

Git worktrees allow multiple branches to be checked out simultaneously in different directories. This enables true parallel development without context switching, making it ideal for:

- Developing multiple features simultaneously (7+ at once)
- Emergency hotfixes while feature work is in progress
- Code review without switching branches
- Testing multiple branches at the same time
- Isolated testing environments per feature

### Worktree Architecture

```
lolstonksrss/              (main repo - port 8000)
├── .venv/                  (shared venv)
├── data/articles.db        (main DB)
└── src/
lolstonksrss-feature-a/     (worktree 1 - port 8001)
├── .venv → ../lolstonksrss/.venv  (symlink)
├── data/articles-feature-a.db      (isolated DB)
└── src/
lolstonksrss-feature-b/     (worktree 2 - port 8002)
├── .venv → ../lolstonksrss/.venv  (symlink)
├── data/articles-feature-b.db      (isolated DB)
└── src/
```

### Key Benefits

1. **No Context Switching**: Each branch stays open in its own directory
2. **Isolated Databases**: Each worktree uses its own SQLite database file
3. **Different Ports**: Each worktree runs on a different port (8001-8999)
4. **Shared Venv**: Symlink to main venv saves disk space and installation time
5. **True Parallelism**: Multiple agents can work simultaneously without conflicts

### Creating Worktrees for Parallel Development

#### Manual Creation

```bash
# Single worktree
git worktree add ../lolstonksrss-feature-x feature/x

# Multiple worktrees
for i in {1..7}; do
    git worktree add ../lolstonksrss-agent-$i -b feature/agent-$i-task
done
```

#### Using the Worktree Manager CLI

```bash
# Create single worktree
uv run python scripts/worktree-manager.py create feature/oauth2

# Create 7 worktrees for parallel agent development
uv run python scripts/worktree-manager.py create-multi --count 7

# List all worktrees
uv run python scripts/worktree-manager.py list

# Cleanup specific worktree
uv run python scripts/worktree-manager.py cleanup feature/oauth2

# Cleanup all worktrees
uv run python scripts/worktree-manager.py cleanup-all

# Show system status
uv run python scripts/worktree-manager.py status
```

### Parallel Feature Development Workflow

#### Example: 7 Features in Parallel

```bash
# 1. Create worktrees
cd D:\lolstonksrss
uv run python scripts/worktree-manager.py create-multi --count 7

# Output:
# ✓ Created 7 worktrees successfully!
#   • feature/agent-1-task: ../lolstonksrss-feature-agent-1-task (port 8001)
#   • feature/agent-2-task: ../lolstonksrss-feature-agent-2-task (port 8002)
#   • feature/agent-3-task: ../lolstonksrss-feature-agent-3-task (port 8003)
#   • feature/agent-4-task: ../lolstonksrss-feature-agent-4-task (port 8004)
#   • feature/agent-5-task: ../lolstonksrss-feature-agent-5-task (port 8005)
#   • feature/agent-6-task: ../lolstonksrss-feature-agent-6-task (port 8006)
#   • feature/agent-7-task: ../lolstonksrss-feature-agent-7-task (port 8007)

# 2. Work in parallel - each worktree is isolated
cd ../lolstonksrss-feature-agent-1-task
# Feature 1 development (uses articles-feature-agent-1-task.db, port 8001)

cd ../lolstonksrss-feature-agent-2-task
# Feature 2 development (uses articles-feature-agent-2-task.db, port 8002)

# ... and so on for all 7 features

# 3. Each worktree creates its own PR
gh pr create --base develop --head feature/agent-1-task --title "feat: implement agent 1 task"

# 4. After PR merge, cleanup
cd D:\lolstonksrss
uv run python scripts/worktree-manager.py cleanup-all
```

### Emergency Hotfix with Worktrees

When a critical bug appears while you're working on a feature:

```bash
# Main worktree has uncommitted feature work
# (no need to stash or commit)

# Create separate worktree for hotfix
git worktree add ../lolstonksrss-hotfix -b hotfix/critical-bug

# Fix the bug in isolated environment
cd ../lolstonksrss-hotfix
# Make fix, test, commit, push, create PR

# Merge hotfix PR
# Continue feature work in main worktree - context intact!
cd ../lolstonksrss

# Cleanup hotfix worktree
git worktree remove ../lolstonksrss-hotfix
```

### Worktree Management Best Practices

#### Naming Conventions

```
../lolstonksrss-feature-description     (feature branches)
../lolstonksrss-fix-bug-description     (bug fixes)
../lolstonksrss-hotfix-urgent-fix        (hotfixes)
../lolstonksrss-review-pr-123            (PR reviews)
../lolstonksrss-experiment-new-arch     (experiments)
```

#### Port Allocation

The WorktreeManager automatically allocates ports from the 8001-8999 range:

- Port 8000: Main repository
- Ports 8001-8999: Worktrees (99 possible worktrees)
- Registry stored in: `data/worktree-ports.json`

#### Database Isolation

Each worktree uses an isolated database:

```
Main repo:      data/articles.db
Feature branch: data/articles-feature-description.db
Hotfix:         data/articles-hotfix-urgent-fix.db
```

#### Virtual Environment Sharing

Worktrees automatically symlink to the main venv:

```bash
# Automatically created by WorktreeManager
lolstonksrss-feature-x/.venv → ../lolstonksrss/.venv
```

### CI/CD Integration

The `.github/workflows/parallel-development.yml` workflow tests parallel worktree functionality:

```bash
# Manual trigger
gh workflow run parallel-development.yml -f branch_count=7

# Tests:
# - Creates 7 worktrees
# - Runs tests in each worktree
# - Verifies database isolation
# - Cleans up worktrees
```

### Worktree Commands Reference

```bash
# List worktrees
git worktree list

# Create worktree (new branch)
git worktree add ../path -b feature/name

# Create worktree (existing branch)
git worktree add ../path existing-branch

# Remove worktree (clean)
git worktree remove ../path

# Remove worktree (force, discards changes)
git worktree remove --force ../path

# Move/rename worktree
git worktree move ../old-path ../new-path

# Prune stale metadata
git worktree prune

# Lock/unlock (for network drives)
git worktree lock ../path
git worktree unlock ../path
```

### Troubleshooting Worktrees

#### Problem: Worktree with uncommitted changes

```bash
# Solution 1: Commit changes
cd ../worktree-path
git add .
git commit -m "WIP: save work"

# Solution 2: Force remove (discards changes)
git worktree remove --force ../worktree-path
```

#### Problem: Port already allocated

```bash
# Solution: Release port and re-allocate
uv run python scripts/worktree-manager.py release feature/x
uv run python scripts/worktree-manager.py allocate feature/x
```

#### Problem: Venv symlink broken

```bash
# Solution: Recreate symlink
powershell.exe -ExecutionPolicy Bypass -File scripts/setup-worktree-venv.ps1 ../worktree-path
```

#### Problem: Worktree metadata corrupted

```bash
# Solution: Prune and recreate
git worktree prune
git worktree list
# Remove corrupted worktrees if needed
```

### Worktree Cleanup Strategy

After features are merged:

```bash
# 1. Checkout main or develop
git checkout develop

# 2. List worktrees
uv run python scripts/worktree-manager.py list

# 3. Remove merged worktrees
for wt in $(git worktree list | grep -v "lolstonksrss$" | awk '{print $1}'); do
    git worktree remove "$wt"
done

# 4. Prune metadata
git worktree prune

# 5. Verify cleanup
git worktree list
```

## Quality Gates

All code must pass these quality gates before merging:

### Pre-commit Checks

Automatically run before each commit:

- Code formatting (Black)
- Linting (Ruff)
- Type checking (mypy)
- Unit tests
- No debugging code
- No secrets in code

### Pull Request Checks

Required for PR approval:

- [ ] All tests pass (100%)
- [ ] Code coverage >= 90%
- [ ] No linting errors
- [ ] No type errors
- [ ] Security scan passed
- [ ] Docker build successful
- [ ] Documentation updated
- [ ] At least 1 approving review
- [ ] No unresolved comments
- [ ] Branch up to date with base

### Pre-push Checks

Run before pushing to remote:

- Full test suite passes
- Test coverage >= 90%
- All linting checks pass
- Type checking passes
- No uncommitted changes

### Release Checks

Required before production release:

- [ ] All quality gates passed
- [ ] Staging deployment successful
- [ ] Performance benchmarks met
- [ ] Security audit passed
- [ ] Documentation complete
- [ ] CHANGELOG updated
- [ ] Version tagged
- [ ] Release notes created

## Best Practices

### Do's

- **Always branch from the correct base**:
  - Features from `develop`
  - Releases from `develop`
  - Hotfixes from `main`

- **Keep branches up to date**:
  - Regularly merge/rebase from base branch
  - Resolve conflicts early

- **Write descriptive commit messages**:
  - Follow conventional commits
  - Explain why, not just what

- **Small, focused PRs**:
  - One feature per PR
  - Easier to review
  - Faster to merge

- **Test thoroughly**:
  - Write tests for new code
  - Run full test suite
  - Test in staging

- **Review carefully**:
  - Review your own code first
  - Address all PR comments
  - Be respectful and constructive

- **Clean up after merge**:
  - Delete merged branches
  - Update local repository

### Don'ts

- **Never commit directly to main or develop**
  - Always use pull requests
  - Ensure code review

- **Don't merge without passing checks**
  - Wait for CI/CD to pass
  - Fix failing tests

- **Don't create long-lived feature branches**
  - Merge frequently
  - Break large features into smaller PRs

- **Don't bypass quality gates**
  - No `--no-verify` pushes
  - No skipping tests

- **Don't mix concerns**
  - One feature per branch
  - Separate refactoring from features

- **Don't leave branches unmerged**
  - Finish what you start
  - Keep PRs moving

## Branch Protection Rules

### Main Branch

- Require pull request reviews (1+ approvals)
- Require status checks to pass:
  - CI tests
  - Linting
  - Type checking
  - Security scan
  - Docker build
- Require branches to be up to date
- No force pushes
- No deletions
- Require linear history
- Require signed commits (optional)

### Develop Branch

- Require pull request reviews (1+ approval)
- Require status checks to pass:
  - CI tests
  - Linting
  - Type checking
- Allow force pushes for maintainers only
- No deletions

### Docs Branch

- Require pull request reviews (optional)
- Require doc build to pass
- Allow fast-forward merges only

## Semantic Versioning

We follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

### Version Format

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

### Version Increments

- **MAJOR** (1.0.0 -> 2.0.0): Breaking changes
  - API changes
  - Removed features
  - Incompatible changes

- **MINOR** (1.0.0 -> 1.1.0): New features
  - New functionality
  - Backwards compatible
  - Deprecations

- **PATCH** (1.0.0 -> 1.0.1): Bug fixes
  - Bug fixes
  - Security patches
  - Backwards compatible

### Pre-release Versions

- `1.2.0-alpha.1` - Alpha release
- `1.2.0-beta.1` - Beta release
- `1.2.0-rc.1` - Release candidate

### Examples

- `1.0.0` - Initial release
- `1.0.1` - Bug fix
- `1.1.0` - New feature
- `2.0.0` - Breaking change
- `2.1.0-beta.1` - Beta release

## GitFlow Diagram

```
main        ─────●─────────────●─────────────●──────── (v1.0.0, v1.1.0, v2.0.0)
             │     │             │             │
             │     │             │             └─ merge release/2.0.0
             │     │             └─────────────── merge hotfix/1.0.1
             │     └───────────────────────────── merge release/1.0.0
             │
develop     ─●─────●─────●─────●─────●─────●─────●──── (staging)
             │      │     │     │     │     │     │
             │      │     │     │     │     │     └─ merge feature/c
             │      │     │     │     │     └─────── merge feature/b
             │      │     │     │     └─────────────── merge feature/a
             │      │     │     └─────────────────────── create release/1.1.0
             │      │     └───────────────────────────── merge hotfix/1.0.1
             │      └─────────────────────────────────── create release/1.0.0
             │
feature/a   ─────●─────●─────●────────────────────────
                      commits
feature/b   ───────────────────●─────●───────────────
                                  commits
release/1.0.0 ─●─────●─────●────────────────────────
                  testing & fixes
hotfix/1.0.1  ───────────●─────●──────────────────────
                        fix commits
```

## Summary

GitFlow provides structure and organization for the development process:

1. **Develop features** in `feature/*` branches from `develop`
2. **Create releases** in `release/*` branches from `develop`
3. **Deploy to production** by merging to `main`
4. **Fix production issues** in `hotfix/*` branches from `main`
5. **Maintain quality** with automated checks and reviews
6. **Track versions** with semantic versioning and tags

Follow this workflow consistently to maintain a clean, organized, and professional codebase.

---

For questions or suggestions about the GitFlow process, please open an issue or discussion.
