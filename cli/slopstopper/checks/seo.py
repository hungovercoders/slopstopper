"""SEO + social-share metatag audit (subprocess wrapper).

Ports the bash reliability:seo flow:

  task ss:reliability:seo -- https://your-site.example.com

  which is, under the covers:

  SEO_TEST_URL=...
  SEO_PAGES=$(python3 .ss/scripts/discover-pages.py seo --event=local)
  python3 .ss/scripts/check-seo-metatags.py

Unlike the Playwright reliability checks, this one wraps a stdlib-only
Python script (.ss/scripts/check-seo-metatags.py, 434 lines) — no
external tool dep beyond Python itself. The slopstopper-cli wheel
still ships zero copy of the script today; it's adopter-vendored.
Lifting check-seo-metatags.py and discover-pages.py into the CLI
package (so adopters un-vendor .ss/scripts/) is the next phase.

The wrapped script writes .ss/reports/seo/seo-metatags-report.{md,json}
— real diffable reports — but SEO is still NOT parity-tested in CI
because it hits live URLs (network-dependent, OG-image HEAD-checks
can transiently fail).

Threads SEO_TEST_URL via --url flag or env. Optional flags:
  --pages, --no-require-og-image, --no-verify-og-image, --og-image-base
all map onto the env vars the script already reads.

Exit codes:
  0 — all pages passed (or script reported pass)
  1 — failures detected, or URL/script missing
  other — propagated from the wrapped script
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from slopstopper import discovery

SCRIPT_PATH = Path(".ss/scripts/check-seo-metatags.py")


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="slopstopper run reliability:seo", add_help=False)
    p.add_argument("--url", default=None, help="Site URL to audit")
    p.add_argument("--pages", default=None, help="Comma-separated paths (default: /)")
    p.add_argument(
        "--no-require-og-image", action="store_true",
        help="Skip og:image presence check",
    )
    p.add_argument(
        "--no-verify-og-image", action="store_true",
        help="Skip HEAD-fetching og:image",
    )
    p.add_argument(
        "--og-image-base", default=None,
        help="Rewrite og:image/twitter:image origin to this base before HEAD",
    )
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


def _resolve_url(parsed_url: str | None) -> str | None:
    return parsed_url or os.environ.get("SEO_TEST_URL")


def _discover_pages() -> str | None:
    """Resolve pages.seo via the in-CLI discovery module."""
    try:
        paths = discovery.discover("seo", "local")
    except Exception:
        return None
    return ",".join(paths) if paths else None


def _build_env(parsed: argparse.Namespace, url: str) -> dict[str, str]:
    env = dict(os.environ)
    env["SEO_TEST_URL"] = url
    if parsed.pages is not None:
        env["SEO_PAGES"] = parsed.pages
    elif "SEO_PAGES" not in env:
        pages = _discover_pages()
        if pages is not None:
            env["SEO_PAGES"] = pages
    if parsed.no_require_og_image:
        env["SEO_REQUIRE_OG_IMAGE"] = "0"
    if parsed.no_verify_og_image:
        env["SEO_VERIFY_OG_IMAGE"] = "0"
    if parsed.og_image_base is not None:
        env["SEO_OG_IMAGE_BASE"] = parsed.og_image_base
    return env


def run(args: list[str] | None = None) -> int:
    parsed = _parse_args(args)
    url = _resolve_url(parsed.url)
    if not url:
        print("❌ Error: SEO target URL is required")
        print("Usage:")
        print("  slopstopper run reliability:seo -- --url https://your-site.example.com")
        print("  SEO_TEST_URL=https://your-site slopstopper run reliability:seo")
        return 1

    if not SCRIPT_PATH.exists():
        print(f"❌ SEO script not found at {SCRIPT_PATH}")
        print("   The script is vendored under .ss/scripts/ by the installer.")
        return 1

    print(f"🔎 Running SEO metatag audit against: {url}")
    env = _build_env(parsed, url)
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        env=env,
        check=False,
    )
    return result.returncode
