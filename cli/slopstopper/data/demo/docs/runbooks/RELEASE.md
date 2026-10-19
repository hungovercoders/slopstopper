# Releasing

A release is a tag. Tag the commit, push the tag, and the host deploys
it:

```bash
git tag -a v1.2.0 -m "v1.2.0: billing moved to the payments team"
git push --tags
```

The tag message is the changelog, so write it for the people who read
the page: what changed, not which files moved.

## Rolling back

Retag the previous commit as the next version rather than deleting the
bad tag. The host caches by tag name, and a deleted tag can be served
from that cache for up to an hour.

This runbook has no route from `docs/README.md`, so the
`hygiene:docs-structure` check fails until one is added. That is the
fixture's second deliberate finding.
