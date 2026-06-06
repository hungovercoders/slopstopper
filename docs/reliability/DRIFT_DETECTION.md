# Git Commit Drift Detection

This template includes automated git commit drift detection to verify that a deployed environment is running the exact code version it is expected to be running. If drift is detected, it means the environment may be out of date or have been deployed from the wrong source.

## Quick Start

### Check Drift Locally

```bash
task drift-detect
```

### What You Get Automatically

- ✅ Drift detection runs on every PR and push to `main`
- ✅ Validates the deployed `app/index.html` carries the correct commit SHA
- ✅ Fails the check if the wrong commit is detected

---

## How It Works

### 1. Commit Marker in the App

A placeholder is embedded in `app/index.html` as an HTML meta tag:

```html
<meta name="git-commit" content="__GIT_COMMIT__">
```

This placeholder has **no value** at rest in version control — it is only meaningful after injection.

### 2. SHA Injection at Deploy Time

When the deployment or drift-detection workflow runs, a `sed` step replaces the placeholder with the real commit SHA before serving files:

```bash
sed -i 's/__GIT_COMMIT__/${{ github.sha }}/g' app/index.html
```

The rendered page then contains the exact SHA, for example:

```html
<meta name="git-commit" content="abc1234def5678...">
```

### 3. Playwright Drift Test

The test in `.ss/tests/drift-detection.spec.js` reads the meta tag from the live page and compares it against the expected `GITHUB_SHA` environment variable:

```js
const commitSha = await page.locator('meta[name="git-commit"]').getAttribute('content');
expect(commitSha).toBeTruthy();

if (process.env.GITHUB_SHA) {
  expect(commitSha).toBe(process.env.GITHUB_SHA);
}
```

If the deployed app was built from a different commit — or was never properly injected — this test fails and surfaces the drift.

---

## Files Involved

| File | Purpose |
|------|---------|
| [`app/index.html`](../../app/index.html) | Contains the `__GIT_COMMIT__` placeholder meta tag |
| [`.ss/tests/drift-detection.spec.js`](../../.ss/tests/drift-detection.spec.js) | Playwright spec that validates the commit SHA |
| [`.github/workflows/drift-detection.yml`](../../.github/workflows/drift-detection.yml) | Dedicated CI workflow for drift detection |
| [`.github/workflows/ss-netlify-deploy.yml`](../../.github/workflows/ss-netlify-deploy.yml) | Injects the SHA before deployment |
| [`Taskfile.yml`](../../Taskfile.yml) | `drift-detect` task for running locally |

---

## Running Locally

To run the drift detection test locally (the placeholder will not be injected, so only the presence check runs):

```bash
# Install Task (one-time setup)
curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin

# Run drift detection
task drift-detect
```

To simulate a full CI run with SHA injection:

```bash
# Inject a SHA manually
sed -i 's/__GIT_COMMIT__/my-test-sha-123/g' app/index.html

# Run with GITHUB_SHA set so the full assertion fires
GITHUB_SHA=my-test-sha-123 BASE_URL=http://localhost:8080 task drift-detect

# Restore the placeholder
git checkout app/index.html
```

---

## Applying This Pattern to Other Systems

The commit-marker pattern is general and can be extended to any environment where you want to verify what version is actually running.

### API / Backend Health Endpoint

Embed the commit SHA in a `/health` or `/version` endpoint response:

```json
{
  "status": "ok",
  "git_commit": "__GIT_COMMIT__"
}
```

Inject the SHA at build or container image creation time:

```bash
sed -i 's/__GIT_COMMIT__/${{ github.sha }}/g' config/version.json
```

A Playwright (or any HTTP) test can then call the endpoint and assert the SHA:

```js
const res = await page.request.get('/health');
const body = await res.json();
expect(body.git_commit).toBe(process.env.GITHUB_SHA);
```

This is especially useful for:
- Canary or blue-green deployments where you want to confirm which instance is live
- Staging environments that should always track a specific branch
- Post-deploy smoke tests that run against the real environment

### Database / Persistent Store

For systems where the version needs to be persisted (e.g. to detect a stale schema migration or data seed), store the commit SHA in a dedicated table or key-value entry at deploy time:

```sql
-- Example: store current deploy version in a settings table
INSERT INTO settings (key, value) VALUES ('git_commit', '__GIT_COMMIT__')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

Replace the placeholder before running migrations:

```bash
sed -i 's/__GIT_COMMIT__/${{ github.sha }}/g' migrations/seed_version.sql
```

A test or monitoring script then queries this value and compares it to the expected SHA, alerting if the database is behind or was seeded from a different source.

---

## Disabling Drift Detection

**Option A:** Disable the workflow in the GitHub UI
- Go to Actions → Git Commit Drift Detection → Disable workflow

**Option B:** Delete the workflow file
```bash
rm .github/workflows/drift-detection.yml
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Test passes but SHA is `__GIT_COMMIT__` | The `sed` injection step did not run — check the workflow logs |
| Test fails with SHA mismatch | The deployed file was built from a different commit; re-deploy from the correct branch |
| Test passes locally but fails in CI | Ensure `GITHUB_SHA` is set as an `env:` entry in the workflow step |
