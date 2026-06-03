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
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # nosec B310 — URL comes from env, not user input
        return resp.status, resp.headers.get("Content-Type", ""), resp.read().decode("utf-8", errors="replace")


def head_ok(url: str) -> tuple[bool, str]:
    """Return (ok, detail). Validates og:image is reachable and is an image."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
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

    title = parser.title or ""
    description = get_meta(parser.metas, "name", "description") or ""
    canonical = get_link(parser.links, "canonical") or ""
    og_title = get_meta(parser.metas, "property", "og:title") or ""
    og_description = get_meta(parser.metas, "property", "og:description") or ""
    og_type = get_meta(parser.metas, "property", "og:type") or ""
    og_url = get_meta(parser.metas, "property", "og:url") or ""
    og_image = get_meta(parser.metas, "property", "og:image") or ""
    twitter_card = get_meta(parser.metas, "name", "twitter:card") or ""
    twitter_title = get_meta(parser.metas, "name", "twitter:title") or ""
    twitter_description = get_meta(parser.metas, "name", "twitter:description") or ""
    twitter_image = get_meta(parser.metas, "name", "twitter:image") or ""
    viewport = get_meta(parser.metas, "name", "viewport") or ""

    # Required: core SEO
    if not title:
        issues.append("Missing <title>")
    elif len(title) > 70:
        notes.append(f"<title> is {len(title)} chars — consider ≤ 60")
    if not description:
        issues.append("Missing <meta name=\"description\">")
    elif len(description) > 160:
        notes.append(f"meta description is {len(description)} chars — consider ≤ 160")
    if not viewport:
        issues.append("Missing <meta name=\"viewport\">")
    if not canonical:
        issues.append("Missing <link rel=\"canonical\">")

    # Required: OpenGraph
    if not og_title:
        issues.append("Missing og:title")
    if not og_description:
        issues.append("Missing og:description")
    if not og_type:
        issues.append("Missing og:type")
    if not og_url:
        issues.append("Missing og:url")
    if require_og_image and not og_image:
        issues.append("Missing og:image")

    # Required: Twitter card
    if not twitter_card:
        issues.append("Missing twitter:card")
    elif twitter_card not in {"summary", "summary_large_image", "app", "player"}:
        notes.append(f"twitter:card is {twitter_card!r}, expected one of summary|summary_large_image|app|player")
    if not twitter_title:
        issues.append("Missing twitter:title")
    if not twitter_description:
        issues.append("Missing twitter:description")
    if require_og_image and not twitter_image:
        issues.append("Missing twitter:image")

    # Verify og:image is reachable
    image_check: Optional[dict] = None
    if og_image and verify_og_image:
        # Normalise relative og:image against page URL
        og_image_abs = urllib.parse.urljoin(page_url, og_image)
        ok, detail = head_ok(og_image_abs)
        image_check = {"url": og_image_abs, "ok": ok, "detail": detail}
        if not ok:
            issues.append(f"og:image not reachable ({og_image_abs}): {detail}")

    return {
        "url": page_url,
        "status": "fail" if issues else "pass",
        "issues": issues,
        "notes": notes,
        "tags": {
            "title": title,
            "description": description,
            "canonical": canonical,
            "viewport": viewport,
            "og:type": og_type,
            "og:title": og_title,
            "og:description": og_description,
            "og:url": og_url,
            "og:image": og_image,
            "twitter:card": twitter_card,
            "twitter:title": twitter_title,
            "twitter:description": twitter_description,
            "twitter:image": twitter_image,
        },
        "image_check": image_check,
    }


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
    lines: list[str] = []
    lines.append("# 🔎 SEO / Social-Share Metatag Report")
    lines.append("")
    lines.append(f"**Base URL:** {base}")
    lines.append("")
    lines.append(f"**Overall:** {'✅ PASS' if overall_pass else '❌ FAIL'}")
    lines.append("")
    for r in results:
        status_icon = {"pass": "✅", "fail": "❌", "error": "💥"}.get(r["status"], "•")
        lines.append(f"## {status_icon} {r['url']}")
        lines.append("")
        if r["issues"]:
            lines.append("**Issues:**")
            for issue in r["issues"]:
                lines.append(f"- ❌ {issue}")
            lines.append("")
        if r.get("notes"):
            lines.append("**Notes:**")
            for note in r["notes"]:
                lines.append(f"- ⚠️  {note}")
            lines.append("")
        if r.get("tags"):
            lines.append("<details><summary>Tags detected</summary>")
            lines.append("")
            lines.append("| Tag | Value |")
            lines.append("|---|---|")
            for k, v in r["tags"].items():
                display = (v[:120] + "…") if v and len(v) > 120 else v
                lines.append(f"| `{k}` | {display or '_(empty)_'} |")
            lines.append("")
            lines.append("</details>")
            lines.append("")
        if r.get("image_check"):
            ic = r["image_check"]
            icon = "✅" if ic["ok"] else "❌"
            lines.append(f"**og:image fetch:** {icon} `{ic['url']}` — {ic['detail']}")
            lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## How to Fix")
    lines.append("")
    lines.append("- **Missing tag** → add it to the page's `<head>`. See [docs/reliability/SEO.md](../../../docs/reliability/SEO.md) for the full required set.")
    lines.append("- **og:image not reachable** → confirm the URL is absolute, same-origin (or CORS-allowed for crawlers), and returns `image/*` content type.")
    lines.append("- **Title / description too long** → trim to keep search-result snippets readable.")
    lines.append("")
    md_path.write_text("\n".join(lines) + "\n")


def main() -> int:
    base = os.environ.get("SEO_TEST_URL", "").strip()
    if not base:
        print("❌ Error: SEO_TEST_URL is required", file=sys.stderr)
        print("", file=sys.stderr)
        print("Usage:", file=sys.stderr)
        print("  SEO_TEST_URL=https://your-site.com task ss:reliability:seo", file=sys.stderr)
        return 2

    pages_raw = os.environ.get("SEO_PAGES", "/")
    pages = [p.strip() for p in pages_raw.split(",") if p.strip()] or ["/"]
    require_og_image = os.environ.get("SEO_REQUIRE_OG_IMAGE", "1") != "0"
    verify_og_image = os.environ.get("SEO_VERIFY_OG_IMAGE", "1") != "0"

    print(f"🔎 SEO metatag audit against: {base}")
    print(f"   Pages: {', '.join(pages)}")
    print("━" * 60)

    results = [check_page(base, p, require_og_image, verify_og_image) for p in pages]
    write_reports(results, base)

    overall_pass = all(r["status"] == "pass" for r in results)
    for r in results:
        icon = {"pass": "✅", "fail": "❌", "error": "💥"}.get(r["status"], "•")
        suffix = "" if r["status"] == "pass" else f" — {len(r['issues'])} issue(s)"
        print(f"  {icon} {r['url']}{suffix}")
        for issue in r["issues"]:
            print(f"      - {issue}")

    print("━" * 60)
    if overall_pass:
        print("✅ All pages pass.")
    else:
        print("❌ Failures detected. See .ss/reports/seo/seo-metatags-report.md for full details.")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
