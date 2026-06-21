# slopstopper-cli

The SlopStopper quality suite, packaged as a Python CLI on PyPI.

> **Status: Beta.** Every check in the [public catalogue](https://slopstopper.dev/features.html) runs through this package. The CI workflows under `.github/workflows/ss-*.yml` install the pinned `slopstopper-cli` via `jdx/mise-action` and call `slopstopper run <category>:<check>` — same code path you use locally.

## Install

Quick standalone try (unpinned):

```bash
pipx install slopstopper-cli
slopstopper --version
slopstopper checks list
slopstopper doctor
```

> Published to PyPI on every release tag. `pipx upgrade slopstopper-cli` pulls the latest. Each release is also attached to the [latest GitHub Release](https://github.com/hungovercoders/slopstopper/releases/latest) with a Sigstore build-provenance attestation — verify with `gh attestation verify <wheel> --owner hungovercoders`.

Pinned suite (a repo you'll keep — local and CI run the same version):

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

> Requires [mise](https://mise.jdx.dev). `install.sh` pins `slopstopper-cli` + `task` in `mise.toml` (the single source of truth both local runs and CI read) and seeds the `ss-*.yml` workflows. Move the pin with `install.sh --upgrade-cli` / `--cli-version`.

Development (editable, from a clone of this repo):

```bash
pip install -e ./cli
slopstopper run hygiene:docs-size
```

## CLI surface

```text
slopstopper run <category>:<check>             # run a check, write reports under .ss/reports/
slopstopper emit <c>:<n> --target {pr-comment,issue}
slopstopper discover <check> --event <e>       # resolve pages.<check> from sitemap / changed / list
slopstopper config get <key> [<default>]       # read .slopstopper.yml
slopstopper templates {list, path <n>, eject <n>}   # inspect / customise bundled templates
slopstopper serve                              # bundled static server (auto-detects worker/headers.json)
slopstopper checks list [--category <c>] [--json]
slopstopper doctor                             # verify external tools are installed
slopstopper --quiet …                          # suppress decorative output (CI logs)
```

`slopstopper` with no args prints a banner of the commands above plus a quick-start block.

## Run the tests

```bash
# From the repo root:
task -t cli/Taskfile.yml test

# Or from cli/:
task test

# Filter to a single test:
task -t cli/Taskfile.yml test -- -k docs_size
```

The same `task test` target is what CI runs (see [`.github/workflows/ci-cli.yml`](../.github/workflows/ci-cli.yml)), so local and CI invocations stay in sync. The Taskfile creates and reuses a project-local venv at `cli/.venv/` (gitignored) so it doesn't conflict with system Python under PEP 668.

This workflow is slopstopper-internal — it is **not** part of the distributed `ss-*-check.yml` suite and is never seeded into adopter repos.

## Layout

- `slopstopper/cli.py` — argparse dispatcher + bare-invocation banner
- `slopstopper/output.py` — shared formatters (running / success / warn / error / footer / `--quiet`)
- `slopstopper/config.py` — `.slopstopper.yml` reader (stdlib-only YAML subset)
- `slopstopper/templates.py` — bundled-template resolver + `templates {list, path, eject}` API
- `slopstopper/emit.py` — `gh` CLI wrapper for PR comment + main-branch issue emission
- `slopstopper/discovery.py` — pages-to-audit resolver for reliability checks
- `slopstopper/checks/` — one module per check; registry in `__init__.py`
- `slopstopper/data/` — bundled Playwright specs, lighthouserc dev/prod, server.js

## Adding a check

1. Add `slopstopper/checks/<name>.py` exposing `run(args) -> int`. Start the module docstring with a one-line summary (`slopstopper checks list` reads it).
2. Register it in `slopstopper/checks/__init__.py`'s `REGISTRY` dict.
3. Write the report to `.ss/reports/<category>/<name>-report.md` in the CWD.
4. Use `from slopstopper import output` for any user-facing print calls so `--quiet` and the consistent visual language come for free.
5. If the check should be postable to a PR or issue, declare a `META` dict in the module — `emit.py` reads it.

## Skills for agents

The trio under [`.claude/skills/slopstopper-{install,update,triage}/SKILL.md`](../.claude/skills/) is the long-form playbook for Claude Code agents working with this CLI. Update them when you add or rename a check, env var, or `task ss:*` target.

## Acknowledgements

slopstopper-cli ships with no third-party Python dependencies — every check invokes its tool via `subprocess` only. Full credit, licences and upstream links for every tool we drive live in [`ATTRIBUTIONS.md`](../ATTRIBUTIONS.md).

## License

MIT — see [LICENSE](./LICENSE).
