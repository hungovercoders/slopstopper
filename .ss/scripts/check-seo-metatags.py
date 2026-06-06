#!/usr/bin/env python3

"""
SEO / Social-Share Metatag Validator

Fetches one or more pages and asserts the presence of the metadata that
social-share crawlers (Slack, Twitter/X, LinkedIn, Discord, Facebook) and
SEO indexers rely on. Complements `ss:reliability:cwv` — Lighthouse's SEO
category covers core SEO (description, viewport, canonical, indexability)
but does not flag missing OpenGraph or Twitter tags.

Inputs (env vars):
    SEO_TEST_URL       (required)  base URL, e.g. https://slopstopper.dev
    SEO_PAGES          (default /) comma-separated paths to check
    SEO_REQUIRE_OG_IMAGE  (default 1)  set to 0 to skip og:image presence check
    SEO_VERIFY_OG_IMAGE   (default 1)  set to 0 to skip HEAD-fetching og:image

Outputs:
    .ss/reports/seo/seo-metatags-report.md   (human-readable)
    .ss/reports/seo/seo-metatags-report.json (machine-readable)

Exit code: 0 if all required tags present on all pages, 1 otherwise.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional


REPORT_DIR = Path(".ss/reports/seo")
USER_AGENT = "SlopStopper-SEO-Check/1.0"
TIMEOUT_SECONDS = 15
ALLOWED_SCHEMES = ("http", "https")


def _require_safe_url(url: str) -> None:
    """Reject any URL whose scheme isn't http/https.

    urllib.request.urlopen happily handles file:// and ftp:// too, which
    could let a hostile SEO_TEST_URL value (e.g. file:///etc/passwd) be
    read by this checker. Validating the scheme up-front makes the
    urlopen calls safe by construction even though they take a variable
    URL — Semgrep's dynamic-urllib-use-detected rule cannot see that
    safety, hence the # nosemgrep annotations downstream.
    """
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"SEO check refuses scheme {scheme!r} (only http/https allowed). url={url!r}"
        )


# ── HTML parser: only walks the <head>, captures meta/title/link ─────

class HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_head = False
        self.in_title = False
        self.title: Optional[str] = None
        self.metas: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag == "head":
            self.in_head = True
            return
        if not self.in_head:
            return
        a = {k: v or "" for k, v in attrs}
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self.in_head = False
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title and self.title is None:
            self.title = data.strip()


def fetch(url: str) -> tuple[int, str, str]:
    # Scheme validated by _require_safe_url; URL originates from the
    # SEO_TEST_URL env var (operator-supplied), not end-user input. The
    # # nosemgrep on the urlopen line below references that guarantee;
    # # nosec B310 is the same suppression in Bandit's syntax.
    _require_safe_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # nosec B310
        return resp.status, resp.headers.get("Content-Type", ""), resp.read().decode("utf-8", errors="replace")


def head_ok(url: str) -> tuple[bool, str]:
    """Return (ok, detail). Validates og:image is reachable and is an image."""
    # Scheme validated by _require_safe_url; URL is derived from a
    # page-resolved og:image, which itself came from operator-supplied
    # SEO_TEST_URL. The # nosemgrep on the urlopen line below references
    # that guarantee; # nosec B310 is the same suppression in Bandit's
    # syntax.
    try:
        _require_safe_url(url)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # nosec B310
            ct = resp.headers.get("Content-Type", "")
            if resp.status != 200:
                return False, f"HTTP {resp.status}"
            if not ct.startswith("image/"):
                return False, f"Content-Type is {ct!r}, expected image/*"
            return True, ct
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        return False, f"{type(e).__name__}: {e}"


def get_meta(metas: list[dict[str, str]], key_attr: str, key_value: str) -> Optional[str]:
    for m in metas:
        if m.get(key_attr, "").lower() == key_value.lower():
            return m.get("content", "")
    return None


def get_link(links: list[dict[str, str]], rel: str) -> Optional[str]:
    for link in links:
        if link.get("rel", "").lower() == rel.lower():
            return link.get("href", "")
    return None


def value_or_empty(value: Optional[str]) -> str:
    return value if value else ""


def collect_tags(parser: HeadParser) -> dict[str, str]:
    return {
        "title": value_or_empty(parser.title),
        "description": value_or_empty(get_meta(parser.metas, "name", "description")),
        "canonical": value_or_empty(get_link(parser.links, "canonical")),
        "viewport": value_or_empty(get_meta(parser.metas, "name", "viewport")),
        "og:type": value_or_empty(get_meta(parser.metas, "property", "og:type")),
        "og:title": value_or_empty(get_meta(parser.metas, "property", "og:title")),
        "og:description": value_or_empty(get_meta(parser.metas, "property", "og:description")),
        "og:url": value_or_empty(get_meta(parser.metas, "property", "og:url")),
        "og:image": value_or_empty(get_meta(parser.metas, "property", "og:image")),
        "twitter:card": value_or_empty(get_meta(parser.metas, "name", "twitter:card")),
        "twitter:title": value_or_empty(get_meta(parser.metas, "name", "twitter:title")),
        "twitter:description": value_or_empty(get_meta(parser.metas, "name", "twitter:description")),
        "twitter:image": value_or_empty(get_meta(parser.metas, "name", "twitter:image")),
    }


def validate_core_tags(tags: dict[str, str], issues: list[str], notes: list[str]) -> None:
    title = tags["title"]
    description = tags["description"]
    if not title:
        issues.append("Missing <title>")
    elif len(title) > 70:
        notes.append(f"<title> is {len(title)} chars — consider ≤ 60")
    if not description:
        issues.append("Missing <meta name=\"description\">")
    elif len(description) > 160:
        notes.append(f"meta description is {len(description)} chars — consider ≤ 160")
    if not tags["viewport"]:
        issues.append("Missing <meta name=\"viewport\">")
    if not tags["canonical"]:
        issues.append("Missing <link rel=\"canonical\">")


def validate_open_graph_tags(tags: dict[str, str], issues: list[str], require_og_image: bool) -> None:
    for key in ("og:title", "og:description", "og:type", "og:url"):
        if not tags[key]:
            issues.append(f"Missing {key}")
    if require_og_image and not tags["og:image"]:
        issues.append("Missing og:image")


def validate_twitter_tags(tags: dict[str, str], issues: list[str], notes: list[str], require_og_image: bool) -> None:
    twitter_card = tags["twitter:card"]
    if not twitter_card:
        issues.append("Missing twitter:card")
    elif twitter_card not in {"summary", "summary_large_image", "app", "player"}:
        notes.append(f"twitter:card is {twitter_card!r}, expected one of summary|summary_large_image|app|player")
    for key in ("twitter:title", "twitter:description"):
        if not tags[key]:
            issues.append(f"Missing {key}")
    if require_og_image and not tags["twitter:image"]:
        issues.append("Missing twitter:image")


def check_page(base: str, path: str, require_og_image: bool, verify_og_image: bool) -> dict:
    page_url = urllib.parse.urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    issues: list[str] = []
    notes: list[str] = []

    try:
        status, ctype, body = fetch(page_url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        return {
            "url": page_url,
            "status": "error",
            "issues": [f"Failed to fetch: {type(e).__name__}: {e}"],
            "notes": [],
        }

    if status != 200:
        issues.append(f"HTTP status {status}")
    if "text/html" not in ctype.lower():
        notes.append(f"Content-Type is {ctype!r}, expected text/html")

    parser = HeadParser()
    parser.feed(body)
    tags = collect_tags(parser)
    validate_core_tags(tags, issues, notes)
    validate_open_graph_tags(tags, issues, require_og_image)
    validate_twitter_tags(tags, issues, notes, require_og_image)

    # Verify og:image is reachable
    image_check: Optional[dict] = None
    if tags["og:image"] and verify_og_image:
        # Normalise relative og:image against page URL
        og_image_abs = urllib.parse.urljoin(page_url, tags["og:image"])
        ok, detail = head_ok(og_image_abs)
        image_check = {"url": og_image_abs, "ok": ok, "detail": detail}
        if not ok:
            issues.append(f"og:image not reachable ({og_image_abs}): {detail}")

    return {
        "url": page_url,
        "status": "fail" if issues else "pass",
        "issues": issues,
        "notes": notes,
        "tags": tags,
        "image_check": image_check,
    }


def append_issues(lines: list[str], issues: list[str]) -> None:
    lines.append("**Issues:**")
    for issue in issues:
        lines.append(f"- ❌ {issue}")
    lines.append("")


def append_notes(lines: list[str], notes: list[str]) -> None:
    lines.append("**Notes:**")
    for note in notes:
        lines.append(f"- ⚠️  {note}")
    lines.append("")


def append_tags(lines: list[str], tags: dict[str, str]) -> None:
    lines.append("<details><summary>Tags detected</summary>")
    lines.append("")
    lines.append("| Tag | Value |")
    lines.append("|---|---|")
    for k, v in tags.items():
        display = (v[:120] + "…") if v and len(v) > 120 else v
        lines.append(f"| `{k}` | {display or '_(empty)_'} |")
    lines.append("")
    lines.append("</details>")
    lines.append("")


def append_image_check(lines: list[str], image_check: dict) -> None:
    icon = "✅" if image_check["ok"] else "❌"
    lines.append(f"**og:image fetch:** {icon} `{image_check['url']}` — {image_check['detail']}")
    lines.append("")


def append_page_markdown(lines: list[str], result: dict) -> None:
    status_icon = {"pass": "✅", "fail": "❌", "error": "💥"}.get(result["status"], "•")
    lines.append(f"## {status_icon} {result['url']}")
    lines.append("")
    if result["issues"]:
        append_issues(lines, result["issues"])
    if result.get("notes"):
        append_notes(lines, result["notes"])
    if result.get("tags"):
        append_tags(lines, result["tags"])
    if result.get("image_check"):
        append_image_check(lines, result["image_check"])


def build_markdown_report(results: list[dict], base: str, overall_pass: bool) -> str:
    lines: list[str] = []
    lines.append("# 🔎 SEO / Social-Share Metatag Report")
    lines.append("")
    lines.append(f"**Base URL:** {base}")
    lines.append("")
    lines.append(f"**Overall:** {'✅ PASS' if overall_pass else '❌ FAIL'}")
    lines.append("")
    for result in results:
        append_page_markdown(lines, result)
    lines.append("---")
    lines.append("")
    lines.append("## How to Fix")
    lines.append("")
    lines.append("- **Missing tag** → add it to the page's `<head>`. See [docs/reliability/SEO.md](../../../docs/reliability/SEO.md) for the full required set.")
    lines.append("- **og:image not reachable** → confirm the URL is absolute, same-origin (or CORS-allowed for crawlers), and returns `image/*` content type.")
    lines.append("- **Title / description too long** → trim to keep search-result snippets readable.")
    lines.append("")
    return "\n".join(lines) + "\n"


def write_reports(results: list[dict], base: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    overall_pass = all(r["status"] == "pass" for r in results)

    # JSON
    json_path = REPORT_DIR / "seo-metatags-report.json"
    json_path.write_text(json.dumps({
        "base_url": base,
        "overall": "pass" if overall_pass else "fail",
        "pages": results,
    }, indent=2) + "\n")

    # Markdown
    md_path = REPORT_DIR / "seo-metatags-report.md"
    md_path.write_text(build_markdown_report(results, base, overall_pass))


def read_config() -> tuple[str, list[str], bool, bool]:
    base = os.environ.get("SEO_TEST_URL", "").strip()
    pages_raw = os.environ.get("SEO_PAGES", "/")
    pages = [p.strip() for p in pages_raw.split(",") if p.strip()] or ["/"]
    require_og_image = os.environ.get("SEO_REQUIRE_OG_IMAGE", "1") != "0"
    verify_og_image = os.environ.get("SEO_VERIFY_OG_IMAGE", "1") != "0"
    return base, pages, require_og_image, verify_og_image


def print_results(results: list[dict]) -> None:
    for r in results:
        icon = {"pass": "✅", "fail": "❌", "error": "💥"}.get(r["status"], "•")
        suffix = "" if r["status"] == "pass" else f" — {len(r['issues'])} issue(s)"
        print(f"  {icon} {r['url']}{suffix}")
        for issue in r["issues"]:
            print(f"      - {issue}")


def main() -> int:
    base, pages, require_og_image, verify_og_image = read_config()
    if not base:
        print("❌ Error: SEO_TEST_URL is required", file=sys.stderr)
        print("", file=sys.stderr)
        print("Usage:", file=sys.stderr)
        print("  SEO_TEST_URL=https://your-site.com task ss:reliability:seo", file=sys.stderr)
        return 2

    print(f"🔎 SEO metatag audit against: {base}")
    print(f"   Pages: {', '.join(pages)}")
    print("━" * 60)

    results = [check_page(base, p, require_og_image, verify_og_image) for p in pages]
    write_reports(results, base)

    overall_pass = all(r["status"] == "pass" for r in results)
    print_results(results)
    print("━" * 60)
    if overall_pass:
        print("✅ All pages pass.")
    else:
        print("❌ Failures detected. See .ss/reports/seo/seo-metatags-report.md for full details.")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
