# GitHub Pages Deployment Checklist

Complete this checklist to deploy your news page to GitHub Pages.

## Pre-Deployment Checklist

### 1. Files Verification

- [x] `.github/workflows/publish-news.yml` - Workflow file created
- [x] `scripts/generate_news_page.py` - Generation script exists
- [x] `templates/news_page.html` - Template exists
- [x] `scripts/test_news_workflow.py` - Test script created
- [x] Documentation files created:
  - [x] `GITHUB_PAGES_QUICKSTART.md`
  - [x] `docs/SETUP_GITHUB_PAGES.md`
  - [x] `docs/GITHUB_PAGES_NEWS.md`
  - [x] `docs/GITHUB_PAGES_DELIVERY.md`

### 2. Local Testing

- [ ] Run test script: `python scripts/test_news_workflow.py`
- [ ] Verify all steps pass
- [ ] Check generated `news.html` file
- [ ] Open `_site/index.html` in browser
- [ ] Verify page displays correctly

### 3. Update Repository URLs

- [ ] Replace `yourusername` in `README.md` with your GitHub username
- [ ] Find all instances (there are several)
- [ ] Update badge URLs
- [ ] Update live news page links

**Quick find-and-replace:**
- Find: `yourusername`
- Replace: `YOUR-GITHUB-USERNAME`

Files to update:
- [ ] `README.md` (multiple locations)

## Deployment Checklist

### 4. GitHub Repository Setup

- [ ] Repository is on GitHub
- [ ] Repository is public (or GitHub Pro for private)
- [ ] You have admin access to repository

### 5. Enable GitHub Pages

- [ ] Go to repository Settings
- [ ] Click Pages in sidebar
- [ ] Set Source to "GitHub Actions"
- [ ] Click Save

### 6. Configure Workflow Permissions

- [ ] Go to Settings > Actions > General
- [ ] Under Workflow permissions:
  - [ ] Select "Read and write permissions"
  - [ ] Check "Allow GitHub Actions to create and approve pull requests"
- [ ] Click Save

### 7. Push Workflow to GitHub

**Option A - Push all files:**
```bash
git add .
git commit -m "Add GitHub Pages news publishing workflow"
git push origin main
```

**Option B - Push workflow only:**
```bash
git add .github/workflows/publish-news.yml
git add GITHUB_PAGES_QUICKSTART.md
git add docs/SETUP_GITHUB_PAGES.md
git add docs/GITHUB_PAGES_NEWS.md
git add scripts/test_news_workflow.py
git commit -m "Add GitHub Pages news publishing workflow"
git push origin main
```

### 8. Monitor First Deployment

- [ ] Go to Actions tab
- [ ] Click on "Publish News to GitHub Pages" workflow
- [ ] Watch workflow run (should take 2-3 minutes)
- [ ] Verify all steps complete successfully (green checkmarks)

### 9. Verify Deployment

- [ ] Workflow shows "Success" status
- [ ] Visit `https://YOUR-USERNAME.github.io/lolstonksrss/`
- [ ] Page loads correctly
- [ ] Articles are displayed
- [ ] Filtering works
- [ ] Search works
- [ ] Theme switcher works
- [ ] Mobile view is responsive

### 10. Test Manual Trigger (Optional)

- [ ] Go to Actions tab
- [ ] Click "Publish News to GitHub Pages"
- [ ] Click "Run workflow" button
- [ ] Select branch (main)
- [ ] Set article limit (e.g., 50)
- [ ] Click "Run workflow"
- [ ] Verify manual run succeeds

## Post-Deployment Checklist

### 11. Update Documentation

- [ ] Add live URL to your documentation
- [ ] Update README with live link
- [ ] Test all documentation links

### 12. Set Up Monitoring

- [ ] Add status badge to README (already in place)
- [ ] Set up email notifications for failed workflows
- [ ] (Optional) Set up Discord/Slack notifications
- [ ] (Optional) Add analytics to news page

### 13. Optimize for Your Needs

**If exceeding GitHub Actions free tier:**
- [ ] Increase update interval to 10-15 minutes
- [ ] OR upgrade to GitHub Pro
- [ ] OR set up self-hosted runner

**Customization options:**
- [ ] Adjust article limit if needed
- [ ] Customize template colors/styling
- [ ] Add custom domain (optional)
- [ ] Add logo or branding

### 14. Test Automatic Updates

- [ ] Wait 5 minutes for next scheduled run
- [ ] Verify workflow runs automatically
- [ ] Check that page content updates
- [ ] Verify auto-refresh works in browser

## Ongoing Maintenance Checklist

### Weekly Tasks
- [ ] Check workflow run status
- [ ] Review for any failed runs
- [ ] Monitor GitHub Actions minutes usage

### Monthly Tasks
- [ ] Review analytics (if enabled)
- [ ] Check for template updates
- [ ] Update dependencies if needed
- [ ] Review and clean up old workflow caches

### As Needed
- [ ] Update article limit based on usage
- [ ] Adjust update frequency if needed
- [ ] Customize template design
- [ ] Add new features to news page

## Troubleshooting Checklist

If something goes wrong, check:

### Workflow Fails
- [ ] Check workflow logs in Actions tab
- [ ] Verify permissions are correct
- [ ] Check if GitHub API is down
- [ ] Review error messages
- [ ] Try manual trigger to reproduce

### Page Shows 404
- [ ] Verify GitHub Pages is enabled
- [ ] Check source is set to "GitHub Actions"
- [ ] Wait 2-3 minutes for propagation
- [ ] Clear browser cache
- [ ] Check deployment logs

### Empty News Page
- [ ] Check "Fetch latest news" step in logs
- [ ] Verify LoL API is accessible
- [ ] Test locally with test script
- [ ] Check database initialization

### Page Not Updating
- [ ] Verify workflow is running every 5 minutes
- [ ] Check for failed workflow runs
- [ ] Clear browser cache
- [ ] Check auto-refresh meta tag

## Success Criteria

Your deployment is successful when:

- [x] Workflow file is valid YAML
- [x] Local testing passes
- [ ] Workflow runs successfully on GitHub
- [ ] Page is accessible at GitHub Pages URL
- [ ] Articles are displayed correctly
- [ ] Page updates automatically every 5 minutes
- [ ] All features work (filter, search, theme switch)
- [ ] Mobile view is responsive
- [ ] Documentation is up to date

## Resources

Quick reference documentation:

- **5-minute setup**: `GITHUB_PAGES_QUICKSTART.md`
- **Detailed setup**: `docs/SETUP_GITHUB_PAGES.md`
- **Full documentation**: `docs/GITHUB_PAGES_NEWS.md`
- **Technical details**: `docs/GITHUB_PAGES_DELIVERY.md`
- **Test script**: `scripts/test_news_workflow.py`

External resources:

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [GitHub Pages Docs](https://docs.github.com/en/pages)
- [GitHub Actions Pricing](https://docs.github.com/en/billing/managing-billing-for-github-actions)

## Getting Help

If you encounter issues:

1. Review the troubleshooting section in `docs/SETUP_GITHUB_PAGES.md`
2. Check workflow logs in the Actions tab
3. Search existing GitHub issues
4. Open a new issue with:
   - Workflow logs
   - Error messages
   - Steps to reproduce
   - Expected vs actual behavior

## Completion

Once all items are checked:

- [ ] Deployment is complete and verified
- [ ] Documentation is updated
- [ ] Monitoring is set up
- [ ] Next steps are planned

**Congratulations!** Your League of Legends news page is now live and auto-updating every 5 minutes!

**Live URL**: `https://YOUR-USERNAME.github.io/lolstonksrss/`

Share it with the community and enjoy automatic news updates!

---

**Last Updated**: 2025-12-29
**Project**: LoL Stonks RSS
