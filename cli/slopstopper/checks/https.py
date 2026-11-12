"""HTTPS redirect + HSTS audit (in-CLI implementation).

A site can answer `http://` with a page and nothing in a browser on a
desk says so: the browser remembers the https URL, or the TLD is on the
HSTS preload list. A link shortener that rewrites the link to `http://`,
or an in-app browser that ignores the preload list, then gets a plain-HTTP
page or no page at all. This check asks the two questions that close it:

  1. Does `http://<host>/` redirect (301/302/307/308) to `https://` on
     the same host? A 200, a 4xx or a redirect to anywhere else fails.
  2. Does the HTTPS response carry `Strict-Transport-Security` with a
     `max-age` above zero, so a browser that has visited once never asks
     over plain HTTP again?

Nothing listening on port 80 is a pass with a note: there is no
plain-HTTP page to redirect. A target that is not https, or is a local
host, is skipped with a note, because neither question means anything
there. A custom https port is audited for HSTS only.

CLI surface:
  slopstopper run security:https -- --url URL [--no-require-hsts]

Stdlib-only (urllib). Writes .ss/reports/https/https-report.{md,json}.

Configuration (.slopstopper.yml, all optional):

    security:
      https:
        require_hsts: true   # demand Strict-Transport-Security on the https response

Env-var equivalents the CLI also honours (precedence: flag > env > config):
  HTTPS_TEST_URL   base URL to audit (required)

See .slopstopper.yml.example for the canonical schema.

Exit codes:
  0: plain HTTP redirects to https and HSTS is sent, or the target is skipped
  1: failures detected
  2: the URL is missing, its scheme is not http/https, or the https host
     is unreachable
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import re
import urllib.error
import urllib.parse
from pathlib import Path

from slopstopper import config, output
from slopstopper.checks import _http, _report
from slopstopper.checks._contract import EXIT_CANNOT_RUN, EXIT_FAIL, EXIT_PASS, refuse_unsafe_url

REPORT_DIR = Path(".ss/reports/https")
REPORT_MD = REPORT_DIR / "https-report.md"
REPORT_JSON = REPORT_DIR / "https-report.json"
USER_AGENT = "SlopStopper-Https-Check/1.0"
REDIRECT_STATUSES = (301, 302, 307, 308)
HSTS_HEADER = "Strict-Transport-Security"

# Consumed by `slopstopper emit security:https --target pr-comment`.
# No issue keys: the exit code fails the workflow, and the failure
# tracker raises the main-branch issue.
META = {
    "report_path": str(REPORT_MD),
    "comment_discriminator": "🔐 HTTPS",
}

_LABEL = "HTTPS check"

REDIRECT_FIX = (
    "Redirect every plain-HTTP request to https at the edge. On Cloudflare: SSL/TLS → Edge "
    "Certificates → Always Use HTTPS. Elsewhere, the host's or the proxy's own force-HTTPS setting"
)
HSTS_FIX = (
    f"Send `{HSTS_HEADER}: max-age=15552000` on every response: in `_headers` (Cloudflare Pages, "
    "Netlify), in `worker/headers.json` or whatever `headers.source` names, or in the server's "
    "own config. Set security.https.require_hsts: false to stop asking"
)


class Unreachable(Exception):
    """The https host did not answer, so there is nothing to give a verdict on."""


# ── requests ─────────────────────────────────────────────────────


def _probe(url: str) -> tuple[int, dict[str, str]]:
    """One request, redirects not followed. Returns (status, headers)."""
    return _http.probe(url, USER_AGENT, label=_LABEL)


# ── the two questions ────────────────────────────────────────────


def _is_local(host: str) -> bool:
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or address.is_unspecified


def _skip_reason(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if _is_local(host):
        return f"{host} is a local host, where there is no edge to redirect and HSTS has no effect"
    if parsed.scheme.lower() != "https":
        return "the target is not https, so there is no https origin to redirect to or to send HSTS from"
    return None


def _header(headers: dict[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def _hsts_finding(headers: dict[str, str]) -> str | None:
    """What is wrong with the response's HSTS header, or None."""
    value = _header(headers, HSTS_HEADER)
    if not value:
        return f"`{HSTS_HEADER}` is missing from the https response. {HSTS_FIX}"
    match = re.search(r"max-age\s*=\s*\"?(\d+)", value, re.I)
    if not match:
        return f"`{HSTS_HEADER}: {value}` has no `max-age`, so browsers ignore it. {HSTS_FIX}"
    if int(match.group(1)) == 0:
        return f"`{HSTS_HEADER}: {value}` switches HSTS off (`max-age=0`). {HSTS_FIX}"
    return None


def _redirect_finding(status: int, headers: dict[str, str], http_url: str, host: str) -> str | None:
    """What is wrong with the plain-HTTP response, or None."""
    if status not in REDIRECT_STATUSES:
        return (
            f"`{http_url}` answered HTTP {status} with no redirect to https, so a link that "
            f"starts `http://` is served in the clear or not at all. {REDIRECT_FIX}"
        )
    location = _header(headers, "Location")
    target = urllib.parse.urlparse(urllib.parse.urljoin(http_url, location))
    if target.scheme.lower() != "https":
        return (
            f"`{http_url}` redirects ({status}) to `{location or '(no Location)'}`, which is not "
            f"https. {REDIRECT_FIX}"
        )
    if (target.hostname or "").lower() != host:
        return (
            f"`{http_url}` redirects ({status}) to another host, `{target.hostname}`, before the "
            f"browser has seen https on `{host}`. Redirect to `https://{host}/` first, then on to "
            f"the other host. {REDIRECT_FIX}"
        )
    return None


def _audit(url: str, require_hsts: bool) -> dict:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    https_url = f"https://{parsed.netloc}/"
    http_url = f"http://{host}/"
    issues: list[str] = []
    notes: list[str] = []

    try:
        _status, https_headers = _probe(https_url)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Unreachable(f"{https_url} did not answer: {type(e).__name__}: {e}") from e

    hsts = _hsts_finding(https_headers)
    if hsts and require_hsts:
        issues.append(hsts)
    elif hsts:
        notes.append(f"{hsts} (not required: security.https.require_hsts is false)")

    redirect: dict = {"url": http_url, "status": None, "location": None}
    if parsed.port not in (None, 443):
        notes.append(
            f"The redirect was not asked for: {https_url} is on a custom port, and port 80 "
            "on that host may be another service"
        )
    else:
        try:
            status, http_headers = _probe(http_url)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            notes.append(
                f"Nothing answered on `{http_url}` ({type(e).__name__}), so there is no "
                "plain-HTTP page to redirect"
            )
        else:
            redirect.update(status=status, location=_header(http_headers, "Location") or None)
            if finding := _redirect_finding(status, http_headers, http_url, host):
                issues.append(finding)

    return {
        "url": https_url,
        "status": "fail" if issues else "pass",
        "issues": issues,
        "notes": notes,
        "hsts": _header(https_headers, HSTS_HEADER) or None,
        "redirect": redirect,
    }


# ── report ───────────────────────────────────────────────────────


def _build_markdown_report(result: dict) -> str:
    lines = ["# 🔐 HTTPS Report", "", f"**Site:** {result['url']}", ""]
    if result["status"] == "skipped":
        lines.extend(_report.render_skip(result["reason"], [
            "Run it against the deployed site: `task ss:security:https -- https://your-site.example.com`.",
        ]))
        return "\n".join(lines) + "\n"
    lines.append(f"**Overall:** {'✅ PASS' if result['status'] == 'pass' else '❌ FAIL'}")
    lines.append("")
    redirect = result["redirect"]
    if redirect["status"] is not None:
        where = f" → `{redirect['location']}`" if redirect["location"] else ""
        lines.append(f"**Plain HTTP:** `{redirect['url']}` answered {redirect['status']}{where}")
        lines.append("")
    lines.append(f"**HSTS:** `{result['hsts']}`" if result["hsts"] else "**HSTS:** not sent")
    lines.append("")
    lines.extend(_report.render_issues(result["issues"]))
    lines.extend(_report.render_notes(result["notes"]))
    lines.extend([
        "---",
        "",
        "## How to Fix",
        "",
        f"- **No redirect to https** → {REDIRECT_FIX}.",
        f"- **Missing HSTS** → {HSTS_FIX}.",
        "",
        "See [docs/security/HTTPS.md](../../../docs/security/HTTPS.md).",
        "",
    ])
    return "\n".join(lines) + "\n"


def _write_reports(result: dict) -> None:
    _report.write_reports(REPORT_JSON, REPORT_MD, result, _build_markdown_report)


# ── CLI entrypoint ───────────────────────────────────────────────


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="slopstopper run security:https", add_help=False)
    p.add_argument("url_positional", nargs="?", default=None, help="Base URL to audit")
    p.add_argument("--url", default=None, help="Base URL to audit")
    p.add_argument("--no-require-hsts", action="store_true", help="Don't demand HSTS")
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


def _resolve_url(parsed_url: str | None) -> str | None:
    return parsed_url or os.environ.get("HTTPS_TEST_URL")


def run(args: list[str] | None = None) -> int:
    parsed = _parse_args(args)
    url = _resolve_url(parsed.url_positional or parsed.url)
    if not url:
        output.error("HTTPS check target URL is required")
        output._emit("Usage:")
        output._emit("  slopstopper run security:https -- --url https://your-site.example.com")
        output._emit("  HTTPS_TEST_URL=https://your-site.example.com slopstopper run security:https")
        return EXIT_CANNOT_RUN

    if (rc := refuse_unsafe_url(url, _LABEL)) is not None:
        return rc

    if reason := _skip_reason(url):
        output.info(f"Skipping: {reason}.")
        _write_reports({"url": url, "status": "skipped", "reason": reason})
        output.success("Nothing to audit, so skipping (exit 0).")
        return EXIT_PASS

    require_hsts = not parsed.no_require_hsts and config.get_bool("security.https.require_hsts", True)

    output.status("🔐", f"HTTPS redirect + HSTS audit against: {url}")
    output.separator()

    try:
        result = _audit(url, require_hsts)
    except Unreachable as e:
        output.error(f"{e}. The check could not run.")
        return EXIT_CANNOT_RUN
    except ValueError as e:
        output.error(str(e))
        return EXIT_CANNOT_RUN

    _write_reports(result)
    output._emit(f"  {'✅' if result['status'] == 'pass' else '❌'} {result['url']}")
    for issue in result["issues"]:
        output._emit(f"      - {issue}")
    for note in result["notes"]:
        output._emit(f"      · {note}")

    output.separator()
    if result["status"] == "pass":
        output.success("Plain HTTP redirects to https and HSTS is in place.")
        return EXIT_PASS
    output.error("Failures detected. See .ss/reports/https/https-report.md for full details.")
    return EXIT_FAIL
