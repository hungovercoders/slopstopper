"""The preview-URL lookup ss-cloudflare-deployed.yml runs on Cloudflare's PR comment (#425)."""

from __future__ import annotations

import io

from slopstopper import cli, cloudflare

# The shape Cloudflare's bot keeps on a PR: one table row per deployed commit.
COMMENT = """## Deploying with Cloudflare Workers
<table><tr><th>Status</th><th>Commit</th><th>Preview URL</th></tr>
<tr><td>✅ Deployment successful!</td><td>1a2b3c4</td>
<td><a href='https://1a2b3c4d-site.acct.workers.dev'>Commit Preview URL</a><br>
<a href='https://feat-x-site.acct.workers.dev'>Branch Preview URL</a></td></tr>
<tr><td>✅ Deployment successful!</td><td>9f8e7d6</td>
<td><a href='https://9f8e7d6c-site.acct.workers.dev'>Commit Preview URL</a></td></tr>
</table>"""

# The Markdown form the bot posts (#459): pipe-delimited rows, the short SHA in
# its own cell, commit and branch links in one cell.
MARKDOWN_COMMENT = """## Deploying with Cloudflare Workers
| Status | Name | Commit | Preview URL | Updated |
| :--- | :--- | :--- | :--- | :--- |
| ✅ Deployment successful! <br>[View logs](https://dash.cloudflare.com/x) | site | 1f7a4c97 | <a href='https://36664209-site.acct.workers.dev'>Commit Preview URL</a><br><br><a href='https://chore-x-site.acct.workers.dev'>Branch Preview URL</a> | Oct 11 2026, 08:24 AM |
| ✅ Deployment successful! <br>[View logs](https://dash.cloudflare.com/y) | site | 9f8e7d6c | <a href='https://9f8e7d6c-site.acct.workers.dev'>Commit Preview URL</a> | Oct 10 2026, 08:00 AM |
"""


def test_the_markdown_table_row_for_the_deployed_commit_gives_its_commit_preview():
    assert cloudflare.preview_url(MARKDOWN_COMMENT, "1f7a4c97abcd") == "https://36664209-site.acct.workers.dev/"
    assert cloudflare.preview_url(MARKDOWN_COMMENT, "9f8e7d6c5b4a") == "https://9f8e7d6c-site.acct.workers.dev/"
    assert cloudflare.preview_url(MARKDOWN_COMMENT, "0000000aaaa") is None


def test_the_row_for_the_deployed_commit_gives_its_preview():
    assert cloudflare.preview_url(COMMENT, "9f8e7d6c5b4a") == "https://9f8e7d6c-site.acct.workers.dev/"
    assert cloudflare.preview_url(COMMENT, "1a2b3c4d5e6f") == "https://1a2b3c4d-site.acct.workers.dev/"


def test_a_commit_not_deployed_yet_has_no_preview():
    assert cloudflare.preview_url(COMMENT, "0000000aaaa") is None


def test_a_short_sha_matches_nothing():
    assert cloudflare.preview_url(COMMENT, "1a2") is None


def test_the_cli_reads_the_comment_on_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(COMMENT))
    assert cli.main(["cloudflare", "preview-url", "9f8e7d6c5b4a"]) == 0
    assert capsys.readouterr().out.strip() == "https://9f8e7d6c-site.acct.workers.dev/"
    monkeypatch.setattr("sys.stdin", io.StringIO(COMMENT))
    assert cli.main(["cloudflare", "preview-url", "0000000aaaa"]) == 1
