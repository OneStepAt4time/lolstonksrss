# Agent Gitflow Guide

**MANDATORY READING for all AI agents working on this repository**

## 🎯 Mission Critical Rules

When you (as an AI agent) are delegated work on this repository:

### Rule #1: NEVER Touch Master Branch

```bash
# ❌ FORBIDDEN - DO NOT DO THIS
git checkout master
git commit -m "..."
git push origin master
git push --no-verify

# ✅ CORRECT - ALWAYS DO THIS
git checkout -b feature/your-task
git commit -m "..."
git push origin feature/your-task
```

### Rule #2: Verify Branch Before Starting

**BEFORE making ANY changes**, check current branch:

```bash
git branch --show-current
```

**Expected output**: `feature/...` or `fix/...` or `docs/...`
**NEVER**: `master` or `main`

If on master:
1. ❌ **STOP immediately**
2. ⚠️ **Alert the coordinating agent**
3. ✅ **Create feature branch FIRST**

### Rule #3: Follow Conventional Commits

**EVERY commit MUST follow this format**:

```
type(scope): subject

body (optional)

footer (optional)
```

**Valid types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `refactor` - Code refactoring
- `test` - Test changes
- `style` - Code style/formatting
- `perf` - Performance improvements
- `build` - Build system changes
- `ci` - CI/CD changes

**Examples**:
```bash
# Good commits
git commit -m "feat(integration): add GitHub workflow dispatcher"
git commit -m "fix(docker): remove hardcoded token from compose file"
git commit -m "docs(agents): add gitflow guide for AI agents"
git commit -m "test(dispatcher): add unit tests for GitHub API client"

# Bad commits (DON'T USE)
git commit -m "updated files"           # No type, vague
git commit -m "fix stuff"                # No scope, unclear
git commit -m "Added new feature"        # Wrong tense (use imperative)
```

### Rule #4: NEVER Use --no-verify

```bash
# ❌ ABSOLUTELY FORBIDDEN
git commit --no-verify
git push --no-verify

# These bypass critical quality checks:
# - Black formatting
# - Ruff linting
# - Mypy type checking
# - Unit tests
# - Pre-push hooks
```

**Exception**: ONLY if explicitly instructed by user for emergency hotfix.

### Rule #5: Always Push to Feature Branch

```bash
# ✅ CORRECT
git push origin feature/github-pages-sync
git push origin fix/docker-token-removal
git push origin docs/agent-guidelines

# ❌ WRONG
git push origin master
git push origin main
git push  # (if on master branch)
```

---

## 📋 Workflow Checklist

Before you start work, verify:

- [ ] Current branch is NOT master (run: `git branch --show-current`)
- [ ] Feature branch exists (or create one)
- [ ] Branch name follows convention (feature/, fix/, docs/, etc.)

During work:

- [ ] Make focused, atomic changes
- [ ] Write clear commit messages (Conventional Commits)
- [ ] Run pre-commit checks locally
- [ ] All tests pass

After completing work:

- [ ] All changes committed to feature branch
- [ ] Feature branch pushed to origin
- [ ] PR created (if final step)
- [ ] NEVER pushed to master

---

## 🤖 Agent-Specific Scenarios

### Scenario 1: python-pro Agent Adding New Code

```bash
# 1. Verify branch
git branch --show-current  # Should be: feature/your-feature

# 2. Make changes
# ... create src/integrations/github_dispatcher.py ...

# 3. Commit with Conventional Commits
git add src/integrations/
git commit -m "feat(integration): add GitHub workflow dispatcher

- Implement GitHubWorkflowDispatcher class
- Add async trigger_workflow method
- Include retry logic and error handling
- Add comprehensive unit tests"

# 4. Push to feature branch
git push origin feature/your-feature
```

### Scenario 2: devops-engineer Agent Fixing Docker Config

```bash
# 1. Verify branch
git branch --show-current  # Should be: fix/docker-token

# 2. Make changes
# ... edit docker-compose.yml ...

# 3. Commit
git add docker-compose.yml
git commit -m "fix(docker): remove hardcoded GitHub token

- Replace inline environment variables with env_file
- Load secrets from .env file (gitignored)
- Update documentation with env_file usage"

# 4. Push to fix branch
git push origin fix/docker-token
```

### Scenario 3: qa-expert Agent Adding Tests

```bash
# 1. Verify branch
git branch --show-current  # Should be: test/github-integration

# 2. Add tests
# ... create tests/unit/test_github_dispatcher.py ...

# 3. Commit
git add tests/unit/test_github_dispatcher.py
git commit -m "test(integration): add GitHub dispatcher unit tests

- Test successful workflow trigger
- Test authentication failures
- Test rate limiting handling
- Test token masking in logs
- Achieve 98% code coverage"

# 4. Push to test branch
git push origin test/github-integration
```

### Scenario 4: Multi-Agent Coordination

When multiple agents work on same feature:

**Coordinator** (e.g., master-orchestrator):
```bash
# Create feature branch ONCE
git checkout -b feature/github-pages-sync

# Delegate to agent 1: python-pro
# Agent 1 commits to feature/github-pages-sync

# Delegate to agent 2: devops-engineer
# Agent 2 commits to feature/github-pages-sync

# Delegate to agent 3: qa-expert
# Agent 3 commits to feature/github-pages-sync

# Final push
git push origin feature/github-pages-sync

# Create PR
gh pr create --title "feat: GitHub Pages auto-sync integration" --body "..."
```

**Key Points**:
- ONE feature branch for the entire feature
- ALL agents commit to SAME feature branch
- Coordinator creates PR at the end
- NEVER push to master

---

### Scenario 7: Parallel Feature Development with Worktrees

When developing **7+ features in parallel**, use git worktrees for isolation:

**Coordinator** (master-orchestrator + worktree-orchestrator):
```python
# 1. Create 7 worktrees for parallel development
from src.worktree_manager import WorktreeManager

wm = WorktreeManager()
features = [
    ("feature/oauth2", "python-pro"),
    ("feature/redis-cache", "python-pro"),
    ("feature/websocket-notifications", "python-pro"),
    ("feature/rate-limiting", "security-engineer"),
    ("feature/database-migrations", "python-pro"),
    ("feature/enhanced-logging", "python-pro"),
    ("feature/performance-monitoring", "devops-engineer"),
]

worktrees = []
for feature_name, agent_type in features:
    info = wm.create_worktree(feature_name)
    worktrees.append((info, agent_type))
    print(f"Created {info.path} (port {info.port})")

# 2. Delegate to agents in parallel (each in its own worktree)
# Use Task tool with subagent_type parameter
for info, agent_type in worktrees:
    Task(
        subagent_type=agent_type,
        prompt=f"""
        Develop feature '{info.branch}' in worktree: {info.path}

        Worktree configuration:
        - Branch: {info.branch}
        - Port: {info.port}
        - Database: data/articles-{info.db_suffix}.db (isolated)
        - Venv: shared symlink to main venv

        GitFlow requirements:
        1. All changes committed to {info.branch} branch
        2. Conventional Commits format required
        3. Run tests with isolated database
        4. Push {info.branch} to origin when complete
        5. NEVER push to master

        Your task: Implement the feature for {info.branch}
        """
    )

# 3. Wait for all agents to complete
# 4. Create PRs for each feature
for info, _ in worktrees:
    subprocess.run([
        "gh", "pr", "create",
        "--base", "develop",
        "--head", info.branch,
        "--title", f"feat: {info.branch}"
    ])

# 5. Wait for CI/CD checks
# 6. Cleanup worktrees after PR merge
for info, _ in worktrees:
    wm.cleanup_worktree(info.branch)
```

**Individual Agent** (working in a worktree):
```python
# 1. Detect worktree environment
import subprocess
from pathlib import Path

branch = subprocess.check_output(['git', 'branch', '--show-current']).decode().strip()
is_worktree = Path.cwd().name.startswith('lolstonksrss-')

# 2. Configure for worktree mode
import os
from src.config import Settings

if is_worktree:
    settings = Settings(
        worktree_mode=True,
        worktree_branch=branch,
        worktree_db_suffix=branch.replace('/', '-'),
        worktree_port=int(os.getenv('WORKTREE_PORT', '8000'))
    )

# 3. Work in isolation
# - All git commands use current worktree branch
# - Tests use isolated database
# - Server uses allocated port (if applicable)

# 4. Commit and push
git add .
git commit -m "feat({feature_scope}): implement {feature_name}"
git push origin {branch}
```

**Key Points for Parallel Development**:
- **7+ features** developed simultaneously
- **Each worktree** has isolated database and port
- **Shared venv** via symlink (saves disk space)
- **No conflicts** between features
- **True parallelism** - no context switching
- **Automatic cleanup** after PR merge

**Benefits**:
- Massive throughput improvement (7x parallel development)
- Zero context switching overhead
- Emergency hotfix doesn't disrupt feature work
- Perfect for agent coordination

---

## ⚠️ Common Mistakes and Fixes

### Mistake #1: Committed to Master by Accident

**DON'T PANIC**

```bash
# Option A: Move commits to new branch
git branch feature/accidental-commits  # Save commits
git reset --hard origin/master          # Reset master
git checkout feature/accidental-commits # Work on feature branch

# Option B: Create feature branch and cherry-pick
git checkout -b feature/my-work
git cherry-pick <commit-hash>
git checkout master
git reset --hard origin/master
```

### Mistake #2: Pushed to Master (Already Remote)

**CRITICAL - Alert user immediately**

```
⚠️ CRITICAL ERROR: Accidentally pushed to master branch

Commit: <hash>
Message: <message>

Recommended actions:
1. git revert <hash> && git push origin master
2. Or coordinate with team for force reset

Awaiting user instructions.
```

### Mistake #3: Used --no-verify

**Acknowledge and remediate**:

1. Inform user of violation
2. Run all checks manually:
   ```bash
   uv run black --check src/ tests/
   uv run ruff check src/ tests/
   uv run mypy src/
   uv run pytest
   ```
3. Fix any failures
4. Create follow-up commit with fixes

---

## 📚 Quick Reference

### Branch Naming

| Type | Prefix | Example |
|------|--------|---------|
| New feature | `feature/` | `feature/github-pages-sync` |
| Bug fix | `fix/` | `fix/docker-token-exposure` |
| Documentation | `docs/` | `docs/agent-gitflow-guide` |
| Refactoring | `refactor/` | `refactor/api-client-structure` |
| Performance | `perf/` | `perf/rss-generation-optimization` |
| Tests | `test/` | `test/integration-github-api` |

### Commit Message Types

| Type | Usage | Example |
|------|-------|---------|
| `feat` | New feature | `feat(api): add webhook support` |
| `fix` | Bug fix | `fix(rss): escape XML special characters` |
| `docs` | Documentation | `docs(readme): update installation steps` |
| `test` | Tests | `test(api): add endpoint integration tests` |
| `refactor` | Refactoring | `refactor(database): simplify query logic` |
| `perf` | Performance | `perf(rss): cache feed generation` |
| `style` | Formatting | `style(api): apply Black formatting` |
| `build` | Build system | `build(docker): optimize image layers` |
| `ci` | CI/CD | `ci(github): add security scanning workflow` |

### Git Commands Reference

```bash
# Check current branch
git branch --show-current

# Create and switch to new branch
git checkout -b feature/your-feature

# Stage changes
git add <files>

# Commit with message
git commit -m "type(scope): subject"

# Push feature branch
git push origin feature/your-feature

# Set upstream for new branch
git push -u origin feature/your-feature

# Check status
git status

# View commit history
git log --oneline -10
```

---

## 🎓 Agent Self-Check Questions

Before **EVERY** git operation, ask yourself:

1. ❓ Am I on a feature branch? (NOT master)
2. ❓ Does my commit message follow Conventional Commits?
3. ❓ Am I pushing to a feature branch? (NOT master)
4. ❓ Have I run all pre-commit checks?
5. ❓ Are all tests passing?
6. ❓ Is this operation following the gitflow?

**If ANY answer is "No" or "Unsure"**:
- ⚠️ **STOP**
- 📋 **Review this guide**
- 🤔 **Ask coordinating agent for clarification**

---

## 📞 Escalation Path

If you encounter:

1. **Uncertain about gitflow** → Ask coordinating agent
2. **Accidental master push** → Alert user immediately
3. **Pre-commit hooks failing** → Fix issues, don't bypass
4. **Merge conflicts** → Request user guidance
5. **CI/CD checks failing** → Review logs, fix issues, re-push

**NEVER**:
- Bypass hooks without permission
- Push to master to "fix quickly"
- Ignore failing checks
- Make assumptions about gitflow

---

## 🏆 Success Criteria

You've followed gitflow correctly when:

- ✅ All work done on feature/fix/docs branches
- ✅ Master branch never touched directly
- ✅ All commits follow Conventional Commits format
- ✅ All pre-commit/pre-push hooks pass
- ✅ Feature branch pushed, PR created
- ✅ CI/CD checks passing
- ✅ Code review requested

---

**Remember**: Gitflow is not bureaucracy. It's essential for:
- Code quality (automated checks)
- Team collaboration (code review)
- Change tracking (conventional commits)
- Deployment safety (PR-based merges)
- Professional standards (SDLC compliance)

**Your adherence to gitflow directly impacts project quality and team efficiency.**

---

*Last Updated: 2025-12-30*
*Version: 1.0.0*
*For: AI Agents working on lolstonksrss repository*
