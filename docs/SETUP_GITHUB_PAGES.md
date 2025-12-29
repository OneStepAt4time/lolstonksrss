# GitHub Pages Setup Guide

Quick guide to enable automatic news page publishing to GitHub Pages.

## Prerequisites

- GitHub repository with this project
- Repository must be public (or GitHub Pro/Enterprise for private repos)
- Admin access to repository settings

## Step-by-Step Setup

### 1. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** (top navigation)
3. In the left sidebar, click **Pages**
4. Under **Source**, select **GitHub Actions**
5. Click **Save**

![GitHub Pages Settings](https://docs.github.com/assets/cb-47267/mw-1440/images/help/pages/publishing-source-drop-down.webp)

### 2. Configure Workflow Permissions

1. Still in **Settings**, click **Actions** in the left sidebar
2. Click **General**
3. Scroll to **Workflow permissions**
4. Select **Read and write permissions**
5. Check **Allow GitHub Actions to create and approve pull requests**
6. Click **Save**

### 3. Update Repository URLs

Before deploying, update the URLs in the files to match your repository:

**In `.github/workflows/publish-news.yml`** - No changes needed, URLs are dynamic

**In `README.md`** - Replace `yourusername` with your GitHub username:
```markdown
# Find and replace all instances of:
https://yourusername.github.io/lolstonksrss/

# With:
https://YOUR-USERNAME.github.io/lolstonksrss/
```

**Tip**: Use find-and-replace in your editor (Ctrl+H or Cmd+H):
- Find: `yourusername`
- Replace: `YOUR-GITHUB-USERNAME`

### 4. Trigger First Deployment

**Option A: Push the workflow file**
```bash
git add .github/workflows/publish-news.yml
git commit -m "Add GitHub Pages news publishing workflow"
git push origin main
```

**Option B: Manual trigger**
1. Go to **Actions** tab
2. Click **Publish News to GitHub Pages** in the left sidebar
3. Click **Run workflow** button (right side)
4. Select branch (`main`)
5. Optionally set article limit (default: 100)
6. Click **Run workflow**

### 5. Monitor Deployment

1. Go to **Actions** tab
2. Click on the running workflow
3. Watch the progress of each step
4. Wait for deployment to complete (~2-3 minutes)

### 6. Verify Your News Page

Once the workflow completes successfully:

1. Visit `https://YOUR-USERNAME.github.io/lolstonksrss/`
2. You should see the news page with latest LoL articles
3. The page will auto-update every 5 minutes

## Customization Options

### Change Update Frequency

Edit `.github/workflows/publish-news.yml`:

```yaml
# Every 5 minutes (default)
- cron: '*/5 * * * *'

# Every 10 minutes
- cron: '*/10 * * * *'

# Every 30 minutes
- cron: '*/30 * * * *'

# Every hour
- cron: '0 * * * *'

# Every 6 hours
- cron: '0 */6 * * *'
```

**Note**: GitHub Actions minimum interval is 5 minutes.

### Change Article Limit

Edit `.github/workflows/publish-news.yml`:

```yaml
workflow_dispatch:
  inputs:
    article_limit:
      default: '150'  # Change from 100 to 150
```

Or specify when manually triggering the workflow.

### Customize News Page Template

Edit `templates/news_page.html` to change:
- Colors and styling
- Layout and structure
- Feature set
- Branding

Changes will be applied on the next workflow run.

## Using Custom Domain (Optional)

### 1. Add CNAME File

Create `static/CNAME` file:
```
news.yourdomain.com
```

Update workflow to copy it:
```yaml
- name: Create GitHub Pages directory structure
  run: |
    mkdir -p _site
    cp news.html _site/index.html
    cp static/CNAME _site/CNAME  # Add this line
```

### 2. Configure DNS

Add DNS record with your domain provider:
- **Type**: CNAME
- **Name**: news (or your subdomain)
- **Value**: YOUR-USERNAME.github.io
- **TTL**: 3600 (or default)

### 3. Configure Custom Domain in GitHub

1. Go to **Settings** > **Pages**
2. Under **Custom domain**, enter `news.yourdomain.com`
3. Click **Save**
4. Wait for DNS check to complete
5. Check **Enforce HTTPS** (recommended)

Wait 24-48 hours for full DNS propagation.

## Troubleshooting

### Workflow Fails

**Error: "Resource not accessible by integration"**
- Fix: Enable workflow permissions (Step 2 above)

**Error: "Pages deployment failed"**
- Fix: Ensure GitHub Pages source is set to "GitHub Actions" (Step 1)

**Error: "No module named 'src'"**
- Fix: This is expected in first run. The workflow installs dependencies automatically.

### Page Shows 404

**Issue**: Page not found at GitHub Pages URL

**Solutions**:
1. Verify workflow completed successfully (green checkmark in Actions)
2. Check GitHub Pages is enabled (Settings > Pages)
3. Confirm repository is public
4. Wait 1-2 minutes for CDN propagation
5. Clear browser cache (Ctrl+F5 / Cmd+Shift+R)

### Empty News Page

**Issue**: Page loads but shows no articles

**Solutions**:
1. Check workflow logs for errors in "Fetch latest news" step
2. Verify LoL API is responding correctly
3. Test locally: `python scripts/generate_news_page.py`
4. Check database initialization in workflow logs

### Workflow Exceeds Free Tier

**Issue**: Running out of GitHub Actions minutes

**Solutions**:
1. **Increase interval**: Change from 5 minutes to 10 or 15 minutes
2. **Use self-hosted runner**: Run on your own infrastructure
3. **Upgrade to GitHub Pro**: Get 3,000 minutes/month
4. **Optimize workflow**: Enable more aggressive caching

Example calculation:
- 5-minute interval = 288 runs/day = 8,640 runs/month
- 3 minutes per run = ~25,920 minutes/month (exceeds free tier)
- 10-minute interval = 144 runs/day = ~12,960 minutes/month (within Pro tier)

## Monitoring

### View Workflow Status

Add badge to README:
```markdown
[![News Updates](https://img.shields.io/github/actions/workflow/status/YOUR-USERNAME/lolstonksrss/publish-news.yml?label=news%20updates)](https://github.com/YOUR-USERNAME/lolstonksrss/actions/workflows/publish-news.yml)
```

### Set Up Notifications

**Email notifications** (GitHub default):
- Settings > Notifications > Actions
- Enable "Send notifications for failed workflows only"

**Discord/Slack notifications** (advanced):
Add to workflow:
```yaml
- name: Notify on failure
  if: failure()
  uses: sarisia/actions-status-discord@v1
  with:
    webhook: ${{ secrets.DISCORD_WEBHOOK }}
    title: "News page deployment failed"
```

## Advanced Configuration

### Multiple Environments

Deploy to staging and production:

1. Create `deploy-news-staging.yml` with different branch
2. Create `deploy-news-production.yml` for main branch
3. Use different GitHub Pages repositories or branches

### Analytics Integration

Add Google Analytics or similar to `templates/news_page.html`:

```html
<head>
  <!-- Existing content -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=GA_TRACKING_ID"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'GA_TRACKING_ID');
  </script>
</head>
```

### Database Persistence

The workflow caches the database between runs to reduce API calls. To clear the cache:

1. Go to **Actions** > **Caches**
2. Delete old `lol-news-db-*` caches
3. Next run will fetch fresh data

## Best Practices

1. **Start with longer intervals**: Test with 15-30 minute intervals first
2. **Monitor usage**: Check Actions usage in Settings > Billing
3. **Test locally first**: Run `python scripts/generate_news_page.py` before pushing
4. **Use caching**: Keep database and dependency caching enabled
5. **Version control**: Commit workflow changes with descriptive messages
6. **Document changes**: Update this guide when modifying the workflow

## Next Steps

After successful setup:

1. **Share the link**: Add your news page URL to social media, Discord, etc.
2. **Customize branding**: Edit the template to match your style
3. **Set up monitoring**: Configure alerts for workflow failures
4. **Optimize performance**: Fine-tune update frequency based on usage
5. **Add features**: Enhance the template with additional functionality

## Support

For issues:
1. Check [GitHub Pages News documentation](GITHUB_PAGES_NEWS.md)
2. Review workflow logs in Actions tab
3. Search [GitHub Issues](https://github.com/yourusername/lolstonksrss/issues)
4. Open a new issue with workflow logs

## Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Pricing](https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions)
- [Project Documentation](../README.md)

---

**Setup Time**: ~5 minutes
**First Deployment**: ~2-3 minutes
**Updates**: Automatic every 5 minutes
