"""Read values from .slopstopper.yml.

Stdlib-only YAML subset parser, lifted from .ss/scripts/load_config.py
during the CLI pivot. Slopstopper deliberately avoids a PyYAML
dependency so the CLI installs cleanly via pipx with zero runtime
dependencies. The subset is enough for the .slopstopper.yml shape:
scalars, nested mappings, sequences of scalars, and `null`/empty values.

If the file doesn't exist or a key is absent, get() returns the supplied
default. Errors during parsing are non-fatal — they fall back to defaults
and warn on stderr.
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
    inner = _INLINE_LIST_RE.match(s).group(1).strip()
    if not inner:
        return []
    return [_parse_scalar(part) for part in inner.split(",")]


def _strip_quotes(s: str) -> str | None:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return None


def _parse_scalar(raw: str) -> object:
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
    while stack and stack[-1][0] >= indent:
        stack.pop()
    if not stack:
        return None
    return stack[-1][1]


def _handle_list_item(parent: object, body: str, stack: list) -> None:
    """Append a parsed list item to the parent container.

    If the parent is an empty dict opened by `key:` with no value, this is
    actually a block list — retroactively convert it to a list under the
    grandparent (so the dict→list ambiguity inherent to YAML is resolved
    on the first list item encountered).
    """
    match = _LIST_ITEM_RE.match(body)
    if not match:
        return
    value = _parse_scalar(match.group(1))
    if isinstance(parent, list):
        parent.append(value)
        return
    if isinstance(parent, dict) and not parent and len(stack) >= 2:
        grandparent = stack[-2][1]
        if isinstance(grandparent, dict):
            for k, v in grandparent.items():
                if v is parent:
                    new_list: list = [value]
                    grandparent[k] = new_list
                    stack[-1] = (stack[-1][0], new_list)
                    return


def _handle_key_value(parent: object, indent: int, body: str, stack: list) -> None:
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
    if not path.exists():
        return {}
    try:
        raw = path.read_text()
    except OSError as e:
        print(f"⚠  slopstopper.config: could not read {path} ({e}) — using defaults", file=sys.stderr)
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
            return root
        if _LIST_ITEM_RE.match(body):
            _handle_list_item(parent, body, stack)
        else:
            _handle_key_value(parent, indent, body, stack)

    return _convert_empty_dicts_to_lists_if_needed(root, raw)


def _convert_empty_dicts_to_lists_if_needed(node: object, raw_yaml: str) -> object:
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, dict) and not value:
                pattern = re.compile(rf"^\s*{re.escape(key)}:\s*\n\s+-\s+", re.MULTILINE)
                if pattern.search(raw_yaml):
                    node[key] = []
            else:
                _convert_empty_dicts_to_lists_if_needed(value, raw_yaml)
    return node


_CACHE: dict | None = None
_CACHE_PATH: Path | None = None


def _config() -> dict:
    global _CACHE, _CACHE_PATH
    if _CACHE is None or _CACHE_PATH != CONFIG_PATH:
        _CACHE = _load_yaml_subset(CONFIG_PATH)
        _CACHE_PATH = CONFIG_PATH
    return _CACHE


def get(path: str, default: object = None) -> object:
    """Return the value at a dot-path in .slopstopper.yml, or default."""
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
    global _CACHE, _CACHE_PATH
    _CACHE = None
    _CACHE_PATH = None
