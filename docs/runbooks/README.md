# Runbooks

What you do once around the suite: install it into a repo, install the Claude Code skills, move the CLI pin, and, for the project itself, cut a release.

## Overview

This directory holds step-by-step runbooks for common operational tasks: what an adopter does once around the suite, and what the project does to cut a release.

## Routes

| When you are…                                                              | Do this                                                                                                   |
| -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| adopting slopstopper in a repo, or asking what the suite installs and needs | Read [INSTALL.md](./INSTALL.md) first for prerequisites, what lands, what each check needs, configuration and updates |
| installing or refreshing the Claude Code skill duo in a repo               | Read [INSTALL_SKILLS.md](./INSTALL_SKILLS.md) for `install-skill.sh`, what lands under `<repo>/.claude/skills/` and how to uninstall |
| moving the pinned `slopstopper-cli` version, or a binary drifted off the pin | Read [UPGRADE_CLI.md](./UPGRADE_CLI.md) for `install.sh --upgrade-cli` / `--cli-version`, `mise use` and recovery |
| cutting a `slopstopper-cli` release                                        | Read [RELEASE.md](./RELEASE.md) for release-please, the tag, `ss-release.yml` and the manual fallback        |

## Adding Runbooks

When operational procedures are needed, add them here as individual markdown files. Examples:

- `incident-response.md`, steps for responding to site outages
- `secret-rotation.md`, the process for rotating Cloudflare API tokens
- `rollback.md`, how to roll back a bad deployment (Cloudflare dash → Workers → Deployments → roll back to a previous version)
