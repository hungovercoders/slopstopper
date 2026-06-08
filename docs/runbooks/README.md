# Runbooks

Operational procedures for the SlopStopper project.

## Available runbooks

- [adoption-metrics.md](adoption-metrics.md) — How to measure who is using SlopStopper using only public GitHub signals. Backs `task ss:meta:adoption`.

## Adding Runbooks

When operational procedures are needed, add them here as individual markdown files. Examples:

- `incident-response.md` — Steps for responding to site outages
- `secret-rotation.md` — Process for rotating Cloudflare API tokens
- `rollback.md` — How to roll back a bad deployment (Cloudflare dash → Workers → Deployments → roll back to a previous version)
