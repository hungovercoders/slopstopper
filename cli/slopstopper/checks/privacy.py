"""Privacy statement check.

A site hosted somewhere that keeps traffic data has a privacy statement
to make, even with no cookies and no analytics script: the host processes
every visitor's IP, and every third-party origin the CSP lets a page reach
sees it too. Three hungovercoders sites turned out to have no statement
at all (#537); this check keeps a repo from shipping that gap again.

It applies to a repo with a browser-rendered surface (the `ui` profile)
and evidence of a host that keeps traffic data: a Cloudflare wrangler
config (root or one directory down), `netlify.toml`, `vercel.json`, or
`urls.production` set. It is a no-op for the `api` and `library`
profiles, which drop its workflow, and a graceful skip with no host
evidence.

Rules, each reported with what to add and where:

  1. A privacy page exists: `privacy.page` when set, else the first file
     named `privacy.<ext>` or `privacy/index.<ext>` outside dependency
     and build directories.
  2. The page names the host (Cloudflare, Netlify or Vercel, from the
     config file found) and every name in `privacy.hosts`.
  3. When the wrangler config turns Workers Logs on
     (`observability.enabled: true`), the page mentions logs.
  4. Every third-party origin a fetch directive in the CSP source allows
     (`headers.source`, the same parse as `hygiene:csp-exceptions`) is
     named on the page: its hostname, or any label of it that identifies
     a service (`cdnjs` or `cloudflare` for cdnjs.cloudflare.com, `giscus`
     for giscus.app, `google` for fonts.gstatic.com).
  5. The page carries a date (ISO or long form), so a stale statement
     shows its age.

The matching smoke-test rule, that every audited page links to it, is
`SMOKE_PRIVACY_URL` in the smoke spec; `page_url()` below derives it and
is None whenever this check would not run (profile, no host evidence,
opt-out), so the smoke rule never applies where the check does not.

Configuration (.slopstopper.yml):

    privacy:
      page: auto            # repo path of the statement; '' opts out visibly
      url: auto             # where it is served; smoke asserts every page links it
      require_link: true    # false drops that smoke assertion
      hosts: []             # extra names the page must carry

Exit codes:
  0: passed, opted out, no host evidence, or the profile disables it
  1: no page, or the page misses a required name, the logs mention or a date
  2: arguments were passed (this check takes none)
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from pathlib import Path

from slopstopper import config, headers_adapters, output, profiles
from slopstopper.checks._contract import reject_extra_args

CHECK_NAME = "hygiene:privacy"
REPORT_DIR = Path(".ss/reports/privacy")
REPORT_JSON = REPORT_DIR / "privacy-report.json"
REPORT_MD = REPORT_DIR / "privacy-report.md"

# Consumed by `slopstopper emit hygiene:privacy --target {pr-comment,issue}`.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "🔏 Privacy Statement",
    "issue_title": "🔏 Privacy statement issues",
    "issue_labels": ["privacy", "hygiene"],
    "issue_followup": "🔔 Privacy statement issues detected again in commit",
    "issue_close_comment": "✅ The privacy statement matches the site's configuration again on `main`. Closing automatically.",
}

PAGE_EXTENSIONS = ("html", "htm", "md", "mdx", "astro", "njk", "liquid", "hbs", "ejs", "vue", "svelte")
PAGE_CANDIDATES = tuple(f"privacy.{ext}" for ext in PAGE_EXTENSIONS) + tuple(
    f"privacy/index.{ext}" for ext in PAGE_EXTENSIONS
)
SKIP_DIRS = {
    "node_modules", ".git", ".ss", "dist", "build", ".next", ".astro", "out", ".venv",
    "_site", ".svelte-kit", ".nuxt", ".output", ".vercel", ".netlify", "coverage", "target", "vendor",
}

# Host evidence: the config file a host reads, and what the page must call it.
HOST_FILES: tuple[tuple[str, str], ...] = (
    ("wrangler.jsonc", "Cloudflare"),
    ("wrangler.json", "Cloudflare"),
    ("wrangler.toml", "Cloudflare"),
    ("netlify.toml", "Netlify"),
    ("vercel.json", "Vercel"),
)

# The CSP directives that make the browser fetch from an origin, so a
# third party listed there sees the visitor's IP.
FETCH_DIRECTIVES = {
    "default-src", "script-src", "script-src-elem", "script-src-attr", "connect-src",
    "frame-src", "child-src", "img-src", "style-src", "style-src-elem", "style-src-attr",
    "font-src", "media-src", "object-src", "worker-src", "manifest-src", "prefetch-src",
}
# Labels that don't identify a service, so `api.github.com` is known by `github`.
GENERIC_LABELS = {"www", "api", "cdn", "static", "assets", "fonts", "js", "css", "img", "images", "media", "s", "m", "app", "apps", "edge"}
# Service hostnames whose labels never say who runs them.
SERVICE_ALIASES = {"gstatic": "google", "googleapis": "google", "googletagmanager": "google", "google-analytics": "google", "ggpht": "google"}

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(
    rf"\b\d{{4}}-\d{{2}}-\d{{2}}\b|\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTHS})\s+\d{{4}}\b|\b(?:{MONTHS})\s+\d{{1,2}},?\s+\d{{4}}\b",
    re.I,
)
LOGS_RE = re.compile(r"\blogs?\b|\blogging\b", re.I)


# ── repo evidence ───────────────────────────────────────────────────


def _source_files(root: Path) -> list[Path]:
    """Every file under the root, pruning dependency and build directories
    so a page only in `dist/` is not mistaken for the source."""
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        out.extend(Path(dirpath) / f for f in filenames)
    return out


def _host_config(root: Path) -> tuple[Path, str] | None:
    """The first host config file at the root or one directory down."""
    for depth in (root, *sorted(p for p in root.iterdir() if p.is_dir() and p.name not in SKIP_DIRS)):
        for name, host in HOST_FILES:
            candidate = depth / name
            if candidate.is_file():
                return candidate, host
    return None


def _string_end(text: str, i: int) -> int:
    """Index just past the string that opens at `i`, honouring escapes."""
    i += 1
    while i < len(text) and text[i] != '"':
        i += 2 if text[i] == "\\" else 1
    return i + 1


def _comment_end(text: str, i: int) -> int:
    """Index just past the comment that opens at `i`, or -1 if none does."""
    if text.startswith("//", i):
        nl = text.find("\n", i)
        return len(text) if nl < 0 else nl
    if text.startswith("/*", i):
        close = text.find("*/", i + 2)
        return len(text) if close < 0 else close + 2
    return -1


def _trailing_comma(text: str, i: int) -> bool:
    j = i + 1
    while j < len(text) and text[j] in " \t\r\n":
        j += 1
    return j < len(text) and text[j] in "}]"


def _strip_jsonc(text: str) -> str:
    """JSONC to JSON: comments and trailing commas go, string contents stay
    (a URL's `//` or a quote inside a comment must not confuse it)."""
    out: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == '"':
            end = _string_end(text, i)
            out.append(text[i:end])
            i = end
            continue
        skip_to = _comment_end(text, i)
        if skip_to >= 0:
            i = skip_to
            continue
        if c != "," or not _trailing_comma(text, i):
            out.append(c)
        i += 1
    return "".join(out)


def _logs_enabled(host_config: Path) -> bool | None:
    """Whether the wrangler config turns Workers Logs on; None when the
    file cannot be parsed, so the caller can say so instead of assuming off."""
    text = host_config.read_text(encoding="utf-8", errors="replace")
    if not host_config.name.startswith("wrangler"):
        return False
    try:
        data = tomllib.loads(text) if host_config.suffix == ".toml" else json.loads(_strip_jsonc(text))
    except (ValueError, tomllib.TOMLDecodeError):
        return None
    obs = data.get("observability") if isinstance(data, dict) else None
    if not isinstance(obs, dict):
        return False
    if obs.get("enabled") is True:
        return True
    logs = obs.get("logs")
    return isinstance(logs, dict) and logs.get("enabled") is True


def _csp_rules() -> list[dict]:
    """The parsed headers source, or nothing when it is unset or unreadable."""
    source = config.get("headers.source")
    if not source:
        return []
    path = Path(str(source))
    if not path.exists():
        return []
    fmt = config.get("headers.format", "auto") or "auto"
    if fmt not in {*headers_adapters.ADAPTERS, "auto"}:
        return []
    try:
        return headers_adapters.parse(path, fmt)
    except Exception:  # noqa: BLE001 - csp-exceptions reports a bad source; here it is one input of five
        return []


def _third_party_origins(rules: list[dict]) -> set[str]:
    origins: set[str] = set()
    for rule in rules:
        csp = rule.get("csp")
        if not csp:
            continue
        for directive in csp.split(";"):
            tokens = directive.split()
            if not tokens or tokens[0].lower() not in FETCH_DIRECTIVES:
                continue
            origins.update(headers_adapters.csp_origins(" ".join(tokens)))
    return origins


def _hostname(origin: str) -> str:
    host = re.sub(r"^https?://", "", origin).split("/")[0].split(":")[0].lower()
    return host.removeprefix("*.")


def _service_names(hostname: str) -> list[str]:
    """The words a page can use for a hostname: every label that is not
    generic and not the TLD, plus the operator an alias names. The first is
    the most specific (`cdnjs` before `cloudflare`)."""
    labels = hostname.split(".")[:-1]
    names = [label for label in labels if label not in GENERIC_LABELS] or labels[:1]
    names += [SERVICE_ALIASES[n] for n in names if n in SERVICE_ALIASES]
    return names


def _short_name(hostname: str) -> str:
    return _service_names(hostname)[0]


# ── the page ────────────────────────────────────────────────────────


def applies(root: Path | None = None) -> bool:
    """Whether the check runs here: the profile keeps it and there is host
    evidence (a host config file or `urls.production`)."""
    if profiles.check_is_disabled(CHECK_NAME):
        return False
    root = root or Path.cwd()
    return _host_config(root) is not None or bool(config.get("urls.production"))


def resolve_page(root: Path | None = None) -> tuple[Path | None, str | None]:
    """(page, note). `privacy.page` verbatim when set; '' is an opt-out
    (page None, note says so); `auto` finds the first source candidate."""
    root = root or Path.cwd()
    configured = config.get("privacy.page", "auto")
    if configured is None or str(configured).strip() == "":
        return None, "privacy.page is empty in .slopstopper.yml, so the check is opted out"
    configured = str(configured).strip()
    if configured != "auto":
        return root / configured, None
    candidates = {c.lower() for c in PAGE_CANDIDATES}
    for path in sorted(_source_files(root)):
        rel = path.relative_to(root)
        tail = "/".join(rel.parts[-2:]).lower()
        if rel.name.lower() in candidates or tail in candidates:
            return path, None
    return None, None


def page_url(root: Path | None = None) -> str | None:
    """The URL path the statement is served at, for the smoke-test link
    assertion: `privacy.url` when set, else derived from the page's name
    (`privacy.html` → `/privacy.html`, anything else → `/privacy/`).
    None when the check does not apply here (see `applies`), when opted
    out, when there is no page, or when `privacy.require_link` is false."""
    if not config.get_bool("privacy.require_link", True) or not applies(root):
        return None
    configured = config.get("privacy.url", "auto")
    if configured and str(configured).strip() not in {"", "auto"}:
        return str(configured).strip()
    page, _note = resolve_page(root)
    if page is None:
        return None
    if page.name.lower().endswith((".html", ".htm")) and page.parent.name.lower() != "privacy":
        return f"/{page.name}"
    return "/privacy/"


def _page_text(page: Path) -> str:
    text = page.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"(?s)<script\b.*?</script>|<style\b.*?</style>", " ", text)
    return text


# ── the rules ───────────────────────────────────────────────────────


def _issue(rule: str, message: str, fix: str) -> dict:
    return {"rule": rule, "message": message, "fix": fix}


def _check_names(text: str, names: list[str], page: Path) -> list[dict]:
    low = text.lower()
    return [
        _issue("host", f"`{page}` does not name {name}", f"Say that {name} hosts the site and what it keeps (traffic statistics, request logs) in `{page}`.")
        for name in names
        if name.lower() not in low
    ]


def _check_origins(text: str, origins: set[str], page: Path) -> list[dict]:
    low = text.lower()
    issues = []
    for origin in sorted(origins):
        host = _hostname(origin)
        names = _service_names(host)
        if host in low or any(re.search(rf"\b{re.escape(n)}\b", low) for n in names):
            continue
        issues.append(_issue(
            "third-party",
            f"`{page}` does not name `{host}`, which the CSP lets pages reach",
            f"Name `{host}` (or {' / '.join(f'`{n}`' for n in names)}) in `{page}` and say what reaches it; the visitor's IP does, at least.",
        ))
    return issues


def _check_logs(text: str, logs_on: bool | None, host_config: Path, page: Path) -> list[dict]:
    if logs_on is None:
        output.warn(f"{host_config} could not be parsed, so whether Workers Logs are on is unknown; the logs rule was not applied.")
        return []
    if logs_on and not LOGS_RE.search(text):
        return [_issue(
            "logs",
            f"`{host_config}` turns Workers Logs on, but `{page}` never mentions logs",
            f"Say in `{page}` that the host keeps per-request logs (IP, path, user agent) and for how long, or turn `observability.enabled` off.",
        )]
    return []


def _check_date(text: str, page: Path) -> list[dict]:
    if DATE_RE.search(text):
        return []
    return [_issue(
        "date",
        f"`{page}` carries no date",
        f"Add a 'last checked' date to `{page}` (ISO `2026-10-24` or `24 October 2026`) and move it whenever the hosting or the CSP changes.",
    )]


def _evaluate(root: Path, page: Path, host_config: tuple[Path, str] | None) -> tuple[list[dict], dict]:
    text = _page_text(page)
    names = [host_config[1]] if host_config else []
    names += [str(n) for n in (config.get("privacy.hosts", []) or [])]
    rules = _csp_rules()
    origins = _third_party_origins(rules)
    logs_on = _logs_enabled(host_config[0]) if host_config else False
    rel = page.relative_to(root) if page.is_absolute() else page
    issues = _check_names(text, names, rel)
    issues += _check_logs(text, logs_on, host_config[0].relative_to(root) if host_config else Path("-"), rel)
    issues += _check_origins(text, origins, rel)
    issues += _check_date(text, rel)
    summary = {
        "page": str(rel),
        "host": host_config[1] if host_config else None,
        "host_config": str(host_config[0].relative_to(root)) if host_config else None,
        "logs_enabled": logs_on,
        "required_names": names,
        "third_party_origins": sorted(origins),
        "url": page_url(root),
    }
    return issues, summary


# ── reports ─────────────────────────────────────────────────────────


def _build_md_report(issues: list[dict], summary: dict) -> str:
    lines = [
        "# 🔏 Privacy Statement Report",
        "",
        f"**Status:** {'❌ FAIL' if issues else '✅ PASS'}",
        "",
        f"- Statement: `{summary.get('page') or 'none found'}`" + (f" (served at `{summary['url']}`)" if summary.get("url") else ""),
        f"- Host: {summary.get('host') or 'unknown'}" + (f" (`{summary['host_config']}`)" if summary.get("host_config") else ""),
        f"- Workers Logs: {'on' if summary.get('logs_enabled') else 'off'}",
        f"- Third-party origins the CSP allows: {', '.join(f'`{o}`' for o in summary.get('third_party_origins', [])) or 'none'}",
        "",
    ]
    if not issues:
        lines += ["The statement names the host and every third party the pages reach, and carries a date.", ""]
    else:
        lines += ["## ❌ Issues", ""]
        lines += [f"- **{i['rule']}**: {i['message']}. {i['fix']}" for i in issues]
        lines.append("")
    lines += [
        "## Why this check exists",
        "",
        "A site with no cookies and no analytics still has a host that processes every visitor's IP, and every origin its CSP",
        "allows sees that IP too. The statement is only true while it matches `wrangler.*` and the headers source, so this",
        "check reads both and asks the page to say what they say. Config: the `privacy:` block in `.slopstopper.yml.example`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _write_reports(issues: list[dict], summary: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps({"summary": summary, "issues": issues}, indent=2) + "\n")
    REPORT_MD.write_text(_build_md_report(issues, summary))


def _print_results(issues: list[dict], summary: dict) -> None:
    output.status("🔏", "Privacy statement check")
    output._emit(f"   statement: {summary.get('page') or 'none'}")
    output._emit(f"   host: {summary.get('host') or 'unknown'}  ·  Workers Logs: {'on' if summary.get('logs_enabled') else 'off'}")
    output._emit(f"   third-party origins in the CSP: {len(summary.get('third_party_origins', []))}")
    output.separator()
    if not issues:
        output.success("The statement matches the site's configuration.")
        return
    for i in issues:
        output._emit(f"   ❌ {i['message']}")
        output._emit(f"      → {i['fix']}")
    output.separator()


def _missing_page(root: Path, host_config: tuple[Path, str] | None, configured: bool) -> int:
    where = "the path privacy.page names" if configured else "any of " + ", ".join(f"`{c}`" for c in PAGE_CANDIDATES[:3]) + " (any directory; see the report)"
    host = host_config[1] if host_config else "the host"
    issues = [_issue(
        "page",
        f"no privacy page found at {where}",
        f"Add one (`app/privacy.html`, `src/content/docs/privacy.md`, …) that names {host}, every third party the CSP allows, and a date; link it from every page's footer. Or set `privacy.page: ''` with a comment saying why.",
    )]
    summary = {"page": None, "host": host_config[1] if host_config else None,
               "host_config": str(host_config[0].relative_to(root)) if host_config else None,
               "logs_enabled": False, "required_names": [], "third_party_origins": [], "url": None}
    _write_reports(issues, summary)
    _print_results(issues, summary)
    output.error("No privacy statement. See .ss/reports/privacy/privacy-report.md.")
    return 1


def run(args: list[str] | None = None) -> int:
    if args:
        return reject_extra_args(CHECK_NAME, args)
    if profiles.check_is_disabled(CHECK_NAME):
        output.info("Privacy statement check: the active profile drops it (no browser-rendered surface), so skipping.")
        return 0
    root = Path.cwd()
    host_config = _host_config(root)
    if not applies(root):
        output.info("Privacy statement check: no hosting config (wrangler, netlify.toml, vercel.json) and no urls.production, so skipping.")
        return 0
    page, note = resolve_page(root)
    if note:
        output.info(f"Privacy statement check: {note}.")
        return 0
    if page is None or not page.is_file():
        return _missing_page(root, host_config, configured=page is not None)

    issues, summary = _evaluate(root, page, host_config)
    _write_reports(issues, summary)
    _print_results(issues, summary)
    if issues:
        output.error("The privacy statement does not match the site's configuration. See .ss/reports/privacy/privacy-report.md.")
        return 1
    return 0
