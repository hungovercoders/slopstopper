"""What `slopstopper install` writes into a repo, and where it comes from.

The suite an adopter runs is files: the `ss-*.yml` workflows, the composite
actions they build on, the `task ss:*` shims, the seeds (the `.slopstopper.yml`
starter, the labeler config, the licence policy, the headers baseline, the ZAP
rules, the markdownlint config), the pre-push hook, the two Claude Code skills
and the `package.json` whose devDependencies the browser checks need. This
module names them once.

The hatch build hook (`cli/hatch_build.py`) copies that list into the wheel
under `slopstopper/data/suite/`, so an installed CLI carries the suite of its
own version and the shims it writes always name checks it knows. In a checkout
of this repository, where the CLI is installed editable, the same files are
served from the repository root, which is also where this repository's own
copies live.
"""

from __future__ import annotations

import re
from pathlib import Path

from slopstopper.templates import PACKAGE_DATA_DIR

# The workflows the installer ships, in the order the post-install matrix
# describes them. `ss-cloudflare-deployed.yml` goes only to a Cloudflare repo;
# the doc-updater is a gh-aw source plus its compiled lock file.
GENERIC_WORKFLOWS: tuple[str, ...] = (
    # Layer 1: static analysis (works on any code)
    "ss-hygiene-complexity-check.yml",
    "ss-hygiene-csp-exceptions-check.yml",
    "ss-hygiene-docs-accuracy-check.yml",
    "ss-hygiene-docs-size-check.yml",
    "ss-hygiene-docs-structure-check.yml",
    "ss-hygiene-entry-files-check.yml",
    "ss-hygiene-privacy-check.yml",
    "ss-hygiene-auto-label-pr.yml",
    "ss-security-sast-check.yml",
    "ss-security-secrets-check.yml",
    "ss-security-vulnerability-all-check.yml",
    "ss-security-licences-check.yml",
    "ss-security-vulnerability-new-check.yml",
    "ss-workflow-failure-issue.yml",
    "ss-pr-summary.yml",
    # Layer 2: web-app dynamic (needs a URL)
    "ss-security-dast-check.yml",
    "ss-reliability-smoke-tests.yml",
    "ss-reliability-e2e-check.yml",
    "ss-reliability-accessibility-check.yml",
    "ss-reliability-broken-links-check.yml",
    "ss-reliability-core-web-vitals.yml",
    "ss-reliability-seo-check.yml",
    "ss-reliability-llms-txt-check.yml",
    "ss-reliability-robots-txt-check.yml",
    "ss-reliability-sitemap-check.yml",
    "ss-reliability-api-health-check.yml",
    "ss-reliability-api-latency-check.yml",
    "ss-security-api-headers-check.yml",
    # The one hygiene check that needs a URL: drift means the spec measured
    # against the thing it documents, so it lives in layer 2 with the rest.
    "ss-hygiene-openapi-check.yml",
    # Layer 3: agentic doc-updater (needs COPILOT_GITHUB_TOKEN)
    "ss-hygiene-doc-updater.md",
    "ss-hygiene-doc-updater.lock.yml",
    # Cloudflare Workers Builds only: runs the URL-driven checks against
    # each deployed preview and the live site.
    "ss-cloudflare-deployed.yml",
)

SKILLS: tuple[str, ...] = ("slopstopper-install", "slopstopper-triage")

# Skill directories an earlier release wrote under .claude/skills/ that a
# refresh removes: the single-skill name, and the refresh skill that was
# folded into slopstopper-install.
OBSOLETE_SKILLS: tuple[str, ...] = ("install-slopstopper", "slopstopper-update")

# Composite actions slopstopper stopped shipping or renamed; a refresh
# deletes the old directory.
OBSOLETE_ACTIONS: tuple[str, ...] = ()

TASKFILE = "Taskfile.ss.yml"
PACKAGE_JSON = "package.json"
HOOK = ".githooks/pre-push"
TEMPLATES_DIR = "templates"
WORKFLOWS_DIR = ".github/workflows"
ACTIONS_DIR = ".github/actions"
SKILLS_DIR = ".claude/skills"

_REFERENCE_RE = re.compile(r"references/[A-Za-z0-9_.-]+\.md")


class SuiteMissing(RuntimeError):
    """The CLI can find neither a packaged suite nor a checkout to serve it from."""


def packaged_root() -> Path:
    """Where the build hook puts the suite inside the wheel."""
    return PACKAGE_DATA_DIR / "suite"


def source_root() -> Path:
    """The directory the suite is served from.

    The packaged copy when this is an installed wheel; otherwise the
    repository root above an editable install, recognised by the files the
    installer needs and the CLI's own project file.
    """
    packaged = packaged_root()
    if (packaged / TASKFILE).is_file():
        return packaged
    for candidate in PACKAGE_DATA_DIR.parents:
        if (candidate / TASKFILE).is_file() and (candidate / "cli" / "pyproject.toml").is_file():
            return candidate
    raise SuiteMissing(
        "this slopstopper-cli carries no suite to install: neither a packaged copy "
        f"under {packaged} nor a checkout above {PACKAGE_DATA_DIR}"
    )


def skill_files(root: Path, skill: str) -> list[str]:
    """The files a skill ships, relative to `root`: SKILL.md and every
    `references/<name>.md` it links. Only linked files, so a draft or an
    editor's leftover in the source tree never reaches an adopter."""
    skill_md = Path(SKILLS_DIR) / skill / "SKILL.md"
    text = (root / skill_md).read_text(encoding="utf-8")
    refs = sorted(set(_REFERENCE_RE.findall(text)))
    return [skill_md.as_posix()] + [(Path(SKILLS_DIR) / skill / ref).as_posix() for ref in refs]


def shipped_paths(root: Path) -> list[str]:
    """Every file the installer reads from `root`, relative to it, in a
    stable order. The build hook copies exactly these into the wheel."""
    paths = [TASKFILE, PACKAGE_JSON, HOOK]
    paths += sorted(
        p.relative_to(root).as_posix() for p in (root / TEMPLATES_DIR).iterdir() if p.is_file()
    )
    paths += [f"{WORKFLOWS_DIR}/{name}" for name in GENERIC_WORKFLOWS]
    for action in sorted((root / ACTIONS_DIR).glob("ss-*")):
        if action.is_dir():
            paths += sorted(p.relative_to(root).as_posix() for p in action.rglob("*") if p.is_file())
    for skill in SKILLS:
        paths += skill_files(root, skill)
    return paths
