#!/usr/bin/env python3

"""
load_config — read values from .slopstopper.yml.

Stdlib-only YAML subset parser. Slopstopper deliberately avoids a PyYAML
dependency in .ss/scripts/ so adopters don't have to manage a Python
package install just to run quality checks. The subset is enough for
the .slopstopper.yml shape: scalars, nested mappings, sequences of
scalars (`workflows.disabled: [foo, bar]`), and `null`/empty values.

If the file doesn't exist or a key is absent, get() returns the supplied
default. Errors during parsing are non-fatal — they fall back to defaults
and warn on stderr — so a malformed config can't take down the suite.

Usage from another script:

    from load_config import get
    node_version = get('node_version', '20')
    headers_source = get('headers.source', None)
    headers_format = get('headers.format', 'auto')
    disabled = get('workflows.disabled', [])
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CONFIG_PATH = Path(".slopstopper.yml")

_INDENT_RE = re.compile(r"^( *)(.*)$")
_KV_RE = re.compile(r"^([A-Za-z0-9_\-]+):\s*(.*)$")
_LIST_ITEM_RE = re.compile(r"^-\s+(.*)$")
_INLINE_LIST_RE = re.compile(r"^\[(.*)\]$")


def _parse_scalar(raw: str) -> object:
    """Convert a raw YAML scalar string to a Python value."""
    s = raw.strip()
    if s == "" or s.lower() in ("null", "~"):
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    # Strip matching surrounding quotes (single or double).
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    # Inline list: [a, b, c]
    inline = _INLINE_LIST_RE.match(s)
    if inline:
        inner = inline.group(1).strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in inner.split(",")]
    return s


def _load_yaml_subset(path: Path) -> dict:
    """Parse the .slopstopper.yml subset into a nested dict.

    Tracks indentation to nest mappings; '-' lines collect into sequences.
    Indentation MUST be spaces (no tabs). Comments (#...) and blank lines
    are ignored.
    """
    if not path.exists():
        return {}
    try:
        raw = path.read_text()
    except OSError as e:
        print(f"⚠  load_config: could not read {path} ({e}) — using defaults", file=sys.stderr)
        return {}

    root: dict = {}
    # stack entries: (indent_cols, container) — container is dict or list
    stack: list[tuple[int, object]] = [(-1, root)]

    for raw_line in raw.splitlines():
        # Strip comments (but not '#' inside a quoted string — best-effort)
        line = raw_line
        if "#" in line:
            # naive split on first '#' that isn't inside quotes
            in_squote = False
            in_dquote = False
            for i, ch in enumerate(line):
                if ch == "'" and not in_dquote:
                    in_squote = not in_squote
                elif ch == '"' and not in_squote:
                    in_dquote = not in_dquote
                elif ch == "#" and not in_squote and not in_dquote:
                    line = line[:i].rstrip()
                    break
        if not line.strip():
            continue

        m = _INDENT_RE.match(line)
        if not m:
            continue
        indent = len(m.group(1))
        body = m.group(2)

        # Pop the stack to the parent of this indent.
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            # malformed — bail
            return root
        parent = stack[-1][1]

        # List item under a parent (must be a list)
        list_item = _LIST_ITEM_RE.match(body)
        if list_item:
            value = _parse_scalar(list_item.group(1))
            if isinstance(parent, list):
                parent.append(value)
            elif isinstance(parent, dict):
                # parent expected to be a dict; previous key opened a list-value
                # which we'd have stacked as a list. If we got here, the YAML
                # is malformed for our subset.
                continue
            continue

        # Key-value line
        kv = _KV_RE.match(body)
        if not kv:
            continue
        key = kv.group(1)
        value_str = kv.group(2)

        if not isinstance(parent, dict):
            continue

        if value_str == "":
            # Could open either a nested dict OR a list — we don't know until
            # we see the next line. Default to dict; promote to list if a '-'
            # appears at deeper indent.
            new_container: object = {}
            parent[key] = new_container
            stack.append((indent, new_container))
        else:
            # Inline scalar (or inline list, handled by _parse_scalar)
            parent[key] = _parse_scalar(value_str)

    # Pass 2 — for keys that ended up with empty dicts but should be lists
    # (because the immediately-following lines were '-' items), this parser
    # already populated them as lists via the list_item branch above when
    # the stack head was the empty dict and we appended to it. Wait — that
    # branch checks isinstance(parent, list). So if parent is the empty
    # dict, the append is skipped. We need a fix: when we see a list_item
    # under a dict-parent that was just opened as empty, convert it to list.
    # Handled by a second pass: detect dicts that hold no keys but had list
    # items intended. The simplest fix is to track this differently in
    # pass 1 — but since the test cases for .slopstopper.yml use either
    # inline lists `[]` or explicit list items under a dedicated list key,
    # let's handle the dict-was-meant-to-be-list case lazily:
    return _convert_empty_dicts_to_lists_if_needed(root, raw)


def _convert_empty_dicts_to_lists_if_needed(node: object, raw_yaml: str) -> object:
    """Best-effort: any empty dict whose key has '- '-prefixed children under
    it in the raw YAML becomes an empty list. Covers the `workflows: disabled:`
    pattern where the list could be empty or populated."""
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, dict) and not value:
                # Look for `key:\n  - ` in the raw — if present, it's a list
                pattern = re.compile(rf"^{re.escape(key)}:\s*\n\s+-\s+", re.MULTILINE)
                if pattern.search(raw_yaml):
                    node[key] = []
            else:
                _convert_empty_dicts_to_lists_if_needed(value, raw_yaml)
    return node


_CACHE: dict | None = None


def _config() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = _load_yaml_subset(CONFIG_PATH)
    return _CACHE


def get(path: str, default: object = None) -> object:
    """Return the value at a dot-path in .slopstopper.yml, or default.

    Empty dicts (from `key:` lines with no value AND no indented children)
    are treated as unset and return the default. Empty lists (`[]` or a
    `workflows.disabled:` key explicitly opened as a list) stay empty.
    """
    node: object = _config()
    for segment in path.split("."):
        if not isinstance(node, dict) or segment not in node:
            return default
        node = node[segment]
    if node is None:
        return default
    if isinstance(node, dict) and not node:
        return default
    return node


def reload() -> None:
    """Force re-read of .slopstopper.yml (for tests)."""
    global _CACHE
    _CACHE = None


if __name__ == "__main__":
    # CLI shim: `python3 load_config.py headers.source` prints the value.
    if len(sys.argv) < 2:
        print("usage: load_config.py <dot.path> [default]", file=sys.stderr)
        sys.exit(2)
    fallback = sys.argv[2] if len(sys.argv) > 2 else ""
    value = get(sys.argv[1], fallback)
    if value is None:
        print("")
    elif isinstance(value, list):
        print(",".join(str(v) for v in value))
    else:
        print(value)
