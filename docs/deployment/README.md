# Deployment

How the SlopStopper site ships to production.

## Overview

The site is hosted on Cloudflare. A Cloudflare Worker serves the static
files in [`app/`](../../app/) via the `[assets]` binding and applies the
per-path security headers defined in
[`worker/headers.json`](../../worker/headers.json). **Cloudflare Workers
Builds** (Cloudflare's Git integration) handles the build and deploy on
every push and PR — there is **no** deploy workflow in this repo.

## Lifecycle

| Event | What happens | Where you see it |
| ----- | ------------ | ---------------- |
| Push to `main` | Workers Builds runs `npm run build`, then `wrangler deploy`. Worker is updated; custom domain serves the new version. | GitHub Deployments tab; Cloudflare dash → Workers → `slopstopper` → Deployments |
| Open PR | Workers Builds creates a Worker *version* with a unique preview URL of the form `<hash>-slopstopper.<account>.workers.dev`. | Commit check on the PR (Cloudflare Workers · Build) |
| New commit on the PR | Version is replaced; preview URL refreshes. | Same commit check, updated. |
| Close PR | Cloudflare retires the preview version automatically. | Cloudflare dash → Versions |

No GitHub Action ships deploys. No `NETLIFY_AUTH_TOKEN`-shaped secret
lives in repo settings. This is intentional — duplicating Cloudflare's
built-in capability with a GHA workflow only adds maintenance.

## Configuration

| File | Purpose |
| ---- | ------- |
| [`wrangler.jsonc`](../../wrangler.jsonc) | Worker definition: name, compatibility date, entrypoint, `[assets]` binding pointing at `./app`. Workers Builds reads it. |
| [`worker/index.ts`](../../worker/index.ts) | The Worker. Fetches the asset via `env.ASSETS.fetch(request)`, then applies headers from `worker/headers.json`. Also redirects `/feedback` → `/feedback.html`. |
| [`worker/headers.json`](../../worker/headers.json) | Canonical header map. Three entries: `/*` (strict default), `/og-image.png` (cross-origin CORP), `/feedback.html` (Giscus CSP relaxation). The Worker, `slopstopper serve` and the CSP-drift gate all read this. |

The build command Workers Builds runs is `npm run build` (TypeScript
compile of `src/` → `app/`). The pre-build asset render
(`task ss:contributing:assets`, which renders SVG → PNG via Playwright)
runs locally before commits — the PNG outputs are checked in.

## Visibility

- **README badge — per deploy.** shields.io renders a badge off the
  GitHub Deployments API:
  `https://img.shields.io/github/deployments/hungovercoders/slopstopper/Production`.
  Cloudflare's GitHub App writes a deployment event for every push.
- **README badge — live health.** The existing
  [`ss-reliability-smoke-tests.yml`](../../.github/workflows/ss-reliability-smoke-tests.yml)
  workflow runs hourly and on every `deployment_status` event, exposes
  its GitHub Actions status badge. That tells you "is the live site
  behaving right now."
- **Per-PR check.** Cloudflare's GitHub App writes a Workers Builds
  check on each PR commit with the preview URL — same shape as a
  Netlify preview deploy check.
- **Auto-issue on failure.** `ss-reliability-smoke-tests.yml` already
  opens (and closes) an issue labelled `smoke-test-failure` when the
  scheduled run fails on production.
- **Dashboard.** Cloudflare dash → Workers → `slopstopper` →
  Deployments shows the full per-version history with build logs.

## Cutover steps (manual, one-time)

1. **Confirm the Cloudflare account.** Note the Account ID.
2. **Connect the repo.** Cloudflare dash → Workers & Pages → Create →
   Connect to Git → select `slopstopper`. Cloudflare installs its
   GitHub App on the repo. Cloudflare reads `wrangler.jsonc`
   automatically; no build command override is needed.
3. **Move DNS to Cloudflare** if not already there (change registrar
   nameservers; wait for propagation).
4. **Attach the custom domain.** Cloudflare dash → Workers →
   `slopstopper` → Settings → Domains & Routes → Add Custom Domain.
   Cloudflare provisions the cert.
5. **(Local dev only)** create an API token scoped to
   `Account.Workers Scripts: Edit` and stash it in `.zshrc.local` as
   `CLOUDFLARE_API_TOKEN` so `wrangler dev` can authenticate.
6. **Delete the Netlify site** *after* the first successful Cloudflare
   prod deploy and a smoke-test pass against the new URL.
7. **Remove the `NETLIFY_AUTH_TOKEN` / `NETLIFY_SITE_ID` secrets** from
   the GitHub repo settings.

## Adopters

You don't get a deploy workflow from `install.sh` — connect your
repo in the Cloudflare dash and you're done. If you prefer a
different host, delete `wrangler.jsonc` and `worker/` and wire up
your own deploy. The header map in `worker/headers.json` is the only
file the suite's CSP-drift gate cares about; everything else is
optional.
