# Quick Guide: Upload to GitHub

This is a simplified guide to upload the LoL Stonks RSS project to GitHub.

## Prerequisites
- Git installed and configured
- GitHub account created
- Repository initialized (DONE - commit: 25f0f62)

## Method 1: Using GitHub CLI (Recommended)

```bash
# Install GitHub CLI if not already installed
# Download from: https://cli.github.com/

# Login to GitHub
gh auth login

# Create repository and push
gh repo create lolstonksrss --public --source=. --remote=origin --push

# Or for private repository
gh repo create lolstonksrss --private --source=. --remote=origin --push
```

## Method 2: Using GitHub Web + Git CLI

### Step 1: Create Repository on GitHub
1. Go to https://github.com/new
2. Repository name: `lolstonksrss`
3. Description: `RSS feed generator for League of Legends news - Docker containerized for Windows server deployment`
4. Choose Public or Private
5. **DO NOT** check any initialization options (README, .gitignore, license)
6. Click "Create repository"

### Step 2: Connect and Push
```bash
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/lolstonksrss.git

# Verify remote is added
git remote -v

# Push to GitHub
git push -u origin master

# Or if you prefer 'main' as branch name
git branch -M main
git push -u origin main
```

## Method 3: Using SSH (More Secure)

```bash
# Set up SSH key if not already done
# Follow: https://docs.github.com/en/authentication/connecting-to-github-with-ssh

# Add remote with SSH
git remote add origin git@github.com:YOUR_USERNAME/lolstonksrss.git

# Push to GitHub
git push -u origin master
```

## After Uploading - Repository Configuration

### Add Description and Topics
Go to your repository on GitHub and add:

**Description:**
```
RSS feed generator for League of Legends news - Docker containerized for Windows server deployment
```

**Topics/Tags:**
```
python docker rss league-of-legends fastapi windows-server containerization
```

### Enable Features
In Settings > General:
- [x] Issues
- [x] Discussions (optional but recommended)
- [x] Preserve this repository (optional)

### Set Up Branch Protection (Optional)
In Settings > Branches > Add branch protection rule:
- Branch name pattern: `main` or `master`
- [x] Require pull request reviews before merging
- [x] Require status checks to pass before merging
- [x] Require branches to be up to date before merging

### Add Repository Secrets (For CI/CD)
In Settings > Secrets and variables > Actions:
- Add `CODECOV_TOKEN` (if using Codecov)
- Other secrets as needed

## Verify Upload Success

Check that these are working:
1. All files visible on GitHub
2. README.md renders correctly
3. License shows as MIT
4. Issue templates appear in Issues > New Issue
5. CI workflow appears in Actions tab
6. Security policy visible in Security tab

## Update README Badges (Optional)

Add to top of README.md after upload:

```markdown
![CI](https://github.com/YOUR_USERNAME/lolstonksrss/workflows/CI/badge.svg)
![License](https://img.shields.io/github/license/YOUR_USERNAME/lolstonksrss)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
```

Then commit and push:
```bash
git add README.md
git commit -m "Add CI status badges"
git push
```

## Common Issues and Solutions

### Authentication Failed
```bash
# Use Personal Access Token (PAT) instead of password
# Create PAT at: https://github.com/settings/tokens
# Use PAT as password when prompted
```

### Push Rejected (non-fast-forward)
```bash
# This shouldn't happen with a new repo, but if it does:
git pull origin master --rebase
git push -u origin master
```

### Want to Change Remote URL
```bash
# Switch from HTTPS to SSH
git remote set-url origin git@github.com:YOUR_USERNAME/lolstonksrss.git

# Switch from SSH to HTTPS
git remote set-url origin https://github.com/YOUR_USERNAME/lolstonksrss.git
```

### Wrong Branch Name
```bash
# Rename master to main
git branch -M main
git push -u origin main

# Delete old branch on GitHub (via web UI or CLI)
git push origin --delete master
```

## Next Steps After Upload

1. **Create First Release**
   - Go to Releases > Create a new release
   - Tag version: `v1.0.0`
   - Release title: `LoL Stonks RSS v1.0.0`
   - Describe features from CHANGELOG.md
   - Publish release (this will trigger Docker publish workflow)

2. **Set Up Project Board** (optional)
   - Projects > New project
   - Create boards for: To Do, In Progress, Done
   - Link issues to project

3. **Enable GitHub Pages** (optional)
   - Settings > Pages
   - Source: Deploy from a branch
   - Branch: main, folder: /docs
   - Save

4. **Invite Collaborators** (if needed)
   - Settings > Collaborators
   - Add team members

5. **Set Up Notifications**
   - Watch repository for updates
   - Configure email preferences

## Repository URLs

After upload, your repository will be available at:
- **Web**: https://github.com/YOUR_USERNAME/lolstonksrss
- **Clone HTTPS**: https://github.com/YOUR_USERNAME/lolstonksrss.git
- **Clone SSH**: git@github.com:YOUR_USERNAME/lolstonksrss.git

## Docker Image Publishing

Once you create a release on GitHub:
- Docker workflow will automatically build image
- Image published to: `ghcr.io/YOUR_USERNAME/lolstonksrss`
- Tagged with version number and `latest`

Pull the image:
```bash
docker pull ghcr.io/YOUR_USERNAME/lolstonksrss:latest
```

## Need Help?

- GitHub Documentation: https://docs.github.com
- Git Documentation: https://git-scm.com/doc
- GitHub CLI: https://cli.github.com/manual
- See GIT_SETUP_COMPLETE.md for full details

---

**Repository Status:** Ready for Upload
**Commit Hash:** 25f0f62
**Files:** 134 tracked files
**Lines of Code:** 36,997+
