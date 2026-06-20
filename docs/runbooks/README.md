# Runbooks

Operational procedures for the SlopStopper project — both the suite itself and the things adopters do once around it.

## Overview

This directory holds step-by-step runbooks for common operational tasks. As the project is a minimal static site template, operational procedures are currently minimal.

## Runbooks

| Runbook | What it covers |
| ------- | -------------- |
| [INSTALL_SKILLS.md](./INSTALL_SKILLS.md) | Install the SlopStopper Claude Code skill trio (`slopstopper-install`, `slopstopper-update`, `slopstopper-triage`) into your user profile so any project on this machine can ask Claude Code to add, refresh, or triage SlopStopper |
| [UPGRADE_CLI.md](./UPGRADE_CLI.md) | Move the pinned `slopstopper-cli` version (`cli_version` in `.slopstopper.yml`) with `install.sh --upgrade-cli` / `--cli-version`, and recover from a binary that drifted off the pin |
| [RELEASE.md](./RELEASE.md) | Cut a `slopstopper-cli` release: CHANGELOG bump, version bump in `cli/pyproject.toml` + `__init__.py`, tag, GitHub Release via `ss-release.yml`, optional manual PyPI publish |

## Adding Runbooks

When operational procedures are needed, add them here as individual markdown files. Examples:

- `incident-response.md` — Steps for responding to site outages
- `secret-rotation.md` — Process for rotating Cloudflare API tokens
- `rollback.md` — How to roll back a bad deployment (Cloudflare dash → Workers → Deployments → roll back to a previous version)
