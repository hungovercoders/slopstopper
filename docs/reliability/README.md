# Reliability Testing

## Overview

This directory contains documentation and tests for ensuring the reliability of deployed sites through automated smoke testing.

## Smoke Tests

Smoke tests are lightweight, critical-path tests that verify a deployed site is functioning correctly. These tests run against live URLs (production or staging) and check for:

- Page availability (200 status codes)
- Core navigation functionality
- Asset loading
- Response times
- Critical content rendering

### Running Smoke Tests Locally

**Using Task (Recommended):**

```bash
# Pass URL as argument
task ss:reliability:smoke -- https://your-site.netlify.app

# Or set environment variable
SMOKE_TEST_URL=https://your-site.netlify.app task ss:reliability:smoke
```

**Using npm directly:**

```bash
SMOKE_TEST_URL=https://your-site.netlify.app npm run test:smoke
```

**Using Playwright CLI:**

```bash
SMOKE_TEST_URL=https://your-site.netlify.app npx playwright test tests/smoke.spec.js
```

### Running in CI/CD

For GitHub Actions or other CI environments, use the CI-specific task:

```bash
SMOKE_TEST_URL=https://your-site.netlify.app task ss:reliability:smoke:ci
```

This enables:
- Automatic retries (2 retries on failure)
- Single worker for consistency
- HTML and list reporters
- Proper CI failure modes

### GitHub Actions Example

Create `.github/workflows/ss-reliability-smoke-tests.yml`:

```yaml
name: Smoke Tests

on:
  # Run on every deployment
  deployment_status:
  
  # Run on schedule (every hour)
  schedule:
    - cron: '0 * * * *'
  
  # Allow manual trigger
  workflow_dispatch:
    inputs:
      url:
        description: 'URL to test'
        required: true
        default: 'https://your-site.netlify.app'

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          
      - name: Install dependencies
        run: npm ci
        
      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium
        
      - name: Run smoke tests
        env:
          SMOKE_TEST_URL: ${{ github.event.inputs.url || 'https://your-site.netlify.app' }}
        run: task ss:reliability:smoke:ci
        
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: smoke-test-results
          path: playwright-report/
          retention-days: 30
```

### What the Smoke Tests Check

1. **Homepage Availability** - Ensures the main page loads with 200 status
2. **Secondary Pages** - Verifies all critical pages are accessible
3. **Navigation** - Tests basic user navigation flows
4. **Static Assets** - Confirms CSS and JS files load correctly
5. **Performance** - Validates pages load within acceptable timeframes (< 5s)
6. **Error Detection** - Checks for JavaScript console errors

### Test Configuration

Tests are configured in [playwright.config.js](../../playwright.config.js):
- Uses `SMOKE_TEST_URL` environment variable when set
- Falls back to `BASE_URL` or localhost
- Skips local dev server when testing external URLs
- Includes retries in CI mode

### Adding New Smoke Tests

When adding critical functionality to your site, update [tests/smoke.spec.ts](../../tests/smoke.spec.ts):

```javascript
test('new critical feature works', async ({ page }) => {
  await page.goto('/new-feature');
  
  // Verify the feature loads
  expect(response.status()).toBe(200);
  
  // Test critical functionality
  await expect(page.locator('#critical-element')).toBeVisible();
});
```

### Best Practices

1. **Keep tests fast** - Smoke tests should complete in under 2 minutes
2. **Test critical paths only** - Focus on must-work functionality
3. **Avoid test data dependencies** - Tests should work on any deployment
4. **Set appropriate timeouts** - Allow for network latency in production
5. **Monitor regularly** - Run on a schedule to catch degradation early

### Monitoring Recommendations

- **Frequency**: Run every 15-60 minutes depending on SLA requirements
- **Alerting**: Configure GitHub Actions to notify on failures
- **Retention**: Keep test results for at least 30 days
- **Review**: Regularly review test coverage and update as site evolves

### Troubleshooting

**Tests fail locally but pass in CI:**
- Check SMOKE_TEST_URL is set correctly
- Verify the target URL is accessible from your network
- Ensure Playwright browsers are installed: `npx playwright install`

**Tests timeout:**
- Increase timeout in test: `test.setTimeout(30000)`
- Check site is responding (try curl/wget)
- Verify no network issues or rate limiting

**Flaky tests:**
- Add explicit waits: `await page.waitForLoadState('networkidle')`
- Increase retries in CI configuration
- Check for timing-dependent assertions

### Related Documentation

- [Playwright Testing Guide](https://playwright.dev/docs/intro)
- [GitHub Actions Documentation](https://docs.github.com/actions)
- [Contributing Guidelines](../contributing/README.md)
