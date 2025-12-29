# GitHub Pages News Publishing

This document explains how the LoL Stonks RSS project automatically publishes a beautiful, responsive news page to GitHub Pages.

## Overview

The project uses GitHub Actions to:
1. Fetch the latest League of Legends news every 5 minutes
2. Generate a beautiful HTML page with LoL branding
3. Deploy it to GitHub Pages automatically

**Live News Page**: [https://yourusername.github.io/lolstonksrss/](https://yourusername.github.io/lolstonksrss/)

## Features

### Automatic Updates
- **Frequency**: Every 5 minutes via GitHub Actions scheduled workflow
- **Source**: Official Riot Games LoL news API (EN-US and IT-IT locales)
- **Content**: Up to 100 latest news articles (configurable)

### Beautiful UI
- **LoL Branding**: Uses official League of Legends color scheme (gold, blue, dark theme)
- **Responsive**: Mobile-friendly design that works on all devices
- **Dark/Light Mode**: Theme switcher with auto-detection
- **Filtering**: Filter by source, category, or search term
- **Auto-refresh**: Page refreshes every 5 minutes to show latest news

### Performance
- **Static HTML**: Fast loading times (no server required)
- **CDN**: Served via GitHub Pages CDN for global availability
- **Optimized**: Minimal dependencies, all-in-one HTML file
- **Caching**: Database cached between workflow runs to reduce API calls

## Workflow Configuration

### Workflow File
Location: `.github/workflows/publish-news.yml`

### Trigger Schedule
```yaml
schedule:
  - cron: '*/5 * * * *'  # Every 5 minutes
```

### Manual Trigger
You can manually trigger the workflow from the GitHub Actions tab:
1. Go to `Actions` > `Publish News to GitHub Pages`
2. Click `Run workflow`
3. Optionally specify the number of articles (default: 100)

### Workflow Steps

1. **Checkout Repository** - Clone the latest code
2. **Set up Python 3.11** - Install Python runtime
3. **Install UV** - Fast Python package manager
4. **Cache Dependencies** - Speed up subsequent runs
5. **Install Dependencies** - Install project requirements
6. **Initialize Database** - Create SQLite database if needed
7. **Fetch Latest News** - Call LoL API to get latest articles
8. **Generate HTML Page** - Use Jinja2 template to create news.html
9. **Upload to GitHub Pages** - Deploy to GitHub Pages
10. **Verify Deployment** - Check that the page is accessible

## Configuration

### Article Limit
Default: 100 articles

To change the limit for manual runs:
```bash
# Via GitHub Actions UI
Actions > Publish News to GitHub Pages > Run workflow > article_limit: 150
```

To change the default limit, edit `.github/workflows/publish-news.yml`:
```yaml
workflow_dispatch:
  inputs:
    article_limit:
      default: '150'  # Change this value
```

### Update Frequency
Default: Every 5 minutes

To change the frequency, edit the cron schedule in `.github/workflows/publish-news.yml`:
```yaml
schedule:
  - cron: '*/10 * * * *'  # Every 10 minutes
  - cron: '0 * * * *'     # Every hour
  - cron: '0 */6 * * *'   # Every 6 hours
```

**Note**: GitHub Actions has a minimum interval of 5 minutes for scheduled workflows.

### Template Customization
The HTML template is located at `templates/news_page.html`. You can customize:
- **Colors**: Edit CSS variables in the `:root` section
- **Layout**: Modify HTML structure
- **Styling**: Add custom CSS
- **Functionality**: Add JavaScript features

After modifying the template, the workflow will automatically use the updated version on the next run.

## GitHub Pages Setup

### Initial Setup

1. **Enable GitHub Pages**:
   - Go to repository `Settings` > `Pages`
   - Under "Source", select `GitHub Actions`
   - Save the settings

2. **Configure Permissions**:
   - Go to repository `Settings` > `Actions` > `General`
   - Under "Workflow permissions", select `Read and write permissions`
   - Check `Allow GitHub Actions to create and approve pull requests`
   - Save

3. **First Deployment**:
   - Push the workflow file to the repository
   - Manually trigger the workflow or push a commit to main
   - Wait for the workflow to complete
   - Visit `https://yourusername.github.io/lolstonksrss/`

### Custom Domain (Optional)

To use a custom domain:

1. **Add CNAME file**:
   - Create `static/CNAME` file with your domain (e.g., `news.yourdomain.com`)
   - Update workflow to copy it to `_site/` directory

2. **Configure DNS**:
   - Add CNAME record pointing to `yourusername.github.io`
   - Wait for DNS propagation

3. **Configure GitHub Pages**:
   - Go to repository `Settings` > `Pages`
   - Enter your custom domain
   - Check "Enforce HTTPS"

## Monitoring

### Workflow Status
Monitor workflow runs at:
`https://github.com/yourusername/lolstonksrss/actions/workflows/publish-news.yml`

### Status Badge
Add to README:
```markdown
[![News Updates](https://img.shields.io/github/actions/workflow/status/yourusername/lolstonksrss/publish-news.yml?label=news%20updates)](https://github.com/yourusername/lolstonksrss/actions/workflows/publish-news.yml)
```

### Workflow Logs
To view detailed logs:
1. Go to `Actions` tab
2. Click on `Publish News to GitHub Pages` workflow
3. Click on a specific run
4. Click on the job to view logs

## Troubleshooting

### Workflow Fails

**Issue**: Workflow fails during database initialization
```
Solution: Check that the database path is correct and data/ directory exists
```

**Issue**: Workflow fails during news fetch
```
Solution: LoL API may be rate-limiting. Check logs for error messages.
          Consider increasing the update interval or adding retry logic.
```

**Issue**: Workflow fails during GitHub Pages deployment
```
Solution:
1. Verify GitHub Pages is enabled in repository settings
2. Check that workflow has proper permissions (Settings > Actions > General)
3. Ensure the repository is public (or GitHub Pro for private repos)
```

### Page Not Updating

**Issue**: News page shows old content

1. **Check workflow runs**: Verify the workflow is running successfully
2. **Clear browser cache**: Hard refresh (Ctrl+F5 or Cmd+Shift+R)
3. **Check GitHub Pages status**: Visit the Actions tab for deployment status
4. **Wait for propagation**: GitHub Pages CDN may take 1-2 minutes to update

### Empty News Page

**Issue**: Page loads but shows no articles

1. **Check database**: Verify that the database is being populated
2. **Check logs**: Look for errors in the "Fetch latest news" step
3. **API status**: Verify that the LoL API is responding correctly
4. **Test locally**: Run `python scripts/generate_news_page.py` to test

### Performance Issues

**Issue**: Workflow takes too long to complete

**Solutions**:
- Enable dependency caching (already configured)
- Reduce article limit for faster generation
- Use database caching between runs (already configured)
- Consider fetching from fewer locales

## Cost & Limits

### GitHub Actions Minutes
- **Free tier**: 2,000 minutes/month for public repositories
- **This workflow**: ~2-3 minutes per run
- **Monthly usage**: ~8,640-12,960 minutes (running every 5 minutes)

**Note**: The default every-5-minute schedule may exceed free tier limits. Consider:
- Increasing interval to 10-15 minutes
- Using a self-hosted runner
- Upgrading to GitHub Pro for more minutes

### GitHub Pages
- **Free**: Unlimited for public repositories
- **Bandwidth**: 100GB soft limit per month
- **Size**: 1GB repository size limit
- **Build time**: 10 minutes maximum

## Advanced Configuration

### Environment Variables

Add secrets or variables in repository settings for:
- Custom API endpoints
- Authentication tokens (if needed in future)
- Analytics tracking IDs

Example in workflow:
```yaml
env:
  CUSTOM_API_URL: ${{ secrets.LOL_API_URL }}
```

### Multiple Deployment Targets

Deploy to multiple platforms simultaneously:
```yaml
- name: Deploy to GitHub Pages
  uses: actions/deploy-pages@v4

- name: Deploy to Netlify
  uses: nwtgck/actions-netlify@v2
  with:
    publish-dir: '_site'
```

### Notification Setup

Add notifications on deployment:
```yaml
- name: Notify on Discord
  uses: sarisia/actions-status-discord@v1
  if: always()
  with:
    webhook: ${{ secrets.DISCORD_WEBHOOK }}
```

## Best Practices

1. **Monitor Usage**: Keep track of GitHub Actions minutes usage
2. **Optimize Frequency**: Balance freshness with resource usage
3. **Cache Wisely**: Use caching for dependencies and database
4. **Error Handling**: Implement retries for API failures
5. **Test Changes**: Test template changes locally before pushing
6. **Version Control**: Keep workflow versioned in git
7. **Documentation**: Update docs when changing configuration

## Related Documentation

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Project README](../README.md)
- [Testing Guide](TESTING_GUIDE.md)
- [Windows Deployment Guide](WINDOWS_DEPLOYMENT.md)

## Support

For issues with the news publishing workflow:
1. Check workflow logs in the Actions tab
2. Review this documentation
3. Open an issue on GitHub
4. Contact the maintainers

---

**Last Updated**: 2025-12-29
**Maintained By**: LoL Stonks RSS DevOps Team
