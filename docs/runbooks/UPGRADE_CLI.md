# Upgrade the pinned `slopstopper-cli`

`slopstopper-cli` is pinned per-repo. The pinned version lives in
[`.slopstopper.yml`](../../.slopstopper.yml.example) as `cli_version`, and both
`install.sh` and the `ss-*.yml` workflows install `slopstopper-cli==<cli_version>`.
This is deliberate: a breaking upstream release cannot reach your repo — locally
or in CI — until you choose to move the pin. Upgrades are a decision, not a
surprise.

## How the pin behaves

- **First install** records the latest published version as the pin and writes
  it into `.slopstopper.yml`. Commit it.
- **A plain `install.sh` re-run** reinstalls exactly the pinned version. It never
  bumps the CLI — refreshes only pull new workflows/shims.
- **CI** reads the same `cli_version` and installs that exact version, so local
  and CI always run the same CLI.
- The post-install banner nudges you when the pin is behind PyPI's latest, with
  the one command that moves it — informational, never forced.

## Move the pin

From inside the repo:

```bash
bash install.sh --upgrade-cli        # bump to the latest published version
bash install.sh --cli-version X.Y.Z  # pin to an exact version
```

Either flag rewrites the `cli_version` line in `.slopstopper.yml`, reinstalls
that version locally, and the change ships to CI once you commit.

## Recommended flow

1. Skim the [changelog](https://github.com/hungovercoders/slopstopper/releases)
   for breaking changes since your current pin.
2. Run `install.sh --upgrade-cli` (or `--cli-version X.Y.Z`).
3. Drive every check green locally — `task ss:hygiene:test`,
   `task ss:security:scan`, plus any dynamic checks — before pushing. The
   [`slopstopper-install`](../../.claude/skills/slopstopper-install/SKILL.md)
   skill's local-verify loop covers this.
4. Commit `.slopstopper.yml` (the bumped pin) with the rest of the change so CI
   installs the new version.

## Recover from drift

If `slopstopper --version` no longer matches `cli_version` (e.g. a manual
`pipx upgrade` moved the local binary off the pin), re-run `install.sh` with no
flags — it reinstalls `slopstopper-cli==<cli_version>` and restores the pin. Do
not `pipx upgrade` by hand to "fix" a check; that drifts you off the committed
pin without updating CI.
