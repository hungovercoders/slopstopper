# Runbooks

Operational procedures for the SlopStopper project — both the suite itself and the things adopters do once around it.

## Overview

This directory holds step-by-step runbooks for common operational tasks. As the project is a minimal static site template, operational procedures are currently minimal.

## Runbooks

| Runbook | What it covers |
| ------- | -------------- |
| [INSTALL_SKILL.md](./INSTALL_SKILL.md) | Install the [`install-slopstopper`](../../.claude/skills/install-slopstopper/SKILL.md) Claude Code skill into your user profile so any project on this machine can ask Claude Code to add SlopStopper |

## Adding Runbooks

When operational procedures are needed, add them here as individual markdown files. Examples:

- `incident-response.md` — Steps for responding to site outages
- `secret-rotation.md` — Process for rotating Cloudflare API tokens
- `rollback.md` — How to roll back a bad deployment (Cloudflare dash → Workers → Deployments → roll back to a previous version)
