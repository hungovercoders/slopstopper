"""Cloudflare Workers Builds helpers for ss-cloudflare-deployed.yml.

Workers Builds raises no GitHub deployment, so a branch's preview URL is
only published in the comment Cloudflare's bot keeps on the PR: an HTML
table with one row per deployed commit, each naming the short SHA and the
`*.workers.dev` preview link.
"""

from __future__ import annotations

import re

_ROW_RE = re.compile(r"<tr>.*?</tr>", re.S)
_PREVIEW_RE = re.compile(r"https://[a-z0-9-]+\.[a-z0-9-]+\.workers\.dev")


def preview_url(comments: str, sha: str) -> str | None:
    """The preview URL in the bot's comment row for `sha`, or None."""
    short = sha[:7]
    if len(short) < 7:
        return None
    for row in _ROW_RE.findall(comments):
        if short in row:
            match = _PREVIEW_RE.search(row)
            if match:
                return match.group(0) + "/"
    return None
