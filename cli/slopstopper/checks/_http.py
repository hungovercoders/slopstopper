"""HTTP plumbing shared by every URL-driven check.

Eight checks carried their own copy of the SSRF guard, seven their own
`urlopen` wrapper, four their own HEAD probe, three their own URL
joiner. Four of the `_fetch` copies were byte-identical down to the
`nosec` comments. Eight guards is eight places to forget one; this is
the one.

The guard is the point. `urllib.request.urlopen` happily handles
`file://` and `ftp://`, so a hostile `*_TEST_URL` value such as
`file:///etc/passwd` would be read by a checker and, on some paths,
echoed into a report. Every request a check makes goes through
`open_url`, which refuses anything but http/https before opening it.

Checks keep a module-level `_fetch` / `_head_ok` / `_require_safe_url`
name that delegates here, so tests can monkeypatch the check they are
testing without reaching into this module.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from typing import Any

ALLOWED_SCHEMES = ("http", "https")
DEFAULT_TIMEOUT = 15


def require_safe_url(url: str, label: str = "slopstopper") -> None:
    """Reject any URL whose scheme isn't http/https (blocks file:// SSRF).

    `label` names the check in the error, e.g. "API health check".
    """
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"{label} refuses scheme {scheme!r} (only http/https allowed). url={url!r}"
        )


def open_url(
    url: str,
    user_agent: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    label: str = "slopstopper",
) -> Any:
    """Open `url` after the scheme guard. Returns the response context manager.

    Raises the same things `urllib.request.urlopen` raises (HTTPError,
    URLError, TimeoutError) plus ValueError for a refused scheme — each
    caller decides which of those are data and which are failures.
    """
    require_safe_url(url, label)
    request_headers = {"User-Agent": user_agent, **(headers or {})}
    req = urllib.request.Request(url, headers=request_headers, method=method)
    # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
    return urllib.request.urlopen(req, timeout=timeout)  # nosec B310 — scheme guarded above


def fetch_text(
    url: str, user_agent: str, *, timeout: int = DEFAULT_TIMEOUT, label: str = "slopstopper"
) -> tuple[int, str, str]:
    """GET the URL. Returns (status, content_type, body). 4xx/5xx raise HTTPError."""
    with open_url(url, user_agent, timeout=timeout, label=label) as resp:
        return (
            resp.status,
            resp.headers.get("Content-Type", ""),
            resp.read().decode("utf-8", errors="replace"),
        )


def head_ok(
    url: str, user_agent: str, *, timeout: int = DEFAULT_TIMEOUT, label: str = "slopstopper"
) -> tuple[bool, str]:
    """HEAD the URL. Returns (ok, detail) — reachable and not 4xx/5xx."""
    try:
        with open_url(url, user_agent, method="HEAD", timeout=timeout, label=label) as resp:
            if resp.status >= 400:
                return False, f"HTTP {resp.status}"
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        return False, f"{type(e).__name__}: {e}"


def join_url(url: str, base_path: str, path: str) -> str:
    """`https://host` + `/api/v1` + `health` → `https://host/api/v1/health`."""
    prefix = (base_path or "").rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"{url.rstrip('/')}{prefix}{suffix}"
