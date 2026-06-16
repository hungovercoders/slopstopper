"""Generate GitHub Actions status badges for installed slopstopper workflows.

`slopstopper badges` reads the `ss-*.yml` workflow files under
`.github/workflows/`, groups them by loop (security / hygiene /
reliability / operational), and prints a markdown block ready to paste
into the adopter's README.

OWNER/REPO comes from `$GITHUB_REPOSITORY` (set in GitHub Actions) or
`git remote get-url origin` (local). Override either with `--owner` /
`--repo`.

The workflow → (group, display) mapping is curated in `WORKFLOW_DISPLAY`
to give each badge a short human label (e.g. "SAST" rather than the raw
filename action segment "sast"). Workflows not in the map fall back to
title-cased derivation from the filename.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

GROUP_ORDER = ["security", "hygiene", "reliability", "operational"]

GROUP_HEADERS = {
    "security": "### 🔒 Security",
    "hygiene": "### 🧹 Hygiene",
    "reliability": "### ✅ Reliability",
    "operational": "### 🤖 Operational",
}

# Curated display labels per workflow. New workflows automatically fall
# back to title-cased action segments; add a row here when the default
# reads awkwardly (e.g. "vulnerability-all" → "Dependency CVEs").
WORKFLOW_DISPLAY: dict[str, tuple[str, str]] = {
    "ss-security-sast-check.yml": ("security", "SAST"),
    "ss-security-secrets-check.yml": ("security", "Secrets"),
    "ss-security-vulnerability-all-check.yml": ("security", "Dependency CVEs"),
    "ss-security-vulnerability-new-check.yml": ("security", "Dependency Review"),
    "ss-security-dast-check.yml": ("security", "DAST"),
    "ss-hygiene-complexity-check.yml": ("hygiene", "Complexity"),
    "ss-hygiene-csp-exceptions-check.yml": ("hygiene", "CSP Exceptions"),
    "ss-hygiene-docs-accuracy-check.yml": ("hygiene", "Docs Accuracy"),
    "ss-hygiene-docs-size-check.yml": ("hygiene", "Docs Size"),
    "ss-hygiene-docs-structure-check.yml": ("hygiene", "Docs Structure"),
    "ss-hygiene-entry-files-check.yml": ("hygiene", "Entry Files"),
    "ss-hygiene-auto-label-pr.yml": ("operational", "Auto-label PRs"),
    "ss-hygiene-doc-updater.lock.yml": ("operational", "Doc Updater"),
    "ss-reliability-smoke-tests.yml": ("reliability", "Smoke"),
    "ss-reliability-accessibility-check.yml": ("reliability", "Accessibility"),
    "ss-reliability-broken-links-check.yml": ("reliability", "Broken Links"),
    "ss-reliability-core-web-vitals.yml": ("reliability", "Core Web Vitals"),
    "ss-reliability-seo-check.yml": ("reliability", "SEO"),
    "ss-release.yml": ("operational", "Release"),
    "ss-workflow-failure-issue.yml": ("operational", "Workflow Failures"),
}

ADVERT_BADGE = (
    "[![slopstopper]"
    "(https://img.shields.io/badge/quality-slopstopper-2c7be5?style=flat-square)]"
    "(https://slopstopper.dev/)"
)


def _detect_owner_repo() -> tuple[str | None, str | None]:
    """Detect OWNER/REPO from $GITHUB_REPOSITORY (CI) or git remote (local)."""
    env = os.environ.get("GITHUB_REPOSITORY")
    if env and "/" in env:
        owner, repo = env.split("/", 1)
        return owner, repo
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None, None
    url = result.stdout.strip()
    # SSH: git@github.com:owner/repo.git
    m = re.match(r"^git@github\.com:([^/]+)/(.+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    # HTTPS: https://github.com/owner/repo[.git][/]
    m = re.match(r"^https?://github\.com/([^/]+)/(.+?)(?:\.git)?/?$", url)
    if m:
        return m.group(1), m.group(2)
    return None, None


def _list_installed_workflows() -> list[str]:
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        return []
    return sorted(p.name for p in workflows_dir.glob("ss-*.yml"))


def _group_workflow(filename: str) -> tuple[str, str]:
    if filename in WORKFLOW_DISPLAY:
        return WORKFLOW_DISPLAY[filename]
    m = re.match(r"^ss-(security|hygiene|reliability)-(.+?)(?:-check)?\.yml$", filename)
    if m:
        group = m.group(1)
        action = m.group(2).replace("-", " ").title()
        return group, action
    label = filename.removeprefix("ss-").removesuffix(".yml").replace("-", " ").title()
    return "operational", label


def _badge_line(owner: str, repo: str, display: str, workflow: str) -> str:
    return (
        f"[![{display}]"
        f"(https://github.com/{owner}/{repo}/actions/workflows/{workflow}/"
        f"badge.svg?branch=main)]"
        f"(https://github.com/{owner}/{repo}/actions/workflows/{workflow})"
    )


def generate(
    owner: str | None = None,
    repo: str | None = None,
    no_advert: bool = False,
) -> str:
    """Generate the markdown badges block for the installed workflows.

    Raises ValueError when owner/repo can't be detected or no workflows
    are installed — both are user-facing errors the CLI surfaces to stderr.
    """
    if not owner or not repo:
        detected_owner, detected_repo = _detect_owner_repo()
        owner = owner or detected_owner
        repo = repo or detected_repo
    if not owner or not repo:
        raise ValueError(
            "Could not detect owner/repo. Pass --owner and --repo, or run "
            "from a repository with a github.com remote, or set "
            "$GITHUB_REPOSITORY."
        )

    workflows = _list_installed_workflows()
    if not workflows:
        raise ValueError(
            "No slopstopper workflows installed in .github/workflows/. "
            "Run install.sh first."
        )

    grouped: dict[str, list[tuple[str, str]]] = {g: [] for g in GROUP_ORDER}
    for wf in workflows:
        group, display = _group_workflow(wf)
        grouped.setdefault(group, []).append((display, wf))

    lines: list[str] = ["## Pipeline status", ""]
    if not no_advert:
        lines += [ADVERT_BADGE, ""]
    for group in GROUP_ORDER:
        entries = grouped.get(group) or []
        if not entries:
            continue
        lines.append(GROUP_HEADERS[group])
        for display, wf in entries:
            lines.append(_badge_line(owner, repo, display, wf))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
