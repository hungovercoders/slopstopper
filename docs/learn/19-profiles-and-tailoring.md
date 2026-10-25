# Lesson 19: Profiles and tailoring

**Goal.** Switch a repo between the `ui`, `api` and `library` profiles,
keep one check a profile drops, and know where the CLI pin lives and
how it moves.

## Why this lesson

A check that cannot apply is noise, and noise is how gates get
ignored. The nine browser checks assume HTML, a DOM and a public web
surface; on an API they do not quietly no-op, they build, serve and
audit nothing and go red, and on a library there is nothing to serve
at all. A profile is a named preset for `workflows.disabled` that says
which workflows a repo of that shape should not carry. It only ever
subtracts, and `workflows.enabled` takes an individual check back out
of the profile's set, so an API that does serve a docs site can keep
the broken-links check.

The design has two rules worth knowing. The config is the home, not
the flag: `install.sh --profile api` writes `profile: api` into
`.slopstopper.yml`, and everything downstream (`doctor`, the installer,
the badges, the deploy trigger) reads the same resolved set from the
one mapping in `profiles.json`. And detection suggests, never applies:
`profile detect` reads the repo's contents and prints a suggestion,
because a wrong silent pick, with checks quietly off, is worse than the
default superset, with checks visibly red.

The other thing an adopter tailors is the CLI version, which is pinned
per repo in `mise.toml` so a breaking upstream release cannot reach a
repo until someone moves the pin.

## You will need

The checkout from the [syllabus](README.md), with the CLI on PATH.

## Steps

### 1. See what this repo resolves to, and why

<!-- learn -->
```sh
slopstopper profile show
```

```
  Profile: ui  (from .slopstopper.yml)
      A web UI: a site or app that serves HTML to a browser.

  Disabled workflows (4):
    · ss-hygiene-openapi-check.yml               (profile, no API detected)
    · ss-reliability-api-health-check.yml        (profile, no API detected)
    · ss-reliability-api-latency-check.yml       (profile, no API detected)
    · ss-security-api-headers-check.yml          (profile, no API detected)
```

Every check applies to a site, except the four API checks from lesson
16, which the `ui` profile holds back until the repo shows an API: a
spec, a server framework or an `api.*` key. Each line says why it is
off.

### 2. Ask for a suggestion

<!-- learn -->
```sh
slopstopper profile detect
```

```
  Suggested profile: ui  (found app/feedback.html)
  Active profile:    ui (already a match, nothing to do).
```

The installer prints the same suggestion when it differs from the
active profile, and still does not change anything.

### 3. Read the whole mapping

<!-- learn -->
```sh
slopstopper profile list
```

```
  ui  (default)
      A web UI: a site or app that serves HTML to a browser.
      …
      holds back 4 workflow(s) until the repo shows an API:
        · ss-reliability-api-health-check.yml
        · ss-security-api-headers-check.yml
        · ss-reliability-api-latency-check.yml
        · ss-hygiene-openapi-check.yml

  api
      An HTTP API: JSON/gRPC endpoints with no browser-rendered surface.
      …
      disables 9 workflow(s):
        · ss-reliability-smoke-tests.yml
        · ss-reliability-e2e-check.yml
        …

  library
      A library, CLI or package with no deployed surface of any kind.
      …
      disables 15 workflow(s):
```

### 4. Switch the repo to the API profile

The installer does this with `--profile api`; the key it writes is the
whole mechanism, so write it yourself.

<!-- learn -->
```sh
sed -i.bak 's/^profile: ui$/profile: api/' .slopstopper.yml && rm .slopstopper.yml.bak
slopstopper profile show
```

```
  Profile: api  (from .slopstopper.yml)
      An HTTP API: JSON/gRPC endpoints with no browser-rendered surface.

  Disabled workflows (9):
    · ss-reliability-accessibility-check.yml     (profile)
    · ss-reliability-broken-links-check.yml      (profile)
    · ss-reliability-core-web-vitals.yml         (profile)
    · ss-reliability-e2e-check.yml               (profile)
    · ss-reliability-llms-txt-check.yml          (profile)
    · ss-reliability-robots-txt-check.yml        (profile)
    · ss-reliability-seo-check.yml               (profile)
    · ss-reliability-sitemap-check.yml           (profile)
    · ss-reliability-smoke-tests.yml             (profile)
```

The four API checks are back, because the `api` profile keeps them,
and the nine browser checks are gone. On a real repo the next
`install.sh` run deletes those nine workflow files and the deploy
trigger stops dispatching them; `slopstopper profile disabled` prints
the same list one per line, which is what both of them read.

### 5. Keep one of them

An API that serves its own docs pages still wants the link check.

<!-- learn -->
```sh
python3 - <<'PY'
import pathlib
path = pathlib.Path(".slopstopper.yml")
text = path.read_text()
path.write_text(text.replace("workflows:\n  disabled: []", "workflows:\n  disabled: []\n  enabled: [ss-reliability-broken-links-check.yml]"))
PY
slopstopper profile show
```

```
  Profile: api  (from .slopstopper.yml)
      An HTTP API: JSON/gRPC endpoints with no browser-rendered surface.

  Disabled workflows (8):
    · ss-reliability-accessibility-check.yml     (profile)
    …
    · ss-reliability-smoke-tests.yml             (profile)

  Re-enabled by workflows.enabled despite the profile:
    · ss-reliability-broken-links-check.yml
```

The arithmetic is one line in the CLI: the profile's set, minus
`workflows.enabled`, plus `workflows.disabled`. Put the config back:

<!-- learn -->
```sh
git checkout .slopstopper.yml
```

### 6. Find the pin

<!-- learn -->
```sh
grep -A3 '^\[tools\]' mise.toml
```

```
[tools]
"task" = "3"
"node" = "20"
```

This repo is the CLI, so its `mise.toml` pins only `task` and `node`
and the workflows install the CLI from source. An adopter's `mise.toml`
carries a third line, `"pipx:slopstopper-cli" = "<the version the
installer recorded>"`, and that one line is what both a laptop and CI
install, per directory, so the active `slopstopper` always matches the
repo you are in. A plain `install.sh` re-run never bumps it; the
installer prints a nudge when it is behind PyPI, and
`install.sh --upgrade-cli` (or `--cli-version X.Y.Z`) is the one
command that moves it, by wrapping `mise use`.

## Checkpoint

<!-- learn -->
```sh
slopstopper profile show | grep 'Profile: ui'
```

```
  Profile: ui  (from .slopstopper.yml)
```

## Exercise

How many workflows does the `library` profile drop, and which hygiene
check is among them?

<details>
<summary>Solution</summary>

```sh
slopstopper profile expand library | wc -l
slopstopper profile expand library | grep hygiene
```

Fifteen: the nine browser checks, DAST, CSP exceptions and the four API
checks. The hygiene one is `ss-hygiene-openapi-check.yml`, because
drift means the spec against the live API it documents, and a library
serves nothing. What remains for a library is the static-analysis
layer: complexity, the docs checks, secrets, SAST and dependencies,
which is the whole of what applies to code nothing serves.

</details>

## Going further

- [Profiles](../architecture/PROFILES.md): the mapping, the design
  decisions and why DAST scans an API through ZAP's OpenAPI mode
- [Upgrade the pinned CLI](../runbooks/UPGRADE_CLI.md): how the pin
  behaves and the recommended flow for moving it
- [Adopting slopstopper](../runbooks/INSTALL.md) for what a refresh
  overwrites and what it never touches

<details>
<summary>Episode script</summary>

**Length.** 7 to 9 minutes.

**Cold open (0:00).** An API repo's pull request: nine red browser
checks, every one of them auditing nothing.

**Talking points.**

1. Why: a check that cannot apply is noise, and noise is how gates get
   ignored; a profile only subtracts.
2. `show`, `detect`, `list`: what this repo resolves to and why each
   line is off.
3. Switch to `api`; nine gone, four back; what the installer and the
   deploy trigger read.
4. The escape hatch; the one-line arithmetic.
5. The pin in `mise.toml`; per directory; moved by one command.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/19.tape`. Zoom on "(profile, no API detected)" and
on "Re-enabled by workflows.enabled".

**Chapters.** `0:00 Why` · `1:00 show, detect, list` ·
`3:00 Switch` · `4:30 Keep one` · `6:00 The pin` · `7:30 Next lesson`.

</details>
