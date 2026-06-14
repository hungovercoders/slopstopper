# Cutting a release

slopstopper-cli releases are automated end-to-end via two GitHub workflows:

1. [`release-please.yml`](../../.github/workflows/release-please.yml) watches `main` for [Conventional Commit](https://www.conventionalcommits.org/) pushes and maintains a perpetual **Release PR** that regenerates [`CHANGELOG.md`](../../CHANGELOG.md), bumps `cli/pyproject.toml` `version` and `cli/slopstopper/__init__.py` `__version__`. Merging it creates the matching `vX.Y.Z` tag + GitHub Release with notes.
2. [`ss-release.yml`](../../.github/workflows/ss-release.yml) fires on that tag push, builds the wheel + sdist, signs them with Sigstore build-provenance, uploads to the GitHub Release, and publishes to PyPI via the OIDC Trusted Publisher flow.

End-to-end, **no human edits a CHANGELOG, bumps a version, or pushes a tag**. The only manual step is reviewing and merging the Release PR when you want the next version cut.

## The normal flow

1. **Open PRs with Conventional Commit messages.** `feat:` for new behaviour, `fix:` for bug fixes, `chore:`/`docs:`/`refactor:` for everything else. Use `feat!:` or a `BREAKING CHANGE:` footer for breaking changes.
2. **Merge PRs into `main` as usual.** Squash-merging keeps the commit titles clean — release-please reads the squash subject line.
3. **Watch the Release PR build up.** `release-please.yml` runs after every push to `main` and either opens a new Release PR or amends the existing one to reflect the latest commits. Title shape: `chore(main): release X.Y.Z`. The PR body is a preview of the CHANGELOG section it will write.
4. **Merge the Release PR when you want to cut.** That push creates the `vX.Y.Z` tag + GitHub Release with the generated notes, which immediately fires `ss-release.yml`.
5. **Watch `ss-release.yml` finish.** Roughly 30 seconds. It verifies versions, builds, attests, uploads artifacts to the already-created GitHub Release, and publishes to PyPI.
6. **Verify** (one-liner — same checks each time):

   ```bash
   pip index versions slopstopper-cli                   # latest should match the tag
   gh release download vX.Y.Z --pattern '*.whl'
   gh attestation verify slopstopper_cli-X.Y.Z-py3-none-any.whl --owner hungovercoders
   ```

## Bumping rules

Configured in [`release-please-config.json`](../../release-please-config.json):

| Commit type | Bump (pre-1.0) | Bump (post-1.0) |
|-------------|----------------|------------------|
| `feat:` | MINOR | MINOR |
| `fix:` | PATCH | PATCH |
| `feat!:` / `BREAKING CHANGE:` | MINOR | MAJOR |
| anything else (`chore:`, `docs:`, `refactor:`, `test:`, `ci:`) | no version bump | no version bump |

Pre-1.0 we set `bump-minor-pre-major: true` so `feat:` still moves the version meaningfully (0.3.0 → 0.4.0). Breaking changes also bump MINOR pre-1.0 — this is intentional: an explicit "we're not promising stability yet" signal. Once we cut 1.0.0, breaking changes start bumping MAJOR.

`chore(release): bump version to X.Y.Z` commits — what release-please writes itself — do not trigger another bump on the next pass (release-please ignores them).

## Idempotency notes

- **release-please-action** re-runs on every push to `main`, including the merge of its own Release PR. The second run detects the release commit and creates the tag + GitHub Release rather than opening another Release PR.
- **ss-release.yml** is tag-triggered. Its "Create GitHub Release" step checks for an existing release and uploads artifacts on top if found — so even if `release-please` already created the release, the build step just attaches the wheel + sdist + attestation. The "Publish to PyPI" step uses `skip-existing: true` for the same reason.
- Re-running either workflow from the Actions tab is safe.

## Manual fallback

If `release-please.yml` is wedged (the action is broken, a misconfiguration, etc.) you can cut a release by hand:

1. Edit `CHANGELOG.md`: move whatever's worth releasing under a new `## [X.Y.Z] - YYYY-MM-DD` heading. The format must match `## [X.Y.Z]` exactly — `ss-release.yml`'s release-notes extractor uses that regex.
2. Bump `cli/pyproject.toml` → `version = "X.Y.Z"` and `cli/slopstopper/__init__.py` → `__version__ = "X.Y.Z"`. The release workflow's sanity-check step fails the build if these diverge from the tag.
3. Commit (`chore(release): bump version to X.Y.Z`) and push to main. No further edits needed — adopter workflows, `install.sh`, READMEs and the website all pull `slopstopper-cli` from PyPI by name; the version isn't pinned in any of them.
4. Tag and push:

   ```bash
   git tag vX.Y.Z -m "X.Y.Z"
   git push origin vX.Y.Z
   ```

5. From here on it's identical to the automated flow — `ss-release.yml` builds, attests, releases, publishes.

Don't forget to update `.release-please-manifest.json` to the same version after a manual release so release-please's view of the world doesn't desync.

## Verifying build provenance

Every wheel and sdist in a release ≥ v0.2.1 ships with a Sigstore build-provenance attestation, generated by `actions/attest-build-provenance@v4` as part of `ss-release.yml`. The attestation cryptographically proves which workflow run, on which commit, in which repo produced the artifact — useful for adopters who want to confirm the wheel they're installing really came from the slopstopper release pipeline rather than a tampered upload.

Adopters verify with the `gh` CLI:

```bash
gh release download vX.Y.Z --pattern '*.whl' --repo hungovercoders/slopstopper
gh attestation verify slopstopper_cli-X.Y.Z-py3-none-any.whl --owner hungovercoders
```

A successful verification prints the workflow run + commit SHA that produced the wheel. A tampered wheel (or one not from this repo) makes the command exit non-zero.

No keys are managed manually — `attest-build-provenance` uses the workflow's keyless OIDC token via Sigstore, and the attestation lands in the public transparency log (Rekor). Free for public repos.

## One-time PyPI Trusted Publisher setup

This trust relationship was created on 2026-06-14 to enable the first automated PyPI publish. If you ever need to re-create it (project rename, dashboard reset, etc.), the steps are:

1. **Reserve the project name.** If `slopstopper-cli` is not on PyPI, use the **Pending Publisher** flow under <https://pypi.org/manage/account/publishing/> — no first manual upload is needed before the trust relationship exists.

   - Fill: **PyPI project name** `slopstopper-cli`, **Owner** `hungovercoders`, **Repository name** `slopstopper`, **Workflow filename** `ss-release.yml`, **Environment** (leave blank for now).
   - Save. The first publish from `ss-release.yml` will create the project under your account.

2. **For an already-published project.** Go to <https://pypi.org/manage/project/slopstopper-cli/settings/publishing/> → "Add a new publisher" with the same Owner / Repository / Workflow fields as above.

3. **Recommended hardening (post-first-publish).** Add a GitHub Environment named `pypi` to the slopstopper repo with required reviewers, then edit the `Publish to PyPI` step in `ss-release.yml` to declare `environment: pypi`. Re-add the publisher on PyPI with that environment name. From then on every PyPI publish requires a click-through approval.

The PyPI Trusted Publisher flow is the same OIDC trust pattern used by the Sigstore attestation step — no API tokens to manage, no secrets in repo settings, and the credentials cannot be exfiltrated because they are short-lived per-workflow-run tokens issued by GitHub's OIDC provider.
