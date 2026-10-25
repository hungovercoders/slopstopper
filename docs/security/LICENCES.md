# Licence Inventory

`security:licences` judges every dependency the lockfiles resolve to
against the repo's licence allowlist, so a transitive package under a
denied licence cannot sit in the tree unnoticed. It is the full-tree
companion to the dependency review, which judges only what each PR adds.

## Quick Start

```bash
task ss:security:licences        # the whole resolved tree, against the policy
cat .ss/reports/licences/licences-report.md
```

## What it reads

| Ecosystem | Source of the tree | Needs |
| --------- | ------------------ | ----- |
| npm | `package-lock.json` (lockfile version 2 or 3), at the root or one directory down | nothing installed: the lockfile records each package's `license` |
| Python | `python3 -m pip inspect` of the interpreter the project is installed into | the project's dependencies installed there (a `.venv/` beside `pyproject.toml` or `requirements.txt` is used first, then `python3` on PATH) |

`yarn.lock` and `pnpm-lock.yaml` carry no licence data and are reported
as not judged. A repo with no manifest at all passes with nothing to say.

By default npm `devDependencies` are not judged, the same scope the
dependency review fails on: they build and test the project and never
ship, so their licences impose no obligation on what does. Set
`security.licences.include_dev: true` to judge them too.

## The policy

`.github/dependency-review-config.yml`, which `install.sh` seeds, is the
one policy file. Its `allow-licenses` (or `deny-licenses`) list is the
rule and its `allow-dependencies-licenses` purls are the exemptions:

```yaml
allow-dependencies-licenses:
  # Build-time image library under the LGPL; the shipped site never links it.
  - pkg:npm/@img/sharp-libvips-linux-x64
  - pkg:pypi/some-package
```

A licence is judged as an SPDX expression (`MIT`, `(MIT OR Apache-2.0)`,
`GPL-2.0-only WITH Classpath-exception-2.0`). Common free-text names in
Python metadata (`Apache License 2.0`, `3-Clause BSD License`) are read
as their SPDX id. Anything else, and a package that states no licence,
is **reported as unknown and never fails the run**, which is also how
the dependency review treats a licence it cannot detect. The report
lists them so a reader can look.

## Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | every judged licence is on the allowlist, or there was nothing to inventory |
| 1 | at least one package carries a licence outside the policy; the report names each |
| 2 | no policy file; a version-1 `package-lock.json` (no licence data; rewrite it with npm 7+); `pip inspect` missing (pip 22.2+); or a Python manifest whose declared dependencies are not installed in the inspected interpreter |

The last case is deliberate: an empty environment must never read as a
clean tree. In CI the workflow installs a root-level `requirements.txt`
or `pyproject.toml` into the job's Python first; a project one directory
down adds its own `pip install` step to the workflow.

## Configuration

```yaml
security:
  licences:
    policy: .github/dependency-review-config.yml
    include_dev: false
    python: python3     # or a path, e.g. cli/.venv/bin/python
```

## When it fails

1. Read the report's "Outside the allowlist" table: package, version,
   ecosystem, licence.
2. If the package should go, replace it. If its licence is acceptable
   for this project, add its purl to `allow-dependencies-licenses` with
   a comment saying why; the dependency review honours the same line.
3. If the policy itself is wrong for the project, edit
   `allow-licenses`; both checks move together.

## Files

- `cli/slopstopper/checks/licences.py`, the check (stdlib only)
- `.github/workflows/ss-security-licences-check.yml`, the workflow
- `.ss/reports/licences/licences-report.{md,json}`, the reports
- [VULNERABILITY.md](VULNERABILITY.md), the division of labour with the
  dependency review, Trivy and Dependabot
