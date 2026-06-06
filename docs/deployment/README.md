# Deployment

Release and environment workflows for the SlopStopper project.

## Overview

This project deploys a static site to Netlify using GitHub Actions. The
build step compiles TypeScript via `npm run build` (`tsc`) before Netlify
publishes the `app/` directory.

## Workflows

| Workflow | Trigger | Purpose |
| -------- | ------- | ------- |
| [ss-netlify-deploy.yml](../../.github/workflows/ss-netlify-deploy.yml) | Push to `main` / PR to `main` | Production deploy and PR preview deploy |
| [ss-netlify-cleanup-preview.yml](../../.github/workflows/ss-netlify-cleanup-preview.yml) | PR closed | Delete preview deployments to free Netlify resources |

## Environments

- **Production**: Deployed on push to `main`. URL: `https://<site-name>.netlify.app/`
- **Preview**: Created per PR. URL: `https://pr-<number>--<site-name>.netlify.app`

## Required Secrets

| Secret | Where to find |
| ------ | ------------- |
| `NETLIFY_AUTH_TOKEN` | Netlify User settings → Applications → Personal access tokens |
| `NETLIFY_SITE_ID` | Netlify Site settings → General → Site details → Site ID |

## Configuration

Deployment is configured via [netlify.toml](../../netlify.toml):
- Publish directory: `app`
- Build command: `npm run build` (runs `tsc`)
- Security headers (CSP, frame-ancestors, etc.) are defined in `netlify.toml` and applied by Netlify in production and by `server.js` locally for parity.
