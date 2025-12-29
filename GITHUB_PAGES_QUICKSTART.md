# GitHub Pages News - Quick Start

Get your League of Legends news page live in 5 minutes!

## What You'll Get

A beautiful, auto-updating news page at `https://YOUR-USERNAME.github.io/lolstonksrss/` with:

- Latest 100 LoL news articles
- LoL-themed design (dark/light mode)
- Auto-refresh every 5 minutes
- Mobile-friendly responsive layout
- Filtering and search capabilities
- Zero hosting costs

## 5-Minute Setup

### 1. Enable GitHub Pages (1 minute)

```
Repository Settings > Pages > Source > GitHub Actions > Save
```

### 2. Configure Permissions (1 minute)

```
Repository Settings > Actions > General > Workflow permissions >
Select "Read and write permissions" > Save
```

### 3. Update URLs (1 minute)

Replace `yourusername` with your GitHub username in:
- `README.md` (all instances)

```bash
# Quick find-and-replace
# Find: yourusername
# Replace: YOUR-GITHUB-USERNAME
```

### 4. Deploy (1 minute)

**Option A - Push workflow:**
```bash
git add .github/workflows/publish-news.yml
git commit -m "Add GitHub Pages news publishing"
git push origin main
```

**Option B - Manual trigger:**
```
Actions tab > Publish News to GitHub Pages > Run workflow
```

### 5. Visit Your Page (1 minute)

```
https://YOUR-USERNAME.github.io/lolstonksrss/
```

Done! Your news page is now live and will auto-update every 5 minutes.

## Customization (Optional)

### Change Update Frequency

Edit `.github/workflows/publish-news.yml`:

```yaml
schedule:
  - cron: '*/10 * * * *'  # Every 10 minutes (instead of 5)
```

### Change Number of Articles

Edit `.github/workflows/publish-news.yml`:

```yaml
workflow_dispatch:
  inputs:
    article_limit:
      default: '150'  # Show 150 articles (instead of 100)
```

### Customize Design

Edit `templates/news_page.html` - change colors, layout, features, etc.

## Monitoring

### Add Status Badge to README

```markdown
[![News Updates](https://img.shields.io/github/actions/workflow/status/YOUR-USERNAME/lolstonksrss/publish-news.yml)](https://github.com/YOUR-USERNAME/lolstonksrss/actions/workflows/publish-news.yml)
```

### View Workflow Runs

```
Actions tab > Publish News to GitHub Pages
```

## Troubleshooting

### Page shows 404
- Verify GitHub Pages is enabled (Step 1)
- Wait 1-2 minutes for deployment
- Clear browser cache (Ctrl+F5)

### Workflow fails
- Check workflow permissions (Step 2)
- View logs in Actions tab
- Ensure repository is public

### Empty news page
- Check workflow logs for API errors
- Verify LoL API is accessible
- Try manual workflow trigger

## Cost & Limits

**GitHub Actions Free Tier:**
- 2,000 minutes/month for public repos
- This workflow uses ~25,920 minutes/month (every 5 min)

**Solutions if exceeding free tier:**
1. Increase interval to 10-15 minutes (~13,000-17,000 min/month)
2. Upgrade to GitHub Pro (3,000 minutes/month)
3. Use self-hosted runner (free)

**GitHub Pages:**
- Unlimited for public repositories
- Free hosting and CDN

## Need Help?

- **Detailed Guide**: [docs/SETUP_GITHUB_PAGES.md](docs/SETUP_GITHUB_PAGES.md)
- **Full Documentation**: [docs/GITHUB_PAGES_NEWS.md](docs/GITHUB_PAGES_NEWS.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/lolstonksrss/issues)

## What's Next?

1. Share your news page with the LoL community
2. Customize the template to your style
3. Add analytics tracking
4. Set up a custom domain (optional)
5. Enable email/Discord notifications

---

**Questions?** Check the [full documentation](docs/GITHUB_PAGES_NEWS.md) or open an issue!
