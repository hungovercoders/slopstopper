"""`slopstopper install`: write the suite into a repo.

Everything an adopter's repo carries comes from the suite this CLI ships
(see `slopstopper.suite`): the `task ss:*` shims, the `ss-*.yml` workflows
and the composite actions they build on, the seeds, the pre-push hook and
the two Claude Code skills. The pin in `mise.toml` is seeded with this
CLI's own version when the repo has none, so the shims and the CLI that
runs them agree by construction.

A re-run is a refresh. Slopstopper-owned files (the shims, the workflows,
the actions, the hook, the skills, the block in `.gitignore`) are replaced;
adopter-owned files (`.slopstopper.yml`, `package.json`, the seeds, the
headers file) are seeded only when absent. A workflow the adopter deleted
stays deleted: `.ss/.workflows-installed` lists every workflow the installer
has placed, so one listed there and missing from disk is a choice, and
removing its line is how to have it back. A profile drops whole sets and
`workflows.enabled` takes one back.

Configuration (.slopstopper.yml, read from the target):

    profile: ui           # which workflows the repo carries; --profile writes it
    workflows:
      disabled: []        # adds to the profile's set
      enabled: []         # takes one back
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from slopstopper import __version__, config, emit, output, profiles, suite, workflow_state
from slopstopper.templates import PACKAGE_DATA_DIR

REPO_URL = "https://github.com/hungovercoders/slopstopper"
MARKER = ".ss/.workflows-installed"
INSTALLED_FROM = ".ss/.installed-from"
DEFAULT_NODE_VERSION = "20"
MISE_CONFIGS = ("mise.toml", ".mise.toml", "mise.local.toml", ".config/mise/config.toml")
HEADERS_BEGIN = "# slopstopper security headers begin"
GITIGNORE_BEGIN = "# slopstopper begin"
GITIGNORE_END = "# slopstopper end"
CLOUDFLARE_TRIGGER = "ss-cloudflare-deployed.yml"

# Which URL-driven checks the banner lists, from what landed on disk.
DYNAMIC_LABELS = (
    ("ss-reliability-smoke-tests.yml", "Smoke"),
    ("ss-reliability-e2e-check.yml", "E2E"),
    ("ss-reliability-accessibility-check.yml", "Accessibility"),
    ("ss-reliability-core-web-vitals.yml", "Core Web Vitals"),
    ("ss-security-dast-check.yml", "DAST"),
    ("ss-reliability-seo-check.yml", "SEO"),
    ("ss-reliability-broken-links-check.yml", "Broken Links"),
    ("ss-reliability-llms-txt-check.yml", "llms.txt"),
    ("ss-reliability-robots-txt-check.yml", "robots.txt"),
    ("ss-reliability-sitemap-check.yml", "Sitemap"),
    ("ss-reliability-api-health-check.yml", "API Health"),
    ("ss-reliability-api-latency-check.yml", "API Latency"),
    ("ss-security-api-headers-check.yml", "API Headers"),
    ("ss-hygiene-openapi-check.yml", "OpenAPI Drift"),
)

# Files the CLI used to copy under .ss/ and now serves from the wheel; an
# unmodified copy is removed, a customised one stays as an override.
LEGACY_OVERLAY = ("playwright.config.js", "lighthouserc.json", "lighthouserc.prod.json", "server.js")


@dataclass
class Options:
    target: Path
    profile: str | None = None
    use_task: bool = True
    skills: bool = True
    hooks: bool = True
    topic: bool = True


@dataclass
class State:
    """What the steps found out, for the banner at the end."""

    profile_active: str = "ui"
    profile_skipped: int = 0
    profile_removed: int = 0
    installed: int = 0
    refreshed: int = 0
    deleted_respected: int = 0
    disabled: set[str] = field(default_factory=set)
    pinned: str = __version__


class InstallError(Exception):
    """A condition the installer refuses to continue from; the message is printed."""


# ── helpers ──────────────────────────────────────────────────────


def _sep() -> None:
    output.separator()


def _line(text: str = "") -> None:
    output._emit(text)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


# ── shims and config ─────────────────────────────────────────────

TASKFILE_INCLUDE = "version: '3'\n\nincludes:\n  ss:\n    taskfile: ./Taskfile.ss.yml\n"


def install_taskfiles(root: Path, target: Path) -> None:
    _copy(root / suite.TASKFILE, target / suite.TASKFILE)
    output.success("Taskfile.ss.yml installed (refreshed)")
    taskfile = target / "Taskfile.yml"
    if not taskfile.is_file():
        _write(taskfile, TASKFILE_INCLUDE)
        output.success("Taskfile.yml installed")
        return
    text = _read(taskfile)
    if re.search(r"^\s+ss:\s*$", text, re.M) or "Taskfile.ss.yml" in text:
        output.info("Taskfile.yml already references Taskfile.ss.yml, so no changes are needed")
        return
    output.warn("Taskfile.yml already exists, so leaving it alone.")
    _line()
    _line("  Add the following block to your existing Taskfile.yml so the")
    _line("  SlopStopper tasks become available as 'task ss:<name>':")
    _line()
    _line("    includes:")
    _line("      ss:")
    _line("        taskfile: ./Taskfile.ss.yml")
    _line()


def seed_config(root: Path, target: Path) -> None:
    """The starter: the keys most repos set, with a pointer to the schema."""
    cfg = target / ".slopstopper.yml"
    starter = root / suite.TEMPLATES_DIR / "slopstopper.yml.starter"
    if cfg.is_file() or not starter.is_file():
        return
    _copy(starter, cfg)
    output.success(f".slopstopper.yml: seeded as a starter. Every other key is in {REPO_URL}/blob/main/.slopstopper.yml.example")


PROFILE_BLOCK = (
    "\n# ── Project-shape profile ────────────────────────────────\n"
    "# Which checks apply to a repo of this shape. See\n"
    "# `slopstopper profile list` for the full mapping.\n"
)


def write_profile_key(target: Path, name: str) -> str:
    """Set `profile: <name>` in the config: replaced in place, or appended
    with its comment when the file predates the key. Returns what happened."""
    cfg = target / ".slopstopper.yml"
    if not cfg.is_file():
        return "missing"
    lines = _read(cfg).splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("profile:"):
            if line.strip() == f"profile: {name}":
                return "unchanged"
            lines[i] = f"profile: {name}\n"
            _write(cfg, "".join(lines))
            return "replaced"
    _write(cfg, "".join(lines) + PROFILE_BLOCK + f"profile: {name}\n")
    return "appended"


def apply_profile_flag(target: Path, name: str) -> None:
    outcome = write_profile_key(target, name)
    if outcome == "unchanged":
        output.info(f".slopstopper.yml: profile already '{name}'")
    elif outcome == "replaced":
        output.success(f".slopstopper.yml: profile set to '{name}'")
    elif outcome == "appended":
        output.success(f".slopstopper.yml: profile '{name}' added")
    else:
        output.warn(f".slopstopper.yml: no config file in target, so profile '{name}' was not written")


# ── the toolchain pin ────────────────────────────────────────────


def mise_config_path(target: Path) -> Path:
    """The target's mise config: an existing one, so a second is never
    created beside an adopter's, else mise.toml."""
    for name in MISE_CONFIGS:
        if (target / name).is_file():
            return target / name
    return target / "mise.toml"


def _tool_pattern(key: str) -> re.Pattern[str]:
    return re.compile(rf'^\s*"?{re.escape(key)}"?\s*=', re.M)


def has_mise_tool(cfg: Path, key: str) -> bool:
    return cfg.is_file() and bool(_tool_pattern(key).search(_read(cfg)))


def read_mise_tool(cfg: Path, key: str) -> str | None:
    """The version a [tools] entry pins, or None when there is no entry."""
    if not cfg.is_file():
        return None
    match = re.search(rf'^\s*"?{re.escape(key)}"?\s*=\s*"([^"]*)"', _read(cfg), re.M)
    return match.group(1) if match else None


def seed_mise_tool(cfg: Path, key: str, version: str) -> bool:
    """Add a [tools] entry when there is none: the file and the section are
    created when absent, other entries are left as they are. Returns whether
    the entry was written."""
    if has_mise_tool(cfg, key):
        return False
    line = f'"{key}" = "{version}"'
    if not cfg.is_file():
        _write(cfg, f"[tools]\n{line}\n")
        return True
    text = _read(cfg)
    if not text.endswith("\n"):
        text += "\n"
    if re.search(r"^\[tools\]", text, re.M):
        _write(cfg, re.sub(r"^\[tools\]\n", f"[tools]\n{line}\n", text, count=1, flags=re.M))
    else:
        _write(cfg, text + f"\n[tools]\n{line}\n")
    return True


def read_legacy_key(cfg: Path, key: str) -> str | None:
    """A pre-mise `cli_version:` or `node_version:` in .slopstopper.yml."""
    if not cfg.is_file():
        return None
    match = re.search(rf"^{key}:\s*[\"']?([0-9][0-9.]*)", _read(cfg), re.M)
    return match.group(1) if match else None


def strip_legacy_key(cfg: Path, key: str, heading: str) -> None:
    """Drop a dead `<key>:` line and the comment block that introduced it."""
    if not cfg.is_file() or not re.search(rf"^{key}:", _read(cfg), re.M):
        return
    kept, skipping = [], False
    for line in _read(cfg).splitlines(keepends=True):
        if line.startswith(heading):
            skipping = True
            continue
        if line.startswith(f"{key}:"):
            skipping = False
            continue
        if not skipping:
            kept.append(line)
    _write(cfg, "".join(kept))


def target_has_node_pin(target: Path, cfg: Path) -> bool:
    return (target / ".node-version").is_file() or (target / ".nvmrc").is_file() or has_mise_tool(cfg, "node")


def seed_toolchain_pin(target: Path) -> str:
    """Pin this CLI, task and node in the mise config when the repo has no
    pin yet, and return the pinned CLI version. An existing pin is never
    moved: `install.sh --upgrade-cli` and `--cli-version` are the two
    commands that do that."""
    cfg = target / ".slopstopper.yml"
    mcfg = mise_config_path(target)
    legacy = read_legacy_key(cfg, "cli_version")
    strip_legacy_key(cfg, "cli_version", "# ── slopstopper-cli version pin")
    strip_legacy_key(cfg, "node_version", "# ── Node version pin")
    if seed_mise_tool(mcfg, "pipx:slopstopper-cli", legacy or __version__):
        output.success(f"slopstopper-cli {legacy or __version__} pinned in {mcfg.name}")
    seed_mise_tool(mcfg, "task", "3")
    if not target_has_node_pin(target, mcfg):
        seed_mise_tool(mcfg, "node", DEFAULT_NODE_VERSION)
    return read_mise_tool(mcfg, "pipx:slopstopper-cli") or __version__


# ── the .ss/ overlay ─────────────────────────────────────────────


def scrub_legacy_overlay(target: Path) -> None:
    """Remove what earlier releases copied under .ss/ and the wheel now
    serves: the scripts directory, and any byte-equal template copy."""
    ss = target / ".ss"
    ss.mkdir(exist_ok=True)
    if (ss / "scripts").is_dir():
        shutil.rmtree(ss / "scripts")
        output.success(".ss/scripts/ removed (logic now lives in slopstopper-cli)")
    candidates = list(LEGACY_OVERLAY)
    if (ss / "tests").is_dir():
        candidates += [f"tests/{p.name}" for p in (PACKAGE_DATA_DIR / "tests").glob("*.spec.ts")]
    for rel in candidates:
        adopter, packaged = ss / rel, PACKAGE_DATA_DIR / rel
        if adopter.is_file() and packaged.is_file() and adopter.read_bytes() == packaged.read_bytes():
            adopter.unlink()
            output.success(f".ss/{rel} removed (unmodified copy of package-data fallback)")
    tests = ss / "tests"
    if tests.is_dir() and not any(tests.iterdir()):
        tests.rmdir()


# ── workflows and actions ────────────────────────────────────────


def is_cloudflare_repo(target: Path) -> bool:
    """A worker/ directory, or a wrangler config at the root or one level
    down (a site in website/ or app/ keeps it beside its package.json)."""
    if (target / "worker").is_dir():
        return True
    for pattern in ("wrangler.toml", "wrangler.jsonc", "wrangler.json", "*/wrangler.toml", "*/wrangler.jsonc", "*/wrangler.json"):
        for path in target.glob(pattern):
            if "node_modules" not in path.parts and path.is_file():
                return True
    return False


def _previous_marker(target: Path) -> set[str]:
    """The workflows the last run installed. A marker that lists workflows
    while none is on disk is left over from another branch, not a deletion
    of every check, so it is ignored with a warning."""
    marker = target / MARKER
    if not marker.is_file():
        return set()
    names = {line.strip() for line in _read(marker).splitlines() if line.strip()}
    on_disk = list((target / suite.WORKFLOWS_DIR).glob("ss-*.yml"))
    if names and not on_disk:
        output.warn(
            f"Stale .ss/.workflows-installed detected ({len(names)} entries, 0 workflows on disk), "
            "so treating this as a fresh install and re-adding all workflows. If you genuinely "
            "deleted every workflow, set workflows.disabled in .slopstopper.yml instead so the "
            "choice survives re-runs."
        )
        return set()
    return names


def install_workflows(root: Path, target: Path, state: State) -> None:
    src_dir, dst_dir = root / suite.WORKFLOWS_DIR, target / suite.WORKFLOWS_DIR
    dst_dir.mkdir(parents=True, exist_ok=True)
    previous = _previous_marker(target)
    cloudflare = is_cloudflare_repo(target)
    marker: list[str] = []
    for name in suite.GENERIC_WORKFLOWS:
        src, dst = src_dir / name, dst_dir / name
        if not src.is_file():
            continue
        if name == CLOUDFLARE_TRIGGER and not cloudflare:
            dst.unlink(missing_ok=True)
            continue
        if name in state.disabled:
            if dst.is_file():
                dst.unlink()
                state.profile_removed += 1
            state.profile_skipped += 1
            continue
        if name in previous and not dst.is_file():
            state.deleted_respected += 1
            marker.append(name)
            continue
        if dst.is_file():
            state.refreshed += 1
        else:
            state.installed += 1
        _copy(src, dst)
        marker.append(name)
    _write(target / MARKER, "".join(f"{name}\n" for name in marker))
    output.success(
        f"{state.installed} workflow(s) installed, {state.refreshed} refreshed, "
        f"{state.deleted_respected} previously-deleted skipped"
    )


def install_actions(root: Path, target: Path) -> None:
    """The composite actions every workflow starts with: plumbing, so always
    copied, replaced wholesale, never tracked in the marker."""
    src_dir, dst_dir = root / suite.ACTIONS_DIR, target / suite.ACTIONS_DIR
    dst_dir.mkdir(parents=True, exist_ok=True)
    for obsolete in suite.OBSOLETE_ACTIONS:
        if (dst_dir / obsolete).is_dir():
            shutil.rmtree(dst_dir / obsolete)
            output.info(f"removed obsolete composite action .github/actions/{obsolete}")
    names = []
    for action in sorted(src_dir.glob("ss-*")):
        if not action.is_dir():
            continue
        if (dst_dir / action.name).exists():
            shutil.rmtree(dst_dir / action.name)
        shutil.copytree(action, dst_dir / action.name)
        names.append(action.name)
    output.success(f"composite actions refreshed under .github/actions/ ({', '.join(names)})")


_TASK_WITH_ARGS = re.compile(r"task (?:-x )?ss:([a-z][a-z0-9_:-]+) -- ")
_TASK_BARE = re.compile(r"task (?:-x )?ss:([a-z][a-z0-9_:-]+)")


def rewrite_without_task(target: Path) -> None:
    """`--no-task`: every `task ss:<check>` becomes `slopstopper run <check>`."""
    transformed = 0
    for path in sorted((target / suite.WORKFLOWS_DIR).glob("ss-*.yml")):
        text = _read(path)
        rewritten = _TASK_BARE.sub(r"slopstopper run \1", _TASK_WITH_ARGS.sub(r"slopstopper run \1 ", text))
        if rewritten != text:
            _write(path, rewritten)
            transformed += 1
    output.success(f"Post-processed {transformed} workflow(s) for --no-task mode (invocations rewritten to slopstopper-cli)")


def sweep_disabled(target: Path, disabled: set[str]) -> None:
    """Remove disabled workflows the install loop did not cover: one from an
    older release, or one the adopter added and then listed."""
    removed = 0
    for name in sorted(disabled):
        path = target / suite.WORKFLOWS_DIR / name
        if path.is_file():
            path.unlink()
            removed += 1
    if removed:
        output.info(f"Removed {removed} further workflow(s) from the disabled set")


# ── package.json ─────────────────────────────────────────────────


def install_package_json(root: Path, target: Path) -> None:
    """Merge the suite's devDependencies into the adopter's manifest, or
    write a minimal one named after the repo."""
    pkg = target / "package.json"
    dev = json.loads(_read(root / suite.PACKAGE_JSON)).get("devDependencies", {})
    if not pkg.is_file():
        name = re.sub(r"[^a-z0-9._-]+", "-", target.resolve().name.lower()).strip("-._") or "site"
        _write(pkg, json.dumps({"name": name, "private": True, "devDependencies": dev}, indent=2) + "\n")
        output.success("package.json created (devDependencies only; add scripts.build if your site needs building)")
        return
    try:
        manifest = json.loads(_read(pkg))
    except ValueError:
        output.warn("package.json: not valid JSON, so slopstopper's devDependencies were not added")
        return
    existing = manifest.setdefault("devDependencies", {})
    added = [k for k in dev if k not in existing]
    conflicts = [f"{k}: existing={existing[k]} template={v}" for k, v in dev.items() if k in existing and existing[k] != v]
    if added:
        for k in added:
            existing[k] = dev[k]
        _write(pkg, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        output.success(f"Added devDependencies: {', '.join(added)}")
    else:
        output.info("No new devDependencies to add")
    if conflicts:
        output.warn(f"Version conflicts (your version kept): {'; '.join(conflicts)}")


# ── seeds ────────────────────────────────────────────────────────


def seed(label: str, src: Path, dst: Path) -> None:
    """Copy `src` to `dst` only when `dst` is absent; never overwrite."""
    if not src.is_file():
        return
    if dst.is_file():
        output.info(f"{label}: already exists, so leaving it alone")
        return
    _copy(src, dst)
    output.success(f"{label}: seeded")


def _headers_configured(text: str) -> bool:
    return bool(re.search(r"^\s*(Content-Security-Policy|Strict-Transport-Security|X-Content-Type-Options):", text, re.M | re.I))


def seed_headers_block(root: Path, target: Path) -> None:
    """The commented security-headers baseline, appended between markers to
    a headers file that holds only cache rules. A file that already sets a
    security header is the adopter's policy and gets nothing."""
    if not (target / "public").is_dir():
        output.info("public/_headers: no public/ directory in target, so skipping. Add one and re-run if you want the baseline.")
        return
    src, dst = root / suite.TEMPLATES_DIR / "_headers.example", target / "public" / "_headers"
    if not src.is_file():
        return
    existing = _read(dst) if dst.is_file() else ""
    if HEADERS_BEGIN in existing:
        output.info("public/_headers: slopstopper security headers block already present, so leaving it alone")
        return
    if _headers_configured(existing):
        output.info("public/_headers: already sets security headers, so leaving it alone (the baseline is templates/_headers.example upstream)")
        return
    if existing.strip():
        _write(dst, existing + "\n" + _read(src))
        output.success("public/_headers: appended slopstopper security headers block (commented; uncomment to enable)")
    else:
        _copy(src, dst)
        output.success("public/_headers: seeded")


def seed_templates(root: Path, target: Path) -> None:
    templates = root / suite.TEMPLATES_DIR
    seed(".github/labeler.yml", templates / "labeler.yml.example", target / ".github" / "labeler.yml")
    seed(".github/dependency-review-config.yml", templates / "dependency-review-config.yml.example", target / ".github" / "dependency-review-config.yml")
    seed_headers_block(root, target)
    seed(".zap/rules.tsv", templates / "zap-rules.tsv.example", target / ".zap" / "rules.tsv")
    seed(".markdownlint.json", templates / "markdownlint.json.example", target / ".markdownlint.json")
    entry = PACKAGE_DATA_DIR / "templates" / "entry-files"
    for name in ("README.md", "AGENTS.md", "CLAUDE.md"):
        seed(name, entry / name, target / name)
    if (target / "docs" / "index.md").is_file() and not (target / "docs" / "README.md").is_file():
        output.warn(
            "docs/index.md is the pre-0.15 map and the map is docs/README.md now. Run `git mv docs/index.md "
            "docs/README.md` and rewrite its rows as routes (task ss:hygiene:entry-files explains how)."
        )
    else:
        seed("docs/README.md", entry / "docs" / "README.md", target / "docs" / "README.md")


def refresh_gitignore_block(root: Path, target: Path) -> None:
    """The block between the markers is slopstopper-owned and replaced each
    run; lines outside it are never touched. A begin marker with no end
    marker is a hand-edited block, so it is left alone with a warning."""
    src = root / suite.TEMPLATES_DIR / "gitignore.block"
    if not src.is_file():
        return
    block = _read(src)
    if not block.endswith("\n"):
        block += "\n"
    gi = target / ".gitignore"
    existing = _read(gi) if gi.is_file() else ""
    if GITIGNORE_BEGIN not in existing:
        _write(gi, (existing + "\n" if existing.strip() else existing) + block)
        output.success(".gitignore: appended slopstopper block")
        return
    lines = existing.splitlines(keepends=True)
    begin = next((i for i, line in enumerate(lines) if line.strip() == GITIGNORE_BEGIN), None)
    end = None if begin is None else next((i for i in range(begin, len(lines)) if lines[i].strip() == GITIGNORE_END), None)
    if begin is None:
        output.warn(".gitignore: mentions '# slopstopper begin' but has no line that is exactly that marker, so the block was left alone. Restore the marker line and re-run to refresh it.")
    elif end is None:
        output.warn(".gitignore: '# slopstopper begin' has no '# slopstopper end', so the block was left alone. Restore the end marker and re-run to refresh it.")
    elif "".join(lines[begin:end + 1]) == block:
        output.info(".gitignore: slopstopper block already current")
    else:
        _write(gi, "".join(lines[:begin]) + block + "".join(lines[end + 1:]))
        output.success(".gitignore: slopstopper block updated to the current template")


# ── skills ───────────────────────────────────────────────────────


def _skill_contents(root: Path, skill: str) -> dict[str, bytes] | None:
    try:
        files = suite.skill_files(root, skill)
    except OSError:
        output.warn(f"{skill}: SKILL.md is missing from this slopstopper-cli")
        return None
    out = {}
    for rel in files:
        path = root / rel
        if not path.is_file():
            output.warn(f"{skill}: {Path(rel).relative_to(Path(suite.SKILLS_DIR) / skill)} is linked from SKILL.md but missing")
            return None
        out[Path(rel).relative_to(Path(suite.SKILLS_DIR) / skill).as_posix()] = path.read_bytes()
    if not out["SKILL.md"].startswith(b"---\n"):
        output.warn(f"{skill}: SKILL.md does not look like a Claude Code skill (no frontmatter)")
        return None
    return out


def _installed_contents(directory: Path) -> dict[str, bytes]:
    return {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob("*") if p.is_file()}


def _recover_skill_swap(dest: Path, skill: str) -> None:
    """A run interrupted mid-swap leaves `<skill>.outgoing.<pid>` beside a
    missing skill, and an older installer could leave `.incoming.<pid>`
    too; Claude Code reads every directory there as a skill, so put the
    outgoing copy back when nothing replaced it and drop the rest."""
    for leftover in sorted(dest.parent.glob(f"{skill}.outgoing.*")):
        if dest.exists():
            shutil.rmtree(leftover)
        else:
            leftover.rename(dest)
    for leftover in dest.parent.glob(f"{skill}.incoming.*"):
        shutil.rmtree(leftover)


def install_skill(root: Path, target: Path, skill: str) -> bool:
    """Write one skill as a whole directory, staged under .ss/ and swapped
    into place only once every file is there, so a failure leaves the
    installed copy as it was."""
    contents = _skill_contents(root, skill)
    if contents is None:
        return False
    dest = target / suite.SKILLS_DIR / skill
    if dest.parent.is_dir():
        _recover_skill_swap(dest, skill)
    if dest.is_dir() and _installed_contents(dest) == contents:
        output.info(f"{skill}: already up to date")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".skill-", dir=target / ".ss"))
    try:
        incoming = staging / skill
        for rel, data in contents.items():
            (incoming / rel).parent.mkdir(parents=True, exist_ok=True)
            (incoming / rel).write_bytes(data)
        had_it = dest.is_dir()
        outgoing = staging / f"{skill}.outgoing"
        if had_it:
            dest.rename(outgoing)
        incoming.rename(dest)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    output.success(f"{skill}: refreshed" if had_it else f"{skill}: installed")
    return True


def install_skills(root: Path, target: Path) -> None:
    _line()
    _sep()
    _line("  🧠  Installing the SlopStopper Claude Code skills (project level)…")
    _sep()
    failed = [skill for skill in suite.SKILLS if not install_skill(root, target, skill)]
    for obsolete in suite.OBSOLETE_SKILLS:
        stale = target / suite.SKILLS_DIR / obsolete
        if stale.is_dir():
            shutil.rmtree(stale)
            output.info(f"Removed obsolete skill: {obsolete}")
    home = Path.home() / ".claude" / "skills"
    if any((home / name).is_dir() for name in (*suite.SKILLS, *suite.OBSOLETE_SKILLS)):
        output.warn("Stale user-level skills detected at ~/.claude/skills/slopstopper-*.")
        output.info("They'll shadow the project-level copies you just installed. Clean up with:")
        output.info("  rm -rf " + " ".join(f"~/.claude/skills/{name}" for name in (*suite.SKILLS, *suite.OBSOLETE_SKILLS)))
    if failed:
        output.warn(f"Claude Code skills not fully installed (non-fatal): {', '.join(failed)}. Any installed copy was left as it was; re-run to retry.")


# ── the pre-push hook ────────────────────────────────────────────


def _has_hook_manager(target: Path) -> bool:
    result = _run(["git", "config", "--local", "--get", "core.hooksPath"], target)
    existing = result.stdout.strip()
    if existing and existing != ".githooks":
        return True
    return any((target / name).exists() for name in (".husky", "lefthook.yml", ".lefthook.yml", "lefthook.yaml", ".pre-commit-config.yaml"))


def install_hook(root: Path, target: Path) -> None:
    """Wire the hygiene gate before every push, unless the repo already
    manages its hooks, in which case the file lands and the wiring is a
    one-line opt-in."""
    src = root / suite.HOOK
    if not src.is_file():
        return
    if shutil.which("git") is None:
        output.info("git not found, so skipping the pre-push hook.")
        return
    if _run(["git", "rev-parse", "--git-dir"], target).returncode != 0:
        output.info("Target is not a git repository, so skipping the pre-push hook.")
        return
    dst = target / suite.HOOK
    _copy(src, dst)
    dst.chmod(dst.stat().st_mode | 0o111)
    if _has_hook_manager(target):
        output.success("pre-push hook written to .githooks/pre-push (refreshed)")
        output.warn("You already manage git hooks, so leaving core.hooksPath alone.")
        output.info("To enable the slopstopper gate, either run:")
        output.info("    git config core.hooksPath .githooks")
        output.info("  or add 'task ss:hygiene:test' to your existing hook manager.")
        return
    _run(["git", "config", "core.hooksPath", ".githooks"], target)
    output.success("pre-push hook installed (core.hooksPath → .githooks)")
    output.info("Pushes now run 'task ss:hygiene:test' locally first. Bypass once with 'git push --no-verify'.")


# ── the banner ───────────────────────────────────────────────────


def ensure_repo_topic() -> str:
    """Add the `slopstopper` topic through gh: added, present, denied (gh
    sees the repo but can't edit it) or skipped (gh missing, unauthenticated
    or not a GitHub repo). Never fails the install."""
    if shutil.which("gh") is None:
        return "skipped"
    view = emit._gh("repo", "view", "--json", "repositoryTopics", "--jq", ".repositoryTopics[].name", capture=True)
    if view.returncode != 0:
        return "skipped"
    if "slopstopper" in view.stdout.split():
        return "present"
    return "added" if emit._gh("repo", "edit", "--add-topic", "slopstopper", capture=True).returncode == 0 else "denied"


def _print_topic(target: Path) -> None:
    outcome = ensure_repo_topic()
    if outcome == "added":
        _line("  🏷  Repo topic 'slopstopper' added, so this repo is discoverable as an adopter.")
    elif outcome == "present":
        _line("  🏷  Repo topic 'slopstopper' already set.")
    elif outcome == "denied":
        _line("  🏷  Repo topic 'slopstopper' not set: gh sees the repo but can't edit it (topics need admin).")
        _line("       Ask a repo admin to run: gh repo edit --add-topic slopstopper")
    else:
        _line("  🏷  Repo topic 'slopstopper' not set: gh can't reach this repo. Add it with:")
        _line("       gh repo edit --add-topic slopstopper")
    _line()


def _print_profile(target: Path, opts: Options, state: State) -> None:
    entry = profiles.describe(state.profile_active) or {}
    _line("  ── SlopStopper status for this repo ──────────────────────────────")
    _line()
    _line(f"  🧭 Profile: {state.profile_active}")
    _line(f"       {entry.get('summary', '')}")
    if state.profile_skipped:
        _line(f"       {state.profile_skipped} check(s) left out as not applying to this shape.")
        _line("       'slopstopper profile show' lists them; workflows.enabled keeps one.")
    held = sorted(set(profiles.without_api(state.profile_active)) & state.disabled) if not profiles.api_signal(target) else []
    if held:
        n = len(held)
        _line("       No API found (no OpenAPI spec, server framework or configured API check),")
        _line(f"       so {n} API check{'' if n == 1 else 's'} {'isn' if n == 1 else 'aren'}'t installed. To add them, set api.* in")
        _line("       .slopstopper.yml (or list them under workflows.enabled) and re-run.")
    _line()
    if opts.profile:
        return
    detected, reason = profiles.detect(target)
    if detected != state.profile_active:
        _line(f"  💡 This looks more like a '{detected}' repo ({reason}),")
        _line("     which would drop the checks that don't apply to that shape.")
        _line("     To switch, set this in .slopstopper.yml and re-run slopstopper install:")
        _line()
        _line(f"       profile: {detected}")
        _line()
        _line("     Nothing was changed for you. See 'slopstopper profile list'.")
        _line()


def _print_github_disabled() -> None:
    rows = workflow_state.disabled_ss_workflows() or []
    if not rows:
        return
    _line(f"  ⛔ GitHub has switched off {len(rows)} slopstopper workflow(s). They run on no trigger, PRs included:")
    for row in rows:
        _line(f"       {row.get('name')} ({row.get('state')}) → {workflow_state.enable_command(row)}")
    _line("     GitHub disables scheduled workflows after 60 days without repo activity.")
    _line()


def _print_checks(target: Path, opts: Options, state: State) -> None:
    _line("  ✅ Active now on any code, with no config needed:")
    _line("       SAST · Secrets · Dependency CVEs · Dependency Review")
    _line("       Complexity · Doc Structure · Doc Accuracy · Doc Size")
    _line("       Auto-label PRs · Workflow-failure tracker")
    _line()
    if opts.hooks:
        _line("  🪝 Local pre-push gate: the hygiene checks run before every push")
        _line("       (task ss:hygiene:test) so CI confirms rather than discovers.")
        _line("       Bypass a single push with 'git push --no-verify'.")
        _line()
    labels = [label for name, label in DYNAMIC_LABELS if (target / suite.WORKFLOWS_DIR / name).is_file()]
    if labels:
        _line("  ⏳ Active once you point them at your app (edit .slopstopper.yml):")
        _line(f"       {' · '.join(labels)}")
        _line()
        _line("     # in .slopstopper.yml:")
        _line("     urls:")
        _line("       production: https://your-site.example.com")
        _line("       preview:    https://staging.your-site.example.com")
        _line()
        _line("     # if you need a different Node version for your build (pinned in")
        _line("     # mise.toml, read by mise locally and CI):")
        _line("     mise use node@22")
        _line()
    else:
        _line(f"  💤 URL-driven checks: none installed. Profile '{state.profile_active}' has no")
        _line("       served surface to audit, so nothing here needs a URL.")
        _line("       Take one back with workflows.enabled in .slopstopper.yml.")
        _line()
    _line("  🔐 Inert until you add secrets in your repo settings:")
    _line("       Doc Auto-Updater (gh-aw agentic workflow)")
    _line("         → COPILOT_GITHUB_TOKEN")
    _line("         → Settings → Actions → General →")
    _line("           'Allow GitHub Actions to create and approve pull requests'")
    _line("         → See docs/hygiene/DOC_UPDATER.md for the full setup")
    _line()


def _print_deploy(target: Path) -> None:
    if is_cloudflare_repo(target):
        _line("  🚀 Cloudflare config detected. Deploy is handled by Cloudflare, not by")
        _line("     a workflow in this suite:")
        _line("       Cloudflare dash → Workers & Pages → Create → Connect to Git")
        _line("       Pushes deploy to prod, PRs get preview URLs, closing a PR")
        _line("       cleans up the preview. No GitHub secrets required.")
        _line("       ss-cloudflare-deployed.yml runs the URL-driven checks against")
        _line("       each preview and, on the default branch, urls.production.")
        _line("       See docs/deployment/README.md for the full cutover steps.")
    else:
        _line("  🚀 Deploy stays wherever it is today; this suite doesn't deploy.")
        _line("       Point urls.production in .slopstopper.yml at the deployed site")
        _line("       (including any sub-path) so scheduled and main runs audit it.")
    _line()
    _line("  If you don't use the doc-updater, delete its workflows from")
    _line("  .github/workflows/. Re-running the installer won't bring them")
    _line("  back (tracked via .ss/.workflows-installed).")
    _line()


def _print_next_steps(opts: Options) -> None:
    _sep()
    _line()
    if opts.use_task:
        _line("  Canonical invocation: task ss:<check>")
        _line()
        _line("    Workflows are Task-driven by default. They call task ss:<check>,")
        _line("    which is the canonical interface for humans, agents and CI alike,")
        _line("    so the suite sits naturally alongside any other task build / task")
        _line("    deploy tasks in your codebase. The workflows install Task")
        _line("    themselves; locally, mise installs the one pinned in mise.toml.")
        _line()
        _line("    Don't want Task in your CI? Re-run with --no-task to get")
        _line("    workflows that call slopstopper-cli directly:")
        _line()
        _line("       slopstopper install --no-task")
        _line()
        _line("  Next steps:")
        _line("    1. mise install                # the pinned slopstopper-cli, task and node")
        _line("    2. npm install")
        _line("    3. task --list")
        _line("    4. slopstopper badges          # generate README status badges (paste into README.md)")
        _line("    5. Open a PR and every check runs automatically.")
    else:
        _line("  Installed in --no-task mode.")
        _line()
        _line("    Workflows call slopstopper-cli directly (no Task install step,")
        _line("    no task ss:* invocations). To switch to the canonical Task-driven")
        _line("    flow later, re-run slopstopper install without --no-task.")
        _line()
        _line("  Next steps:")
        _line("    1. npm install")
        _line("    2. slopstopper checks list      # see every check shipped")
        _line("    3. slopstopper badges           # generate README status badges (paste into README.md)")
        _line("    4. Open a PR and every check runs automatically.")
    _line()
    _sep()


def print_banner(target: Path, opts: Options, state: State) -> None:
    _sep()
    _line()
    _line("  🎉 Installation complete!")
    _line()
    mcfg = mise_config_path(target).name
    _line(f"  📦 slopstopper-cli {__version__} wrote this suite; the pin in {mcfg} is what runs it.")
    if state.pinned != __version__:
        output.warn(f"The pin in {mcfg} is {state.pinned}, but slopstopper-cli {__version__} wrote this suite.")
        _line("     CI and the pre-push hook run the pin, so a check it does not know exits 2 ('unknown check') there.")
        _line(f"     Move the pin:  bash install.sh --cli-version {__version__}   (or: mise use pipx:slopstopper-cli@{__version__})")
        _line("     or write the pinned version's suite instead:  mise exec -- slopstopper install")
    _line()
    _print_profile(target, opts, state)
    _print_github_disabled()
    if opts.topic:
        _print_topic(target)
    _print_checks(target, opts, state)
    _print_deploy(target)
    _print_next_steps(opts)


# ── orchestration ────────────────────────────────────────────────


def preflight() -> None:
    """Say up front which tools the checks will need; none blocks the install."""
    soft = []
    if shutil.which("node") is None:
        soft.append("node (Playwright, Lighthouse CI, markdownlint, TypeScript): https://nodejs.org/")
    if shutil.which("mise") is None:
        soft.append("mise (installs the pinned slopstopper-cli, task and node from mise.toml): https://mise.jdx.dev")
    if shutil.which("docker") is None:
        output.info("Docker not found. Only DAST needs it, so the install carries on.")
    if soft:
        output.warn("The following tools aren't installed. You'll need them to run the checks SlopStopper installs:")
        for tool in soft:
            _line(f"      • {tool}")
        output.info("Continuing with install; install the tools above before running any task.")


def _validate(opts: Options) -> None:
    if not opts.target.is_dir():
        raise InstallError(f"Target directory does not exist: {opts.target}")
    if opts.profile and not profiles.describe(opts.profile):
        raise InstallError(f"Unknown --profile '{opts.profile}'. Expected one of: {' '.join(profiles.names())}")


def _resolve_profile(target: Path, state: State) -> None:
    config.reload()
    state.profile_active = profiles.active_name()
    state.disabled = profiles.effective_disabled()


def install(opts: Options) -> int:
    """Run every step against `opts.target`. Returns the exit code."""
    try:
        root = suite.source_root()
        _validate(opts)
    except (InstallError, suite.SuiteMissing) as exc:
        output.error(str(exc))
        return 1
    target = opts.target.resolve()
    preflight()
    _sep()
    _line("  🛠  SlopStopper: installing tooling")
    _line(f"  Source : slopstopper-cli {__version__} ({root})")
    _line(f"  Target : {target}")
    _sep()
    cwd = Path.cwd()
    os.chdir(target)
    try:
        _install_steps(root, target, opts)
    finally:
        os.chdir(cwd)
    return 0


def _install_steps(root: Path, target: Path, opts: Options) -> None:
    state = State()
    install_taskfiles(root, target)
    seed_config(root, target)
    if opts.profile:
        apply_profile_flag(target, opts.profile)
    state.pinned = seed_toolchain_pin(target)
    scrub_legacy_overlay(target)
    _resolve_profile(target, state)
    install_workflows(root, target, state)
    install_actions(root, target)
    if state.profile_skipped:
        output.info(f"profile '{state.profile_active}': {state.profile_skipped} workflow(s) not installed for this repo shape ({state.profile_removed} removed from a previous install)")
        output.info("  see 'slopstopper profile show'; list one under workflows.enabled in .slopstopper.yml to keep it")
    if not opts.use_task:
        rewrite_without_task(target)
    install_package_json(root, target)
    seed_templates(root, target)
    refresh_gitignore_block(root, target)
    sweep_disabled(target, state.disabled)
    if opts.skills:
        install_skills(root, target)
    else:
        output.info("Skipping Claude Code skill install (--no-skills / SLOPSTOPPER_NO_SKILLS).")
    if opts.hooks:
        install_hook(root, target)
    else:
        output.info("Skipping pre-push hook install (--no-hooks / SLOPSTOPPER_NO_HOOKS).")
    _write(target / INSTALLED_FROM, f"{__version__}\n")
    print_banner(target, opts, state)
