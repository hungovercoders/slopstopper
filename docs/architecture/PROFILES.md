# Project-shape profiles

Not every check applies to every repo. The nine browser-and-SEO reliability
checks (smoke, E2E, accessibility, Core Web Vitals, SEO, broken links, llms.txt,
robots.txt, sitemap) assume HTML, a DOM and a public web surface. On an HTTP API
they don't quietly no-op. They build, serve and audit nothing, and go red. On a
library there is nothing to serve at all.

A **profile** is a named preset for `workflows.disabled`: it says which
workflows a repo of that shape shouldn't carry.

| Profile | Shape | Drops |
| ------- | ----- | ----- |
| `ui` (default) | Serves HTML to a browser | Nothing, because every check applies |
| `api` | JSON/gRPC endpoints, no browser surface | The nine browser-and-SEO checks. Keeps the four API checks (api-health, api-latency, api-headers, OpenAPI drift), CSP exceptions (APIs still set response headers) and DAST, via ZAP's OpenAPI mode |
| `library` | Library, CLI or package; nothing deployed | The nine above, plus DAST, CSP exceptions and the four API checks, which is everything that needs a URL |

**DAST scans an API through ZAP's OpenAPI mode.** The default scan is ZAP's
*baseline*, which spiders a site from a root URL. That is right for an HTML
surface and useless against a JSON API, which exposes no links to crawl.
Setting `api.openapi.spec` switches the check to ZAP's API scan (`-f openapi`),
which reads the spec and exercises the operations it declares. The scanned URL
is passed as ZAP's `-O` host override, so a spec whose `servers` block names
production can be run against a preview environment.

Until a spec is configured the check skips rather than scanning nothing, under
the same "unconfigured is not failing" contract as the other API checks. The
workflow branches the same way: with a spec it audits a resolved URL
(`urls.preview` on PRs, `urls.production` on main), and without one it keeps
the original path of building the repo and serving it on `localhost:8080`.

```bash
bash install.sh --profile api      # writes `profile: api` into .slopstopper.yml
slopstopper profile show           # what this repo resolves to, and why
slopstopper profile detect         # suggest one from the repo's contents
slopstopper profile list           # the full mapping
```

## Design decisions

**The config is the home, not the flag.** `--profile` writes `profile:` into
`.slopstopper.yml` and the installed workflow set is derived from that key on
every run. The choice has to survive a re-run and be visible in review. That is
the same reasoning as `workflows.disabled` itself, which exists so opting out
isn't "delete the file and trust the marker".

**A preset over the existing mechanism, not new machinery.** A profile expands
into the same disabled set that `workflows.disabled` already fed, resolved in
one place ([`profiles.effective_disabled()`](../../cli/slopstopper/profiles.py)):

```
effective = (profile.disables − workflows.enabled) ∪ workflows.disabled
```

So `slopstopper doctor` skipping a missing tool, `install.sh` deleting a
workflow, and `slopstopper badges` (which globs what's on disk) all follow from
the profile without knowing it exists. `workflows.enabled` is the escape hatch:
an API that does serve a docs site can list `ss-reliability-broken-links-check.yml`
and keep that one check. A profile only ever subtracts.

**One mapping, two readers.** The profile → workflow table lives in
[`cli/slopstopper/data/profiles.json`](../../cli/slopstopper/data/profiles.json).
The CLI reads it through `slopstopper.profiles`; `install.sh` imports that same
module from the source tree with `python3` (a hard prereq) rather than requiring
the installed wheel, so the installer can resolve the workflow set before the
mise/CLI step has run and there's no bash-side copy of the mapping to drift.

**Detection suggests, never applies.** `slopstopper profile detect` sniffs for
framework configs, HTML, OpenAPI specs and server-framework dependencies, and
`install.sh` prints the suggestion when it differs from the active profile. It
never writes the key: a curl-piped install is non-interactive, and a wrong
silent pick (checks quietly off) is worse than the default superset (checks
visibly red). When signals conflict, UI wins for the same reason.

**Profiles made `api` quiet before they made it covered.** Subtraction removes
checks that don't apply; it doesn't add the ones that should. The API-shaped
analogues were a separate increment, not a gap in the mechanism, and have all
landed: smoke → [api-health](../reliability/README.md#api-health-check), Core
Web Vitals → [api-latency](../reliability/README.md#api-latency-check), CSP
exceptions → [api-headers](../security/API_HEADERS.md), docs-accuracy →
[openapi](../hygiene/README.md#openapi-drift), DAST's spider → [its OpenAPI
scan mode](../security/DAST.md). Each is inert until configured, so all five
ship under `ui` too. Out of reach: detecting *undocumented* routes, which needs
framework-specific route introspection.
