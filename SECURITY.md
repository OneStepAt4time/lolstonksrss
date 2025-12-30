# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please email security@example.com instead of using the issue tracker.

---

## Security Best Practices for Developers

### 1. Never Commit Secrets

**❌ NEVER commit:**
- API keys
- Passwords
- Tokens
- Private keys
- Credentials
- Connection strings with passwords

**✅ ALWAYS use:**
- Environment variables
- `.env` files (added to `.gitignore`)
- Secret management services
- Configuration templates (`.example` files)

### 2. Files to NEVER Commit

```
.env
.env.local
.mcp.json
glm_settings.json
*secrets.json
*credentials.json
*.key
*.pem
*token*
```

All these patterns are in `.gitignore` and will be blocked by pre-commit hooks.

### 3. Configuration File Templates

We provide template files for configuration:

- `.env.example` → Copy to `.env` and fill in your values
- `.mcp.json.example` → Copy to `.mcp.json` and add your API keys
- `glm_settings.json.example` → Copy to `glm_settings.json` and configure

**Never commit the actual files, only the `.example` templates!**

### 4. Pre-commit Hooks

This repository uses pre-commit hooks to prevent secrets from being committed.

**Setup:**
```bash
git config core.hooksPath .githooks
```

**The hooks will:**
- ✅ Scan for API keys, tokens, passwords
- ✅ Block commits containing secrets
- ✅ Check code quality
- ✅ Validate commit messages

**To bypass (NOT RECOMMENDED):**
```bash
git commit --no-verify  # Only use in emergencies
```

### 5. What to Do If You Commit a Secret

**IMMEDIATE ACTIONS:**

1. **Revoke the secret immediately**
   - Rotate API keys
   - Change passwords
   - Invalidate tokens

2. **Remove from repository**
   ```bash
   # Remove file from git tracking
   git rm --cached <file-with-secret>

   # Add to .gitignore
   echo "<file-with-secret>" >> .gitignore

   # Commit the fix
   git add .gitignore
   git commit -m "fix(security): remove exposed secrets"

   # Force push (if already pushed)
   git push --force
   ```

3. **Clean git history (if needed)**
   ```bash
   # Use BFG Repo-Cleaner or git-filter-repo
   # https://rtyley.github.io/bfg-repo-cleaner/

   bfg --delete-files <secret-file>
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   git push --force
   ```

4. **Monitor for unauthorized usage**
   - Check API logs
   - Review access logs
   - Monitor billing/usage

### 6. Secret Scanning Tools

**GitHub Secret Scanning** (already enabled for public repos)
- Automatically scans for known secret patterns
- Alerts repository admins
- Free for public repositories

**Additional Tools:**

```bash
# TruffleHog - Find secrets in git history
docker run --rm -v "$(pwd):/pwd" trufflesecurity/trufflehog:latest filesystem /pwd

# Gitleaks - Detect secrets in code
docker run -v $(pwd):/path zricethezav/gitleaks:latest detect --source="/path" -v

# git-secrets - Prevent commits
git secrets --install
git secrets --register-aws
```

### 7. Environment Variables

**Local Development:**
```bash
# Create .env file (in .gitignore)
cp .env.example .env

# Edit with your secrets
nano .env
```

**Production:**
```bash
# Use environment variables directly
export API_KEY="your-key"
export DATABASE_URL="your-db-url"

# Or use secret management
# - AWS Secrets Manager
# - HashiCorp Vault
# - Docker secrets
# - Kubernetes secrets
```

### 8. Docker Secrets

**Never bake secrets into images:**

```dockerfile
# ❌ BAD - Secret in image
ENV API_KEY=sk-1234567890

# ✅ GOOD - Use build args and runtime env
ARG API_KEY
ENV API_KEY=${API_KEY}

# ✅ BETTER - Use Docker secrets
RUN --mount=type=secret,id=api_key \
    API_KEY=$(cat /run/secrets/api_key) && \
    # use API_KEY
```

**Docker Compose with secrets:**
```yaml
services:
  app:
    environment:
      - API_KEY=${API_KEY}  # From host environment
    env_file:
      - .env  # From file (in .gitignore)
```

### 9. Code Review Checklist

Before approving PRs, verify:

- [ ] No hardcoded credentials
- [ ] No API keys in code
- [ ] No passwords in config files
- [ ] `.env` files are in `.gitignore`
- [ ] Only `.example` config files committed
- [ ] Secrets passed via environment variables
- [ ] Pre-commit hooks are passing
- [ ] No sensitive data in logs

### 10. Incident Response

**If secrets are exposed:**

1. **Immediate (within 1 hour):**
   - Revoke/rotate all exposed credentials
   - Remove secrets from repository
   - Force push to overwrite history

2. **Short-term (within 24 hours):**
   - Audit logs for unauthorized access
   - Check for unusual activity
   - Review billing for unexpected charges
   - Notify affected parties if needed

3. **Long-term (within 1 week):**
   - Document incident
   - Implement additional safeguards
   - Review and improve processes
   - Train team on security practices

---

## SDLC Security Integration

### Development Phase
- Use `.example` files for configuration templates
- Never hardcode secrets in source code
- Use environment variables for all credentials
- Run secret scanning before commits

### Testing Phase
- Use test/mock credentials
- Never use production secrets in tests
- Separate test and production environments

### Deployment Phase
- Inject secrets at runtime
- Use secret management services
- Rotate secrets regularly
- Audit access to secrets

### Maintenance Phase
- Regular security audits
- Monitor for exposed secrets
- Update dependencies
- Review access logs

---

## Quick Reference

### Setup New Developer

```bash
# 1. Clone repository
git clone https://github.com/OneStepAt4time/lolstonksrss.git

# 2. Setup git hooks
git config core.hooksPath .githooks

# 3. Copy configuration templates
cp .env.example .env
cp .mcp.json.example .mcp.json
cp glm_settings.json.example glm_settings.json

# 4. Fill in your API keys in the copied files
nano .env
nano .mcp.json
nano glm_settings.json

# 5. NEVER commit these files
# They are already in .gitignore
```

### Before Every Commit

```bash
# Pre-commit hooks run automatically and will:
# 1. Scan for secrets
# 2. Check code quality
# 3. Validate commit message

# If blocked, check what was detected:
git status
git diff --cached

# Remove sensitive data and try again
```

---

## Contact

For security concerns: security@example.com

**Last Updated:** 2025-12-29
