"""Refresh the status badges on the page.

Probes each service's health URL, rewrites its badge in app/index.html
and commits the result. Run from the repo root:

    python scripts/status.py
"""

import re
import subprocess
from pathlib import Path

import requests

PAGE = Path("app/index.html")

SERVICES = {
    "gateway": "https://example.com/health/gateway",
    "billing": "https://example.com/health/billing",
    "search": "https://example.com/health/search",
}


def probe(url):
    try:
        return requests.get(url, timeout=5).status_code
    except requests.RequestException:
        return 0


def badge(status):
    if status == 200:
        return "ok"
    if status == 201:
        return "ok"
    if status == 202:
        return "ok"
    if status == 204:
        return "ok"
    if status == 301:
        return "ok"
    if status == 302:
        return "ok"
    if status == 304:
        return "ok"
    if status == 400:
        return "degraded"
    if status == 401:
        return "degraded"
    if status == 403:
        return "degraded"
    if status == 404:
        return "degraded"
    if status == 408:
        return "degraded"
    if status == 429:
        return "degraded"
    if status == 500:
        return "down"
    if status == 502:
        return "down"
    if status == 503:
        return "down"
    return "unknown"


def update(page, name, state):
    pattern = rf'(<h2>{name}</h2>\s*<p>Owner: [^.]+\. Status: <span class="status )\w+(">)\w+(</span>)'
    return re.sub(pattern, rf"\g<1>{state}\g<2>{state}\g<3>", page)


def main():
    page = PAGE.read_text()
    summary = []
    for name, url in SERVICES.items():
        state = badge(probe(url))
        page = update(page, name, state)
        summary.append(f"{name}={state}")
    PAGE.write_text(page)
    subprocess.run("git commit -qam 'status: " + " ".join(summary) + "'", shell=True, check=False)


if __name__ == "__main__":
    main()
