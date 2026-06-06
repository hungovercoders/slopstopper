import { test, expect } from '@playwright/test';

test.describe('Git Commit Drift Detection', () => {
  test('index.html should contain the expected git commit SHA', async ({ page }) => {
    await page.goto('/');

    const commitSha = await page.locator('meta[name="git-commit"]').getAttribute('content');
    expect(commitSha).toBeTruthy();

    if (process.env.GITHUB_SHA) {
      expect(commitSha).toBe(process.env.GITHUB_SHA);
    }
  });
});
