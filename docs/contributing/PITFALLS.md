# Common pitfalls when extending SlopStopper

A short list of the most-hit gotchas. Each one has bitten somebody
before; the rule is "do the obvious thing the obvious way."

## Quality checks

- **Adding a quality check workflow but forgetting to add a matching
  Task target.** CI and local diverge — contributors can't reproduce
  the failure. Every workflow that runs a check must invoke
  `task ss:<category>:<action>`; the same target must exist in
  [`Taskfile.ss.yml`](../../Taskfile.ss.yml).
- **Putting analysis output anywhere other than under
  `.ss/reports/<category>/`.** It won't be `.gitignore`d and could
  pollute the consumer's repo when they install SlopStopper.
- **Invoking `task hygiene:complexity` (or any task) without the `ss:`
  prefix.** "Task not found" — all SlopStopper tasks live under the
  `ss` namespace via the root `Taskfile.yml`'s `includes:` block. Use
  `task ss:hygiene:complexity`.

## Workflows

- **Creating a new workflow file without the `ss-` prefix.** It won't
  get grouped with the rest in the Actions UI, and consumers risk a
  clash when they install. Always name new workflows
  `ss-<category>-<action>.yml`. The single exception is
  `copilot-setup-steps.yml`, whose name is fixed by the platform.

## CSP and headers

- **Adding any external resource.** CSP blocks it silently in
  production; test in DevTools first. If the resource is genuinely
  required, open a per-path exception in
  [`app/_headers`](../../app/_headers) and document it
  in [`docs/security/CSP_EXCEPTIONS.md`](../security/CSP_EXCEPTIONS.md)
  — the `ss:hygiene:csp-exceptions` check fails the build if they
  drift apart.

## Site (`app/`)

- **Editing `app/index.html` but forgetting `aria-current="page"` on
  the active nav link.** Accessibility regression — axe-core catches
  it on every PR.
- **Tweaking `--accent` to use it as text colour.** AA contrast fail.
  Use `--accent-deep` for text on light backgrounds, `--accent` for
  decorative shapes only.
- **Adding to one HTML page's header but not the other two.** There
  is no build step or SSI — nav drifts. Change one, change all
  three.
