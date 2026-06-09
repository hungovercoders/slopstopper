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


_KEYWORDS = {"": None, "null": None, "~": None, "true": True, "false": False}


def _parse_inline_list(s: str) -> list:
    """Parse an inline-list `[a, b, c]` form (caller has already matched _INLINE_LIST_RE)."""
    inner = _INLINE_LIST_RE.match(s).group(1).strip()
    if not inner:
        return []
    return [_parse_scalar(part) for part in inner.split(",")]


def _strip_quotes(s: str) -> str | None:
    """Return the inside of a matched-quote string, or None if not quoted."""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return None


def _parse_scalar(raw: str) -> object:
    """Convert a raw YAML scalar string to a Python value."""
    s = raw.strip()
    keyword_value = _KEYWORDS.get(s.lower()) if s.lower() in _KEYWORDS else "MISS"
    if keyword_value != "MISS":
        return keyword_value
    unquoted = _strip_quotes(s)
    if unquoted is not None:
        return unquoted
    if _INLINE_LIST_RE.match(s):
        return _parse_inline_list(s)
    return s


def _strip_comment(line: str) -> str:
    """Quote-aware strip of '#'-prefixed comments from a single line."""
    if "#" not in line:
        return line
    in_squote = False
    in_dquote = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_dquote:
            in_squote = not in_squote
        elif ch == '"' and not in_squote:
            in_dquote = not in_dquote
        elif ch == "#" and not in_squote and not in_dquote:
            return line[:i].rstrip()
    return line


def _pop_to_parent(stack: list, indent: int) -> object | None:
    """Pop the stack until the head is the parent for `indent`. Return parent or None if malformed."""
    while stack and stack[-1][0] >= indent:
        stack.pop()
    if not stack:
        return None
    return stack[-1][1]


def _handle_list_item(parent: object, body: str) -> None:
    """Append a parsed list item to parent if parent is a list; otherwise no-op."""
    match = _LIST_ITEM_RE.match(body)
    if not match or not isinstance(parent, list):
        return
    parent.append(_parse_scalar(match.group(1)))


def _handle_key_value(parent: object, indent: int, body: str, stack: list) -> None:
    """Apply a 'key: value' line under a dict parent. Empty value opens a child container."""
    if not isinstance(parent, dict):
        return
    kv = _KV_RE.match(body)
    if not kv:
        return
    key, value_str = kv.group(1), kv.group(2)
    if value_str == "":
        new_container: dict = {}
        parent[key] = new_container
        stack.append((indent, new_container))
    else:
        parent[key] = _parse_scalar(value_str)


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
    stack: list[tuple[int, object]] = [(-1, root)]

    for raw_line in raw.splitlines():
        line = _strip_comment(raw_line)
        if not line.strip():
            continue
        match = _INDENT_RE.match(line)
        if not match:
            continue
        indent, body = len(match.group(1)), match.group(2)
        parent = _pop_to_parent(stack, indent)
        if parent is None:
            return root  # malformed
        if _LIST_ITEM_RE.match(body):
            _handle_list_item(parent, body)
        else:
            _handle_key_value(parent, indent, body, stack)

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
