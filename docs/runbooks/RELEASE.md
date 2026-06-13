# Cutting a release

slopstopper-cli ships via GitHub Releases. The [`ss-release.yml`](../../.github/workflows/ss-release.yml) workflow fires on any `v*.*.*` tag push, builds the wheel + sdist, and creates a GitHub Release with notes pulled from [`CHANGELOG.md`](../../CHANGELOG.md). PyPI publishing is intentionally **not** automated yet — that needs a Trusted Publisher trust relationship set up on PyPI first.

## When to bump

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (`1.0.0`) — breaking changes to the CLI surface, check names, or report formats.
- **MINOR** (`0.X.0`) — new subcommands, new checks, additive configuration knobs.
- **PATCH** (`0.0.X`) — bug fixes, doc-only changes, dependency bumps.

If in doubt, prefer a MINOR bump over a PATCH.

## Release steps

1. **Make sure `main` is green.** Every check on the most recent commit should be passing — CI on the release tag re-runs everything, so a broken `main` blocks the release.

2. **Update the CHANGELOG.** Move the `## [Unreleased]` block contents under a new `## [X.Y.Z] - YYYY-MM-DD` heading. Leave a stub `## [Unreleased]` block at the top:

   ```markdown
   ## [Unreleased]

   Nothing yet.

   ## [0.3.0] - 2026-07-01

   ### Added
   - …
   ```

   The workflow's release-notes extractor matches `## [X.Y.Z]` exactly — keep the format consistent.

3. **Bump the version in lockstep.** Two files need to match the tag:

   - `cli/pyproject.toml` → `version = "X.Y.Z"`
   - `cli/slopstopper/__init__.py` → `__version__ = "X.Y.Z"`

   The release workflow has a sanity-check step that fails the build if these diverge from the tag.

4. **Bump the pinned install URL** across docs, the website, `install.sh`, and every `ss-*-check.yml` workflow. The pattern to replace is `@vOLD#subdirectory=cli` → `@vNEW#subdirectory=cli`:

   ```bash
   # From the repo root, swap the old tag for the new one everywhere:
   git ls-files | xargs grep -l "@vOLD#subdirectory=cli" 2>/dev/null \
     | xargs sed -i.bak "s|@vOLD#subdirectory=cli|@vNEW#subdirectory=cli|g" \
     && find . -name '*.bak' -delete
   ```

   This keeps adopters' fresh installs pinned to a known-good release and slopstopper.dev's own CI (which uses the editable install when `cli/` is present) unaffected.

5. **Commit + push** the CHANGELOG, version bumps and URL bumps as a single commit (`chore(release): bump version to X.Y.Z`). Open a PR if you want CI to pre-verify; otherwise push straight to `main` if you have permission.

6. **Tag + push.** Once the bump commit is on `main`:

   ```bash
   git tag vX.Y.Z -m "X.Y.Z"
   git push origin vX.Y.Z
   ```

7. **Watch the workflow.** The `SlopStopper · Release` workflow runs against the tag. It will:
   - Verify versions match the tag.
   - Build wheel + sdist with `python -m build` (uses `hatchling`).
   - Extract the matching `## [X.Y.Z]` section from `CHANGELOG.md`.
   - Create the GitHub Release with that body and both artifacts attached.

8. **Verify the release.** Open [Releases](https://github.com/hungovercoders/slopstopper/releases). Sanity-check the body, download the wheel, run `pipx install <path-to-wheel>` somewhere and confirm `slopstopper --version` matches.

## Manual re-release

If the workflow fails partway, fix the cause then trigger it from the Actions tab → `SlopStopper · Release` → `Run workflow` → enter the tag. The job is idempotent: if a Release already exists for the tag, the workflow uploads any missing artifacts and exits.

## Manual PyPI publish (until Trusted Publisher is set up)

Once the GitHub Release lands, the artifacts are at `cli/dist/`. From a clean local checkout of the tag:

```bash
cd cli && python -m build
pipx run twine upload dist/*
```

You'll be prompted for a PyPI API token (use a project-scoped one — never the account-wide token). Once Trusted Publisher OIDC is configured on PyPI's side, we'll add a `publish-pypi` job to `ss-release.yml` and this manual step goes away.
