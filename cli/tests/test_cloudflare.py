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
