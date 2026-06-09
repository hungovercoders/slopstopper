"""
Headers source adapters.

Slopstopper's CSP-drift check (and anything else that needs a list of
{path, csp} rules) reads its source via one of these adapters. Adopters
pick the adapter in .slopstopper.yml `headers.format`. Adding support
for a new source format = drop in a new adapter module and register it
here. Nothing else in slopstopper changes.

Adapter contract:

    def parse(path: pathlib.Path) -> list[dict]:
        '''Return [{"for": str, "csp": str | None}, ...] for each rule.'''

Path is the file the adopter named in `.slopstopper.yml` `headers.source`.
Adapters do not validate the file's existence — the caller checks first.
"""

from __future__ import annotations

from pathlib import Path

from . import cloudflare_adapter
from . import json_adapter

# Registry maps the `headers.format` value in .slopstopper.yml to a
# callable that takes a Path and returns the rule list.
ADAPTERS = {
    "json": json_adapter.parse,
    "cloudflare-text": cloudflare_adapter.parse,
}


def detect_format(path: Path) -> str:
    """Best-effort format detection from a file path.

    Used when .slopstopper.yml says `format: auto`. Extension `.json`
    means the json adapter; anything else (including no extension, like
    a bare `_headers` file) means the cloudflare-text adapter.
    """
    if path.suffix.lower() == ".json":
        return "json"
    return "cloudflare-text"


def parse(path: Path, format_name: str) -> list[dict]:
    """Dispatch to the named adapter.

    Raises KeyError if format_name is unknown — caller should validate
    against ADAPTERS.keys() and report a friendly error.
    """
    if format_name == "auto":
        format_name = detect_format(path)
    adapter = ADAPTERS[format_name]
    return adapter(path)
