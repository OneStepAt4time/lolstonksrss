# Pull Request

## Description
A clear and concise description of what this PR does.

## Related Issue
Fixes #(issue number)
Closes #(issue number)

## Type of Change
Please check options that are relevant (delete others):

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Dependency update
- [ ] CI/CD improvement
- [ ] Security fix

## Changes Made
List the specific changes made in this PR:
-
-
-

## GitFlow Branch Type
- [ ] Feature branch (`feature/*`) -> merging to `develop`
- [ ] Release branch (`release/*`) -> merging to `main` and `develop`
- [ ] Hotfix branch (`hotfix/*`) -> merging to `main` and `develop`
- [ ] Docs branch (`docs`) -> merging to `main` or `develop`
- [ ] Bugfix/other -> merging to `develop`

## Testing
Describe the testing you've done:

- [ ] Unit tests pass locally (`pytest tests/unit/`)
- [ ] Integration tests pass locally (`pytest tests/integration/`)
- [ ] E2E tests pass locally (`pytest tests/e2e/`)
- [ ] All tests pass (`pytest`)
- [ ] Manual testing performed
- [ ] Tested in Docker container
- [ ] Tested on Windows

### Test Configuration
- OS: [e.g. Windows Server 2022 / Ubuntu 22.04]
- Docker Version: [e.g. Docker Desktop 4.25.0]
- Python Version: [e.g. 3.11 / 3.12]

### Test Coverage
- [ ] Code coverage >= 90%
- [ ] New tests added for new functionality
- [ ] Existing tests updated if needed

## Code Quality Checks
- [ ] Black formatting passed (`black --check src/ tests/`)
- [ ] Ruff linting passed (`ruff check src/ tests/`)
- [ ] MyPy type checking passed (`mypy src/`)
- [ ] Pre-commit hooks passed
- [ ] No debugging code (print statements, breakpoints)
- [ ] No secrets in code

## Documentation
- [ ] Code docstrings added/updated
- [ ] README.md updated (if needed)
- [ ] CHANGELOG.md updated (if applicable)
- [ ] API documentation updated (if needed)
- [ ] Migration guide added (if breaking change)

## Security
- [ ] No sensitive data in code
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Dependencies security scanned
- [ ] Input validation added
- [ ] Error messages don't leak sensitive info

## Performance
- [ ] No performance regressions
- [ ] Performance tests passed (if applicable)
- [ ] Database queries optimized
- [ ] Async/await used appropriately
- [ ] No memory leaks

## Checklist
Before submitting this PR, please ensure:

- [ ] My code follows the project's style guidelines (PEP 8, Black formatting)
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published
- [ ] I have checked that my branch is up to date with the base branch
- [ ] I have followed the conventional commits format for commit messages
- [ ] I have read and followed the CONTRIBUTING.md guidelines

## Breaking Changes
If this PR includes breaking changes, describe them here:

**Before:**
```python
# Old behavior
```

**After:**
```python
# New behavior
```

**Migration Guide:**
Steps to migrate:
1.
2.
3.

## Screenshots (if applicable)
Add screenshots to demonstrate the changes.

## Deployment Notes
Are there any special deployment considerations?

- [ ] Requires environment variable changes (list below)
- [ ] Requires Docker image rebuild
- [ ] Requires database migration
- [ ] Requires configuration file updates
- [ ] Requires dependency updates
- [ ] Requires server restart

**Environment Variables:**
```
NEW_VAR=value
```

**Configuration Changes:**
```yaml
# Changes needed in config
```

## Rollback Plan
If this deployment fails, describe the rollback plan:

1.
2.

## Performance Impact
Describe any performance implications:

- [ ] No performance impact
- [ ] Performance improvement (describe below)
- [ ] Potential performance degradation (describe below)

**Details:**

## Additional Context
Add any other context about the pull request here.

---

## Reviewer Notes
Things to pay special attention to during review:

-
-

## Post-Merge Tasks
Tasks to complete after this PR is merged:

- [ ] Update staging environment
- [ ] Notify team
- [ ] Update documentation site
- [ ] Create release notes (if release PR)
- [ ] Other:

---

By submitting this pull request, I confirm that my contribution is made under the terms of the project license.
