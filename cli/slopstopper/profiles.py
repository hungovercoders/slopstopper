"""Project-shape profiles — presets over `workflows.disabled`.

Not every check applies to every repo. The eight browser-and-SEO
reliability checks (smoke, accessibility, Core Web Vitals, SEO, broken
links, llms.txt, robots.txt, sitemap) assume HTML, a DOM and a public
web surface. On an HTTP API they don't no-op — they build, serve and
audit nothing, and go red. On a library there is nothing to serve at
all.

A profile is a named preset that says which workflows a repo of that
shape should not carry:

    # .slopstopper.yml
    profile: api

The mapping lives in `data/profiles.json` so `install.sh` can read the
same file with python3 and delete the same workflows at install time —
one source of truth, two readers.

Profiles only ever SUBTRACT, and explicit config always wins:

    effective = (profile.disables − workflows.enabled) ∪ workflows.disabled

so `workflows.enabled` is the escape hatch for a repo that wants back
one check its profile drops (an API that does serve a docs site and
wants broken-links, say). An unset `profile:` resolves to the default
(`ui`, which disables nothing), so existing installs are unaffected.

Configuration (.slopstopper.yml):

    profile: ui           # ui | api | library (default: ui)
    workflows:
      disabled: []        # adds to the profile's set
      enabled: []         # removes from the profile's set
"""

from __future__ import annotations

import json
from pathlib import Path

from slopstopper import config

PROFILES_PATH = Path(__file__).resolve().parent / "data" / "profiles.json"

# Fallback used only if the package data file is unreadable — a broken
# install should behave like `ui` (disable nothing) rather than silently
# switching checks off.
_FALLBACK = {"default": "ui", "profiles": {"ui": {"summary": "", "detail": "", "disables": []}}}

_cache: dict | None = None


# ── data access ──────────────────────────────────────────────────


def load() -> dict:
    """Parsed data/profiles.json, cached. Falls back to a `ui`-only table."""
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache = _FALLBACK
    return _cache


def reload() -> None:
    """Drop the cached table (tests)."""
    global _cache
    _cache = None


def names() -> list[str]:
    """Profile names, default first then the rest alphabetically."""
    table = load()
    default = table.get("default", "ui")
    rest = sorted(n for n in table.get("profiles", {}) if n != default)
    return ([default] if default in table.get("profiles", {}) else []) + rest


def default_name() -> str:
    return str(load().get("default", "ui"))


def describe(name: str) -> dict | None:
    """The `{summary, detail, disables}` entry for a profile, or None."""
    return load().get("profiles", {}).get(name)


def expand(name: str) -> list[str] | None:
    """Workflow filenames the named profile disables, or None if unknown."""
    entry = describe(name)
    if entry is None:
        return None
    return [str(w) for w in entry.get("disables", [])]


# ── active profile + effective disabled set ──────────────────────


def active_name() -> str:
    """The repo's profile from .slopstopper.yml, or the default if unset.

    An unrecognised name resolves to the default rather than raising —
    a typo should not quietly disable a different set of checks. The
    caller-facing warning lives in `validate()`.
    """
    raw = config.get("profile")
    name = str(raw).strip() if raw else ""
    return name if describe(name) else default_name()


def validate() -> str | None:
    """Error message if `profile:` names something unknown, else None."""
    raw = config.get("profile")
    if not raw:
        return None
    name = str(raw).strip()
    if describe(name):
        return None
    return (
        f"unknown profile {name!r} in .slopstopper.yml — "
        f"expected one of: {', '.join(names())}. Falling back to {default_name()!r}."
    )


def _config_list(key: str) -> set[str]:
    """A `workflows.*` list from config, normalised to `.yml` filenames."""
    raw = config.get(key, [])
    if not isinstance(raw, list):
        return set()
    out = set()
    for item in raw:
        name = str(item).strip()
        if not name:
            continue
        out.add(name if name.endswith(".yml") else f"{name}.yml")
    return out


def effective_disabled() -> set[str]:
    """Workflow filenames this repo should not carry.

    (profile.disables − workflows.enabled) ∪ workflows.disabled

    `enabled` cancels the *profile's* contribution only. Listing the same
    workflow under both `disabled` and `enabled` is a contradiction, and
    the explicit disable wins: it's the adopter's direct instruction about
    this repo, where `enabled` is only a correction to a preset.
    """
    from_profile = set(expand(active_name()) or [])
    return (from_profile - _config_list("workflows.enabled")) | _config_list("workflows.disabled")


# ── check → workflow mapping ─────────────────────────────────────
#
# Most check keys derive from their workflow filename by convention
# (`hygiene:complexity` → ss-hygiene-complexity-check.yml), but four
# don't, so the map is explicit and curated. Deriving by convention
# silently failed to match those four, which meant `slopstopper doctor`
# never skipped a tool for a disabled check that happened to be one of
# them (trivy for security:vulnerability:all, for instance).

CHECK_WORKFLOWS: dict[str, str] = {
    "hygiene:complexity": "ss-hygiene-complexity-check.yml",
    "hygiene:csp-exceptions": "ss-hygiene-csp-exceptions-check.yml",
    "hygiene:docs-accuracy": "ss-hygiene-docs-accuracy-check.yml",
    "hygiene:docs-size": "ss-hygiene-docs-size-check.yml",
    "hygiene:docs-structure": "ss-hygiene-docs-structure-check.yml",
    "hygiene:entry-files": "ss-hygiene-entry-files-check.yml",
    "reliability:accessibility": "ss-reliability-accessibility-check.yml",
    "reliability:broken-links": "ss-reliability-broken-links-check.yml",
    "reliability:cwv": "ss-reliability-core-web-vitals.yml",
    "reliability:llms-txt": "ss-reliability-llms-txt-check.yml",
    "reliability:robots-txt": "ss-reliability-robots-txt-check.yml",
    "reliability:seo": "ss-reliability-seo-check.yml",
    "reliability:sitemap": "ss-reliability-sitemap-check.yml",
    "reliability:smoke": "ss-reliability-smoke-tests.yml",
    "security:dast": "ss-security-dast-check.yml",
    "security:sast": "ss-security-sast-check.yml",
    "security:secrets": "ss-security-secrets-check.yml",
    "security:vulnerability:all": "ss-security-vulnerability-all-check.yml",
}


def workflow_for(check_name: str) -> str | None:
    """The workflow filename that fronts a check, or None if unmapped."""
    return CHECK_WORKFLOWS.get(check_name)


def check_is_disabled(check_name: str, disabled: set[str] | None = None) -> bool:
    """True if the workflow fronting `check_name` is in the disabled set."""
    workflow = workflow_for(check_name)
    if workflow is None:
        return False
    if disabled is None:
        disabled = effective_disabled()
    return workflow in disabled


# ── shape detection (advisory only) ──────────────────────────────
#
# `install.sh` and the install skill use this to SUGGEST a profile. It
# never picks one: a curl-piped install is non-interactive, and a wrong
# silent pick (checks quietly off) is worse than the default superset
# (checks visibly red). When signals conflict, UI wins — the superset
# errs toward running a check rather than skipping it.

_UI_MARKERS = (
    "astro.config.*",
    "next.config.*",
    "nuxt.config.*",
    "svelte.config.*",
    "remix.config.*",
    "gatsby-config.*",
    "angular.json",
    "hugo.toml",
    "_config.yml",
    "index.html",
    "public/**/*.html",
    "static/**/*.html",
    "app/**/*.html",
    "src/**/*.html",
    "site/**/*.html",
    "web/**/*.html",
)

_API_MARKERS = (
    "openapi.yaml",
    "openapi.yml",
    "openapi.json",
    "swagger.yaml",
    "swagger.yml",
    "swagger.json",
    "api/openapi.*",
    "docs/openapi.*",
    "spec/openapi.*",
    "proto/**/*.proto",
)

_MANIFESTS = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "setup.py",
)

# Dependency names that give the repo's shape away. Matched as substrings
# against the raw manifest text — crude, but a manifest is small and this
# only feeds a suggestion.
_UI_DEPS = (
    "astro",
    '"next"',
    "nuxt",
    "svelte",
    "react-dom",
    '"vue"',
    "@angular/core",
    "gatsby",
    "@remix-run",
    "@11ty/eleventy",
    "tailwindcss",
)

_API_DEPS = (
    "fastapi",
    "starlette",
    "uvicorn",
    "flask",
    "djangorestframework",
    "sanic",
    "aiohttp",
    "grpcio",
    "connexion",
    '"express"',
    "fastify",
    '"koa"',
    "@nestjs/core",
    "@hapi/hapi",
    "gin-gonic",
    "labstack/echo",
    "actix-web",
    '"axum"',
    "spring-boot-starter-web",
)


def _first_match(root: Path, patterns: tuple[str, ...]) -> str | None:
    """First path under `root` matching any glob, as a repo-relative string."""
    for pattern in patterns:
        for hit in root.glob(pattern):
            parts = set(hit.parts)
            if parts & {"node_modules", ".git", "dist", "build", ".ss", "coverage"}:
                continue
            return str(hit.relative_to(root))
    return None


def _manifest_texts(root: Path) -> list[tuple[str, str]]:
    """(filename, lowercased text) for each dependency manifest at the root."""
    out = []
    for name in _MANIFESTS:
        path = root / name
        if not path.is_file():
            continue
        try:
            out.append((name, path.read_text(encoding="utf-8", errors="replace").lower()))
        except OSError:
            continue
    return out


def _dep_match(manifests: list[tuple[str, str]], deps: tuple[str, ...]) -> str | None:
    """`<manifest> declares <dep>` for the first manifest/dep hit."""
    for filename, text in manifests:
        for dep in deps:
            if dep.lower() not in text:
                continue
            label = dep.strip('"')
            return f"{filename} declares {label}"
    return None


def detect(root: Path | None = None) -> tuple[str, str]:
    """Suggest a profile for the repo at `root`. Returns (name, reason).

    Advisory: the caller prints this, it does not apply it.
    """
    root = Path(root) if root is not None else Path(".")
    manifests = _manifest_texts(root)

    ui_hit = _first_match(root, _UI_MARKERS) or _dep_match(manifests, _UI_DEPS)
    if ui_hit:
        return "ui", f"found {ui_hit}"

    api_hit = _first_match(root, _API_MARKERS) or _dep_match(manifests, _API_DEPS)
    if api_hit:
        return "api", f"found {api_hit}"

    if manifests:
        return "library", f"found {manifests[0][0]} but no web or API surface"

    return default_name(), "no clear signal — defaulting to the full check set"
