"""Core Web Vitals audit (Lighthouse CI wrapper).

Ports the bash reliability:cwv flow:

  task ss:reliability:cwv -- https://your-site.example.com

  which is, under the covers:

  npx lhci autorun --collect.url="$CWV_URL" --config=.ss/lighthouserc.json

Subprocess-invokes `npx lhci` — Lighthouse CI is Apache-2.0; the
slopstopper-cli wheel ships zero Lighthouse code. The .ss/lighthouserc.json
config (and any *-ci variant) is still adopter-vendored today; lifting
into package data is a follow-up.

Exit codes:
  0 — lhci passed all thresholds
  non-zero — lhci failed thresholds or URL/config missing
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from slopstopper import templates


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="slopstopper run reliability:cwv", add_help=False)
    p.add_argument("--url", default=None, help="Site URL to audit (else $CWV_URL)")
    p.add_argument(
        "--config",
        default=None,
        help="Lighthouse CI config path (default: resolves via templates "
        "module — .ss/lighthouserc.json override, else package data)",
    )
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


def _npx_available() -> bool:
    return shutil.which("npx") is not None


def _resolve_url(parsed_url: str | None) -> str | None:
    return parsed_url or os.environ.get("CWV_URL")


def _build_cmd(url: str, config_path: str) -> list[str]:
    return [
        "npx", "lhci", "autorun",
        f"--collect.url={url}",
        f"--config={config_path}",
    ]


def run(args: list[str] | None = None) -> int:
    if not _npx_available():
        print("❌ npx is not available — install Node.js to run Lighthouse CI")
        return 1

    parsed = _parse_args(args)
    url = _resolve_url(parsed.url)
    if not url:
        print("❌ Error: CWV target URL is required")
        print("Usage:")
        print("  slopstopper run reliability:cwv -- --url https://your-site.example.com")
        print("  CWV_URL=https://your-site slopstopper run reliability:cwv")
        return 1

    config_path = Path(parsed.config) if parsed.config else templates.lighthouserc()
    if not config_path.exists():
        print(f"❌ Lighthouse CI config not found at {config_path}")
        return 1

    print(f"🚦 Running Core Web Vitals audit against: {url}")
    cmd = _build_cmd(url, str(config_path))
    result = subprocess.run(cmd, check=False)
    return result.returncode
