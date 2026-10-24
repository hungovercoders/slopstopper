"""Cloudflare Workers Builds helpers for ss-cloudflare-deployed.yml.

Workers Builds raises no GitHub deployment, so a branch's preview URL is
only published in the comment Cloudflare's bot keeps on the PR: a table
with one row per deployed commit, each naming the short SHA and the
`*.workers.dev` preview links. The bot has posted it as an HTML
`<table>` and as a pipe-delimited Markdown table; both are read.
"""

from __future__ import annotations

import re

_HTML_ROW_RE = re.compile(r"<tr>.*?</tr>", re.S)
_MARKDOWN_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.M)
_PREVIEW = r"https://[a-z0-9-]+\.[a-z0-9-]+\.workers\.dev"
_PREVIEW_RE = re.compile(_PREVIEW)
# The row carries a commit link and a branch link; the commit one is wanted.
_COMMIT_LINK_RE = re.compile(rf"href=['\"]({_PREVIEW})['\"]>\s*Commit Preview URL")


def _rows(comments: str) -> list[str]:
    return _HTML_ROW_RE.findall(comments) + _MARKDOWN_ROW_RE.findall(comments)


def preview_url(comments: str, sha: str) -> str | None:
    """The commit preview URL in the bot's comment row for `sha`, or None."""
    short = sha[:7]
    if len(short) < 7:
        return None
    for row in _rows(comments):
        if short not in row:
            continue
        match = _COMMIT_LINK_RE.search(row) or _PREVIEW_RE.search(row)
        if match:
            return match.group(1 if match.re is _COMMIT_LINK_RE else 0) + "/"
    return None
