# Upgrade the pinned `slopstopper-cli`

`slopstopper-cli` is pinned per-repo. The pin lives in
[`mise.toml`](../../mise.toml) as the `[tools]` entry `"pipx:slopstopper-cli"`,
and mise installs it both locally and in CI (via `jdx/mise-action`). mise
activates the tool per-directory, so the active `slopstopper` always matches the
repo you're in — there's no single global binary to drift between repos. A
breaking upstream release cannot reach your repo until you choose to move the
pin. Upgrades are a decision, not a surprise.

## How the pin behaves

- **First install** records the latest published version into `mise.toml`. Commit
  it so CI installs the same version.
- **A plain `install.sh` re-run** honours the pin in `mise.toml` and never bumps
  it — refreshes only pull new workflows/shims.
- **CI** reads the same `mise.toml` via `jdx/mise-action` and installs that exact
  version, so local and CI always run the same CLI.
- The post-install banner nudges you when the pin is behind PyPI's latest, with
  the one command that moves it — informational, never forced.

## Move the pin

From inside the repo:

```bash
bash install.sh --upgrade-cli        # bump to the latest published version
bash install.sh --cli-version X.Y.Z  # pin to an exact version
```

Both wrap `mise use`: they rewrite the `"pipx:slopstopper-cli"` entry in
`mise.toml`, install that version locally, and the change ships to CI once you
commit. You can also move it directly:

```bash
mise use pipx:slopstopper-cli@latest   # or @X.Y.Z
```

## Recommended flow

1. Skim the [changelog](https://github.com/hungovercoders/slopstopper/releases)
   for breaking changes since your current pin.
2. Run `install.sh --upgrade-cli` (or `--cli-version X.Y.Z`).
3. Drive every check green locally — `task ss:hygiene:test`,
   `task ss:security:scan`, plus any dynamic checks — before pushing. The
   [`slopstopper-install`](../../.claude/skills/slopstopper-install/SKILL.md)
   skill's local-verify loop covers this.
4. Commit `mise.toml` (the bumped pin) with the rest of the change so CI installs
   the new version.

## Recover from drift

If `slopstopper --version` no longer matches the pin in `mise.toml` (e.g. a stale
shim, or mise isn't activated in your shell), run `mise install` in the repo —
it reinstalls the pinned `slopstopper-cli`. Re-running `install.sh` with no flags
does the same and restores the pin. Ensure mise is
[activated](https://mise.jdx.dev/getting-started.html) so the pinned binary is on
PATH; do not install slopstopper-cli globally by hand to "fix" a check — that
drifts you off the committed pin without updating CI.

## Migrating from a legacy `cli_version` pin

Older installs pinned the CLI in `.slopstopper.yml` as `cli_version`. The next
`install.sh` run migrates that value into `mise.toml` and removes the dead key
automatically — commit the resulting `mise.toml`.
