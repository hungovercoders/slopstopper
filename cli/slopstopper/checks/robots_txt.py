"""robots.txt discoverability + de-index guard audit (in-CLI implementation).

Fetches `/robots.txt` from a live URL and asserts it is present, reachable
and does not silently sabotage discoverability. The headline assertion is
the *de-index guard*: a stray `Disallow: /` under `User-agent: *` (often
leaked from a staging config) removes an entire public site from search —
the single highest-blast-radius line a site can ship. Complements
`reliability:seo` (what human crawlers read) and `reliability:llms-txt`
(what AI assistants read); together the three form the discovery-file
triangle.

The hard-fail bar is deliberately scoped to real damage: reachable,
non-empty, no blanket `Disallow: /`, and at least one `Sitemap:` pointer.
An `Llms:` pointer and the `text/plain` content-type are advisory notes
that only fail the check when a config knob escalates them.

CLI surface:
  slopstopper run reliability:robots-txt -- --url URL [--path /robots.txt]
        [--check-links] [--require-llms] [--allow-disallow-all]

Stdlib-only (urllib). Writes .ss/reports/robots-txt/robots-txt-report.{md,json}.

Configuration (.slopstopper.yml — all optional):

    reliability:
      robots_txt:
        allow_disallow_all: false   # suppress the blanket `Disallow: /` failure
        require_llms: false          # escalate a missing `Llms:` pointer to hard-fail
        check_links: false           # HEAD-verify Sitemap:/Llms: targets resolve

Env-var equivalents the CLI also honours (precedence: flag > env > config):
  ROBOTS_TXT_TEST_URL   base URL to audit (required)
  ROBOTS_TXT_PATH       path to the file (default: /robots.txt)

See .slopstopper.yml.example for the canonical schema.

Exit codes:
  0 — robots.txt present and healthy
  1 — failures detected
  2 — the URL is missing, or its scheme is not http/https
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from slopstopper import config, output


REPORT_DIR = Path(".ss/reports/robots-txt")
REPORT_MD = REPORT_DIR / "robots-txt-report.md"
USER_AGENT = "SlopStopper-RobotsTxt-Check/1.0"
TIMEOUT_SECONDS = 15
ALLOWED_SCHEMES = ("http", "https")
DEFAULT_PATH = "/robots.txt"
PLAIN_CONTENT_TYPES = ("text/plain",)

# Consumed by `slopstopper emit reliability:robots-txt --target pr-comment`.
# No issue keys: the check's exit code fails the workflow, no
# main-branch issue is created.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "🤖 robots.txt",
}


# ── safety ───────────────────────────────────────────────────────


def _require_safe_url(url: str) -> None:
    """Reject any URL whose scheme isn't http/https (blocks file:// SSRF)."""
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"robots.txt check refuses scheme {scheme!r} (only http/https allowed). url={url!r}"
        )


def _fetch(url: str) -> tuple[int, str, str]:
    _require_safe_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # nosec B310
        return (
            resp.status,
            resp.headers.get("Content-Type", ""),
            resp.read().decode("utf-8", errors="replace"),
        )


def _head_ok(url: str) -> tuple[bool, str]:
    """Return (ok, detail) for a link target — reachable and non-4xx/5xx."""
    try:
        _require_safe_url(url)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # nosec B310
            if resp.status >= 400:
                return False, f"HTTP {resp.status}"
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        return False, f"{type(e).__name__}: {e}"


# ── robots.txt parsing ───────────────────────────────────────────


def _directive(line: str) -> tuple[str, str] | None:
    """Split a robots.txt line into (lowercased field, value), or None."""
    # Strip trailing comments and whitespace; robots.txt comments start with #.
    line = line.split("#", 1)[0].strip()
    if not line or ":" not in line:
        return None
    field, value = line.split(":", 1)
    return field.strip().lower(), value.strip()


def _global_directive(body: str, name: str) -> list[str]:
    """Return all values for a non-group directive (e.g. Sitemap, Llms)."""
    name = name.lower()
    return [v for d in map(_directive, body.splitlines()) if d and d[0] == name and (v := d[1])]


def _blocks_all_crawlers(body: str) -> bool:
    """True if the `User-agent: *` group carries a bare `Disallow: /`.

    Groups start with one or more `User-agent` lines and run until the next
    group. A `Disallow: /` (path exactly `/`) in the wildcard group removes
    the whole site from compliant crawlers — the de-index footgun.
    """
    agents: list[str] = []
    star_group = False
    started_rules = False
    for line in body.splitlines():
        parsed = _directive(line)
        if not parsed:
            continue
        field, value = parsed
        if field == "user-agent":
            if started_rules:
                # A new group begins after the previous group's rules.
                agents = []
                started_rules = False
            agents.append(value)
            star_group = "*" in agents
        elif field in ("disallow", "allow"):
            started_rules = True
            if field == "disallow" and star_group and value == "/":
                return True
    return False


# ── content validation ───────────────────────────────────────────


def _validate_body(
    status: int,
    ctype: str,
    body: str,
    require_llms: bool,
    allow_disallow_all: bool,
) -> tuple[list[str], list[str], dict]:
    """Return (issues, notes, parsed) for a fetched robots.txt body."""
    issues: list[str] = []
    notes: list[str] = []

    if status != 200:
        issues.append(f"HTTP status {status} (expected 200)")
    if not any(ct in ctype.lower() for ct in PLAIN_CONTENT_TYPES):
        notes.append(f"Content-Type is {ctype!r}, expected text/plain")
    if not body.strip():
        issues.append("robots.txt is empty")

    if _blocks_all_crawlers(body):
        msg = "`User-agent: *` has a blanket `Disallow: /` — this de-indexes the entire site"
        if allow_disallow_all:
            notes.append(msg + " (allowed by allow_disallow_all)")
        else:
            issues.append(msg)

    sitemaps = _global_directive(body, "Sitemap")
    if not sitemaps:
        issues.append("No `Sitemap:` directive — crawlers can't discover your URL inventory")

    llms = _global_directive(body, "Llms")
    if not llms:
        msg = "No `Llms:` pointer to /llms.txt (recommended for AI-assistant discoverability)"
        (issues if require_llms else notes).append(msg)

    return issues, notes, {"sitemaps": sitemaps, "llms": llms}


def _check_links(urls: list[str], notes: list[str]) -> list[dict]:
    results: list[dict] = []
    for target in urls:
        if urllib.parse.urlparse(target).scheme.lower() not in ALLOWED_SCHEMES:
            continue
        ok, detail = _head_ok(target)
        results.append({"url": target, "ok": ok, "detail": detail})
        if not ok:
            notes.append(f"Referenced URL not reachable ({target}): {detail}")
    return results


def _audit(
    base: str,
    path: str,
    check_links: bool,
    require_llms: bool,
    allow_disallow_all: bool,
) -> dict:
    file_url = urllib.parse.urljoin(base.rstrip("/") + "/", path.lstrip("/"))

    try:
        status, ctype, body = _fetch(file_url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        return {
            "url": file_url,
            "status": "fail",
            "issues": [f"robots.txt not reachable: {type(e).__name__}: {e}"],
            "notes": [],
            "sitemap_count": 0,
            "llms_count": 0,
            "link_checks": [],
        }

    issues, notes, parsed = _validate_body(status, ctype, body, require_llms, allow_disallow_all)

    link_checks: list[dict] = []
    if check_links:
        link_checks = _check_links(parsed["sitemaps"] + parsed["llms"], notes)

    return {
        "url": file_url,
        "status": "fail" if issues else "pass",
        "issues": issues,
        "notes": notes,
        "sitemap_count": len(parsed["sitemaps"]),
        "llms_count": len(parsed["llms"]),
        "link_checks": link_checks,
    }


# ── markdown report ──────────────────────────────────────────────


def _build_markdown_report(result: dict) -> str:
    lines: list[str] = []
    lines.append("# 🤖 robots.txt Report")
    lines.append("")
    lines.append(f"**File:** {result['url']}")
    lines.append("")
    lines.append(f"**Overall:** {'✅ PASS' if result['status'] == 'pass' else '❌ FAIL'}")
    lines.append("")
    lines.append(f"**Sitemaps referenced:** {result['sitemap_count']}")
    lines.append("")
    if result["issues"]:
        lines.append("**Issues:**")
        for issue in result["issues"]:
            lines.append(f"- ❌ {issue}")
        lines.append("")
    if result["notes"]:
        lines.append("**Notes:**")
        for note in result["notes"]:
            lines.append(f"- ⚠️  {note}")
        lines.append("")
    if result["link_checks"]:
        lines.append("<details><summary>Link checks</summary>")
        lines.append("")
        lines.append("| Link | Status |")
        lines.append("|---|---|")
        for lc in result["link_checks"]:
            icon = "✅" if lc["ok"] else "❌"
            lines.append(f"| `{lc['url']}` | {icon} {lc['detail']} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## How to Fix")
    lines.append("")
    lines.append(
        "- **Not reachable** → publish a `robots.txt` at your site root. See "
        "[docs/reliability/ROBOTS_TXT.md](../../../docs/reliability/ROBOTS_TXT.md)."
    )
    lines.append(
        "- **Blanket `Disallow: /`** → this hides the whole site from search. Remove it, "
        "or narrow it to the paths you actually want blocked. If blocking everything is "
        "intentional (e.g. a private staging site), set `reliability.robots_txt.allow_disallow_all: true`."
    )
    lines.append(
        "- **Missing `Sitemap:`** → add `Sitemap: https://your-site/sitemap.xml` so crawlers "
        "can discover your URLs."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def _write_reports(result: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "robots-txt-report.json").write_text(json.dumps(result, indent=2) + "\n")
    REPORT_MD.write_text(_build_markdown_report(result))


def _print_result(result: dict) -> None:
    icon = "✅" if result["status"] == "pass" else "❌"
    output._emit(f"  {icon} {result['url']}")
    for issue in result["issues"]:
        output._emit(f"      - {issue}")


# ── CLI entrypoint ───────────────────────────────────────────────


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="slopstopper run reliability:robots-txt", add_help=False)
    p.add_argument("url_positional", nargs="?", default=None, help="Base URL to audit")
    p.add_argument("--url", default=None, help="Base URL to audit")
    p.add_argument("--path", default=None, help="Path to robots.txt (default: /robots.txt)")
    p.add_argument("--check-links", action="store_true", help="HEAD-verify Sitemap:/Llms: targets")
    p.add_argument(
        "--require-llms",
        action="store_true",
        help="Fail if the `Llms:` pointer is missing",
    )
    p.add_argument(
        "--allow-disallow-all",
        action="store_true",
        help="Permit a blanket `Disallow: /` without failing",
    )
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


def _resolve_url(parsed_url: str | None) -> str | None:
    return parsed_url or os.environ.get("ROBOTS_TXT_TEST_URL")


def _resolve_path(parsed_path: str | None) -> str:
    return parsed_path or os.environ.get("ROBOTS_TXT_PATH") or DEFAULT_PATH


def run(args: list[str] | None = None) -> int:
    parsed = _parse_args(args)
    url = _resolve_url(parsed.url_positional or parsed.url)
    if not url:
        output.error("robots.txt target URL is required")
        output._emit("Usage:")
        output._emit("  slopstopper run reliability:robots-txt -- --url https://your-site.example.com")
        output._emit("  ROBOTS_TXT_TEST_URL=https://your-site slopstopper run reliability:robots-txt")
        return 2

    try:
        _require_safe_url(url)
    except ValueError as e:
        # A file:// or ftp:// URL is a bad input, not a site failure.
        output.error(str(e))
        return 2

    path = _resolve_path(parsed.path)
    check_links = parsed.check_links or config.get_bool("reliability.robots_txt.check_links", False)
    require_llms = parsed.require_llms or config.get_bool("reliability.robots_txt.require_llms", False)
    allow_disallow_all = parsed.allow_disallow_all or config.get_bool("reliability.robots_txt.allow_disallow_all", False)

    output.status("🤖", f"robots.txt audit against: {url}{path}")
    output.separator()

    try:
        result = _audit(url, path, check_links, require_llms, allow_disallow_all)
    except ValueError as e:
        output.error(str(e))
        return 1

    _write_reports(result)
    _print_result(result)

    output.separator()
    if result["status"] == "pass":
        output.success("robots.txt is present and healthy.")
        return 0
    output.error("Failures detected. See .ss/reports/robots-txt/robots-txt-report.md for full details.")
    return 1
