# Security Policy

## Supported versions

SlopStopper is a rolling release shipped from `main`. Adopters re-run
`install.sh` to pick up fixes. Only the latest `main` is supported with
security patches.

| Version | Supported |
| ------- | --------- |
| `main`  | ✅ |
| Older installs | Re-run `install.sh` to pick up patches |

## Reporting a vulnerability

**Please do not open a public issue for security bugs.**

Use [GitHub Security Advisories](https://github.com/hungovercoders/slopstopper/security/advisories/new)
to report privately. This routes the report to the maintainers and lets
us coordinate disclosure with you.

What to include:

- A clear description of the issue and the impact you can demonstrate
- Reproduction steps (a minimal example, ideally against a fork)
- The commit SHA or workflow file affected
- Any suggested mitigation

## What to expect

- **Acknowledgement** within 5 working days.
- **Triage update** within 10 working days — confirming whether it's
  in scope, an estimated severity, and a fix timeline.
- **Coordinated disclosure** once a fix has shipped to `main`. We will
  credit you in the advisory unless you ask us not to.

## Scope

In scope:

- Code in this repository (`Taskfile.ss.yml`, `.ss/scripts/`,
  `.github/workflows/ss-*.yml`, `install.sh`, the `app/` site).
- Documentation that, if followed, would lead an adopter into an
  insecure configuration.

Out of scope:

- Vulnerabilities in upstream tools (Semgrep, Trivy, ZAP, Gitleaks,
  Lizard, axe-core, Lighthouse). Please report those upstream.
- Findings produced by the suite running against adopter code — those
  belong to the adopter.
- Denial of service against `slopstopper.dev` (the demo site).

## Related docs

- [`docs/security/README.md`](./docs/security/README.md) — overview of
  what each security check does and how to extend it.
- [`docs/security/CSP_EXCEPTIONS.md`](./docs/security/CSP_EXCEPTIONS.md) —
  the scoped CSP exception pattern used by the demo site, and the
  pattern adopters should copy.
