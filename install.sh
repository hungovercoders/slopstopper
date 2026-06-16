#!/usr/bin/env bash
# install.sh — installs the SlopStopper tooling into a target repository.
#
# Usage (from inside this repo):
#   ./install.sh [TARGET_DIR]
#
# Usage (recommended two-step from GitHub):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh -o install.sh
#   bash install.sh [TARGET_DIR]
#
# Usage (one-liner from GitHub, review the script first):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
#
# When piped from curl the script clones a temporary copy of the repo and
# installs from there, so no local checkout is required.
#
# Layout installed (all SlopStopper-owned files are under the `ss` namespace):
#
#   slopstopper-cli             # pip-installed (`pipx` preferred); every
#                               #   check now runs via `slopstopper run ...`.
#   Taskfile.yml                # thin root; created on fresh installs, left
#                               #   alone if you already have one (instructions
#                               #   printed in that case)
#   Taskfile.ss.yml             # all SlopStopper task shims; always
#                               #   refreshed on re-run so updates flow through
#   .ss/.workflows-installed    # manifest of installed workflows (commit this)
#   .ss/reports/                # SlopStopper-owned scan/report output dirs
#                               # (every CLI-managed file — Playwright specs,
#                               # Playwright config, lighthouserc dev/prod,
#                               # server.js — lives in the slopstopper-cli
#                               # wheel. To customise, `slopstopper templates
#                               # eject <name>` writes the file into .ss/ and
#                               # the CLI's templates resolver prefers it.)
#   .github/workflows/ss-*      # all SlopStopper workflows are ss- prefixed
#                               #   so they group together in the Actions UI
#                               #   and cannot clash with your existing workflows
#
# Workflow set ships in three conceptual layers:
#   1. Static analysis  — work on any code (SAST, Secrets, Trivy, complexity, doc checks)
#   2. Web-app dynamic  — need a URL (Smoke, Accessibility, CWV, DAST, SEO, Broken Links)
#   3. Agentic updater  — needs COPILOT_GITHUB_TOKEN (gh-aw doc-updater)
# Deploy is intentionally not a layer: connect your repo in the Cloudflare
# dash (Workers & Pages → Create → Connect to Git) and you get production
# deploys, PR previews and preview cleanup for free — no workflow needed.
# Don't use one of the layers? Delete its workflows from .github/workflows/.
# Re-running this installer will respect that deletion (it tracks what it
# installed in .ss/.workflows-installed).

set -euo pipefail

REPO_URL="https://github.com/hungovercoders/slopstopper.git"

# ── argument parsing ─────────────────────────────────────────────────────────
#
# Default mode ships Task-flavour workflows (every check is `task ss:<name>` —
# the canonical interface for humans, agents and CI alike). Adopters who'd
# rather skip Task in CI pass `--no-task` (or set SLOPSTOPPER_NO_TASK=1) and
# the workflows are post-processed at install time to call slopstopper-cli
# directly. See docs/architecture/ for the design rationale.

USE_TASK=true
if [ -n "${SLOPSTOPPER_NO_TASK:-}" ]; then
  USE_TASK=false
fi

INSTALL_SKILLS=true
if [ -n "${SLOPSTOPPER_NO_SKILLS:-}" ]; then
  INSTALL_SKILLS=false
fi

POSITIONAL=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-task)
      USE_TASK=false
      shift
      ;;
    --no-skills)
      INSTALL_SKILLS=false
      shift
      ;;
    --help|-h)
      cat <<'USAGE'
install.sh — install the SlopStopper quality suite into a target repo.

Usage:
  bash install.sh [TARGET_DIR]              # Task-driven workflows (default)
  bash install.sh --no-task [TARGET_DIR]    # CLI-driven workflows (no Task install)
  bash install.sh --no-skills [TARGET_DIR]  # Skip installing Claude Code skills

Env var equivalents:
  SLOPSTOPPER_NO_TASK=1 bash install.sh
  SLOPSTOPPER_NO_SKILLS=1 bash install.sh

Default mode installs workflows that invoke `task ss:<check>` so the suite
shares a single invocation surface with the rest of your codebase. `--no-task`
installs workflows that invoke `slopstopper run <check>` directly.

If ~/.claude/ exists (Claude Code is set up on this machine), the installer
also refreshes the SlopStopper skill trio at ~/.claude/skills/slopstopper-*
by curl-piping install-skill.sh. Pass --no-skills to skip this step.
USAGE
      exit 0
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL[@]:+${POSITIONAL[@]}}"

TARGET_DIR="${1:-$(pwd)}"

# ── helpers ──────────────────────────────────────────────────────────────────

info()    { echo "  ℹ  $*"; }
success() { echo "  ✅ $*"; }
warn()    { echo "  ⚠️  $*"; }
error()   { echo "  ❌ $*" >&2; exit 1; }

sep() { echo "────────────────────────────────────────────────────────────"; }

# ── prerequisite check ────────────────────────────────────────────────────────
#
# Surface missing tools up front rather than letting the install fail mid-flight
# with a cryptic "command not found". `git` is hard-required (the installer
# clones this repo); the rest are soft-required (you'll need them to actually
# run any check, but the install itself will succeed without them).

preflight() {
  local missing_hard=()
  local missing_soft=()

  command -v git     >/dev/null 2>&1 || missing_hard+=("git")
  command -v python3 >/dev/null 2>&1 || missing_hard+=("python3 (slopstopper-cli is a Python package): https://www.python.org/downloads/")
  command -v node    >/dev/null 2>&1 || missing_soft+=("node (Playwright, Lighthouse CI, markdownlint, TypeScript): https://nodejs.org/")
  if [ "$USE_TASK" = "true" ]; then
    command -v task  >/dev/null 2>&1 || missing_soft+=("task (canonical interface — every check is 'task ss:...'): https://taskfile.dev/installation/")
  fi
  command -v docker  >/dev/null 2>&1 || info "Docker not found — only needed for DAST. Skipping check."

  if [ "${#missing_hard[@]}" -gt 0 ]; then
    for tool in "${missing_hard[@]}"; do
      echo "  ❌ Required tool missing: $tool" >&2
    done
    error "Install the tools above and re-run."
  fi

  if [ "${#missing_soft[@]}" -gt 0 ]; then
    warn "The following tools aren't installed — you'll need them to run the checks SlopStopper installs:"
    for tool in "${missing_soft[@]}"; do
      echo "      • $tool"
    done
    info "Continuing with install; install the tools above before running any task."
  fi
}

preflight

# ── locate source directory ───────────────────────────────────────────────────

# Resolve the directory that contains this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)" || true

# Resolve the absolute target so we can compare against SCRIPT_DIR. If they
# are the same directory, the user is running install.sh from inside an
# adopter repo and we MUST clone — otherwise the cp Taskfile.ss.yml step
# would copy the existing Taskfile.ss.yml to itself, never picking up
# upstream changes. Using Taskfile.ss.yml as the slopstopper-source marker
# (the previous behaviour) failed exactly this case because the adopter has
# their own Taskfile.ss.yml from a prior install.
TARGET_ABS="$(cd "$TARGET_DIR" 2>/dev/null && pwd || echo "$TARGET_DIR")"

# Decide whether SCRIPT_DIR is the genuine slopstopper repo. Markers:
#  - templates/  (only slopstopper has it; adopters get the templates
#    expanded into .slopstopper.yml, public/_headers, etc.)
#  - install.sh  (this script itself, sanity check)
#  - SCRIPT_DIR != TARGET_ABS (running install.sh from inside a target
#    that happens to ship its own templates/ dir would still trigger this).
SCRIPT_IS_SOURCE=0
if [ -n "$SCRIPT_DIR" ] \
   && [ -d "$SCRIPT_DIR/templates" ] \
   && [ -f "$SCRIPT_DIR/install.sh" ] \
   && [ "$SCRIPT_DIR" != "$TARGET_ABS" ]; then
  SCRIPT_IS_SOURCE=1
fi

if [ "$SCRIPT_IS_SOURCE" -eq 0 ]; then
  if ! command -v git &>/dev/null; then
    error "git is required when running install.sh from outside the SlopStopper repo. Please install git and try again."
  fi

  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT

  info "Cloning template repository into a temporary directory…"
  git clone --depth=1 "$REPO_URL" "$TMP_DIR/template" &>/dev/null \
    || error "Failed to clone $REPO_URL"

  SCRIPT_DIR="$TMP_DIR/template"
fi

# ── validate target ───────────────────────────────────────────────────────────

[ -d "$TARGET_DIR" ] || error "Target directory does not exist: $TARGET_DIR"

sep
echo "  🛠  SlopStopper — installing tooling"
echo "  Source : $SCRIPT_DIR"
echo "  Target : $TARGET_DIR"
sep

# ── install files ─────────────────────────────────────────────────────────────

# 1. Taskfile.ss.yml — always refreshed (SlopStopper-owned, safe to overwrite).
cp "$SCRIPT_DIR/Taskfile.ss.yml" "$TARGET_DIR/Taskfile.ss.yml"
success "Taskfile.ss.yml installed (refreshed)"

# 2. Root Taskfile.yml — only create if missing.
# If the consumer already has one, print clear instructions instead of editing it.
if [ -f "$TARGET_DIR/Taskfile.yml" ]; then
  if grep -qE "^[[:space:]]+ss:[[:space:]]*$" "$TARGET_DIR/Taskfile.yml" 2>/dev/null \
     || grep -q "Taskfile.ss.yml" "$TARGET_DIR/Taskfile.yml" 2>/dev/null; then
    info "Taskfile.yml already references Taskfile.ss.yml — no changes needed"
  else
    warn "Taskfile.yml already exists — leaving it alone."
    echo ""
    echo "  Add the following block to your existing Taskfile.yml so the"
    echo "  SlopStopper tasks become available as 'task ss:<name>':"
    echo ""
    echo "    includes:"
    echo "      ss:"
    echo "        taskfile: ./Taskfile.ss.yml"
    echo ""
  fi
else
  # Write a minimal root Taskfile inline rather than copying slopstopper's
  # own — slopstopper's root file carries `contributing:*` + `decisions:*`
  # tasks that are scoped to working on slopstopper itself, not the suite
  # being shipped to adopters.
  cat > "$TARGET_DIR/Taskfile.yml" <<'YAML'
version: '3'

includes:
  ss:
    taskfile: ./Taskfile.ss.yml
YAML
  success "Taskfile.yml installed"
fi

# 3. slopstopper-cli — install (or refresh) the Python CLI that every
#    check runs through. Pulled from PyPI, so adopters always get the
#    latest release without us having to bump a pinned wheel URL across
#    docs and workflows on every cut. `pipx` is preferred (isolates the
#    install in its own venv); falls back to `pip install --user`.
#
# If an `.ss/` overlay (specs, playwright config, lighthouse config) is
# already present in the target, the CLI's templates module prefers
# those files over the package data — same shape as the workflows.
install_cli() {
  # Escape hatch used by cli/tests/test_install.py so the bash-side
  # install tests don't have to hit PyPI on every run. Adopter-facing
  # docs don't mention this — it's strictly an internal test affordance.
  if [ "${SKIP_CLI_INSTALL:-0}" = "1" ]; then
    info "Skipping slopstopper-cli install (SKIP_CLI_INSTALL=1)"
    return 0
  fi

  # Capture the pre-install version (empty if not installed). After
  # installing/upgrading, compare against the post-install version and
  # warn if pipx silently kept a stale build. Catches the "0.1.0 reported
  # as just-installed" failure mode that swallowing stderr used to mask.
  local pre_version=""
  if command -v slopstopper &>/dev/null; then
    pre_version="$(slopstopper --version 2>&1 || true)"
  fi

  if command -v pipx &>/dev/null; then
    if pipx list 2>/dev/null | grep -q "slopstopper-cli"; then
      info "Refreshing slopstopper-cli via pipx…"
      # Do NOT swallow stderr — pipx upgrade failures used to vanish
      # silently and the success message lied about the version.
      if ! pipx upgrade slopstopper-cli; then
        warn "pipx upgrade failed — falling through to 'pipx install --force'."
        pipx install --force slopstopper-cli >/dev/null
      fi
    else
      info "Installing slopstopper-cli via pipx…"
      pipx install slopstopper-cli >/dev/null
    fi
  else
    warn "pipx not found — falling back to 'pip install --user'."
    warn "Install pipx for the cleanest experience: https://pipx.pypa.io/"
    python3 -m pip install --user --upgrade slopstopper-cli >/dev/null
  fi

  if ! command -v slopstopper &>/dev/null; then
    error "slopstopper-cli install succeeded but the 'slopstopper' binary is not on PATH. Check your shell's PATH (pipx puts binaries in \$HOME/.local/bin)."
  fi

  local post_version
  post_version="$(slopstopper --version 2>&1 || true)"
  success "slopstopper-cli installed ($post_version)"

  # If an upgrade was supposed to happen (pre_version was non-empty) and
  # the version string didn't change, surface that loudly. pipx sometimes
  # claims success when the version on PyPI is the same as the local
  # build; that's fine. But a genuinely stale local install + a silently-
  # failed upgrade looks identical from the success line — so we warn
  # rather than error, and tell the adopter how to force a refresh.
  if [ -n "$pre_version" ] && [ "$pre_version" = "$post_version" ]; then
    warn "Version unchanged after upgrade attempt ($post_version). If you expected a newer release, run 'pipx install --force slopstopper-cli' to refresh."
  fi
}

install_cli

# 4. .ss/ overlay — nothing is seeded by default. Every CLI-managed
#    file (Playwright specs, Playwright config, lighthouserc dev/prod,
#    server.js) lives inside slopstopper-cli and is resolved at runtime
#    via .ss/ override → package-data fallback. Adopters who want to
#    customise a file run `slopstopper templates eject <name>` to copy
#    the bundled version into .ss/<name>.
mkdir -p "$TARGET_DIR/.ss"

# Clean up any legacy .ss/scripts/ left over from pre-CLI installs —
# every script previously copied into adopter repos is now bundled in
# slopstopper-cli (or was a slopstopper.dev-internal helper that didn't
# belong in adopter repos).
if [ -d "$TARGET_DIR/.ss/scripts" ]; then
  rm -rf "$TARGET_DIR/.ss/scripts"
  success ".ss/scripts/ removed (logic now lives in slopstopper-cli)"
fi

# Clean up legacy byte-equal template copies from pre-lift installs.
# If an adopter has customised any of these, leave the file alone — the
# CLI's templates resolver will keep using the .ss/ override.
# Detection: compare bytes against the package data shipped in the wheel
# the adopter just installed.
DATA_DIR="$(python3 -c 'import slopstopper, pathlib; print(pathlib.Path(slopstopper.__file__).resolve().parent / "data")' 2>/dev/null || true)"
if [ -n "$DATA_DIR" ] && [ -d "$DATA_DIR" ]; then
  scrub_if_byte_equal() {
    local rel="$1"
    local adopter="$TARGET_DIR/.ss/$rel"
    local pkg="$DATA_DIR/$rel"
    if [ -e "$adopter" ] && [ -e "$pkg" ] && cmp -s "$adopter" "$pkg"; then
      rm -rf "$adopter"
      success ".ss/$rel removed (unmodified copy of package-data fallback)"
    fi
  }
  scrub_if_byte_equal "playwright.config.js"
  scrub_if_byte_equal "lighthouserc.json"
  scrub_if_byte_equal "lighthouserc.prod.json"
  scrub_if_byte_equal "server.js"
  if [ -d "$TARGET_DIR/.ss/tests" ] && [ -d "$DATA_DIR/tests" ]; then
    if diff -rq "$TARGET_DIR/.ss/tests" "$DATA_DIR/tests" >/dev/null 2>&1; then
      rm -rf "$TARGET_DIR/.ss/tests"
      success ".ss/tests/ removed (unmodified copy of package-data fallback)"
    fi
  fi
fi

# 4. .github/workflows/ — install ss- prefixed generic workflows.
WORKFLOWS_SRC="$SCRIPT_DIR/.github/workflows"
WORKFLOWS_DST="$TARGET_DIR/.github/workflows"
mkdir -p "$WORKFLOWS_DST"

# Every workflow ships by default. The four layers are documented in
# the post-install matrix; consumers can delete any they don't want and
# re-running the installer will respect that deletion (tracked via
# .ss/.workflows-installed).
#
# copilot-setup-steps.yml is platform-fixed and not included here — install
# it manually if you use GitHub Copilot's setup-steps feature.
GENERIC_WORKFLOWS=(
  # Layer 1 — static analysis (works on any code)
  "ss-hygiene-complexity-check.yml"
  "ss-hygiene-csp-exceptions-check.yml"
  "ss-hygiene-docs-accuracy-check.yml"
  "ss-hygiene-docs-size-check.yml"
  "ss-hygiene-docs-structure-check.yml"
  "ss-hygiene-entry-files-check.yml"
  "ss-hygiene-auto-label-pr.yml"
  "ss-security-sast-check.yml"
  "ss-security-secrets-check.yml"
  "ss-security-vulnerability-all-check.yml"
  "ss-security-vulnerability-new-check.yml"
  "ss-workflow-failure-issue.yml"
  # Layer 2 — web-app dynamic (need a URL)
  "ss-security-dast-check.yml"
  "ss-reliability-smoke-tests.yml"
  "ss-reliability-accessibility-check.yml"
  "ss-reliability-broken-links-check.yml"
  "ss-reliability-core-web-vitals.yml"
  "ss-reliability-seo-check.yml"
  # Layer 3 — agentic doc-updater (needs ANTHROPIC_API_KEY)
  # NB: gh-aw workflows ship as a .md source + .lock.yml compiled artifact.
  "ss-hygiene-doc-updater.md"
  "ss-hygiene-doc-updater.lock.yml"
)

MARKER_FILE="$TARGET_DIR/.ss/.workflows-installed"

# Load the set of workflows we installed last time (if any). If a workflow
# is in this list AND missing from the consumer's repo now, they deleted it
# and we won't re-add it. Compatible with bash 3.2 (no associative arrays).
was_previously_installed() {
  [ "$IGNORE_STALE_MARKER" -eq 1 ] && return 1
  [ -f "$MARKER_FILE" ] && grep -Fxq "$1" "$MARKER_FILE"
}

# Stale-marker detection: a marker lists every workflow as previously-
# installed but zero `ss-*.yml` files exist on disk. The only realistic
# explanation is the marker was left over from a prior branch (e.g. a
# revert) and the deletion-respect logic would now skip every workflow,
# yielding a silent zero-workflows install. A real user would not delete
# all 20 workflows; treat this as a stale marker and re-install fresh.
#
# Use `find` rather than `ls` for the count — `ls path/glob*` returns
# non-zero when the glob has no matches, which combines with `set -e -o
# pipefail` to abort the script. `find` returns 0 even on no matches.
IGNORE_STALE_MARKER=0
if [ -f "$MARKER_FILE" ]; then
  on_disk_count=$(find "$WORKFLOWS_DST" -maxdepth 1 -name 'ss-*.yml' -type f 2>/dev/null | wc -l | tr -d ' ')
  marker_count=$(grep -c '^ss-' "$MARKER_FILE" 2>/dev/null || true)
  [ -z "$marker_count" ] && marker_count=0
  if [ "$on_disk_count" = "0" ] && [ "$marker_count" -gt 0 ]; then
    IGNORE_STALE_MARKER=1
    warn "Stale .ss/.workflows-installed detected ($marker_count entries, 0 workflows on disk) — treating as a fresh install and re-adding all workflows. If you genuinely deleted every workflow, set workflows.disabled in .slopstopper.yml instead so the choice survives re-runs."
  fi
fi

INSTALLED_WORKFLOWS=0
REFRESHED_WORKFLOWS=0
DELETED_RESPECTED=0
NEW_MARKER_CONTENT=""

for wf in "${GENERIC_WORKFLOWS[@]}"; do
  SRC="$WORKFLOWS_SRC/$wf"
  DST="$WORKFLOWS_DST/$wf"
  [ -f "$SRC" ] || continue

  # Respect deletions: if we installed it before AND it's gone now, leave it gone.
  if was_previously_installed "$wf" && [ ! -f "$DST" ]; then
    (( DELETED_RESPECTED++ )) || true
    continue
  fi

  if [ -f "$DST" ]; then
    cp "$SRC" "$DST"
    (( REFRESHED_WORKFLOWS++ )) || true
  else
    cp "$SRC" "$DST"
    (( INSTALLED_WORKFLOWS++ )) || true
  fi
  NEW_MARKER_CONTENT+="$wf"$'\n'
done

# Write the updated marker (atomic via tmp + mv).
printf '%s' "$NEW_MARKER_CONTENT" > "$MARKER_FILE.tmp" && mv "$MARKER_FILE.tmp" "$MARKER_FILE"

success "$INSTALLED_WORKFLOWS workflow(s) installed, $REFRESHED_WORKFLOWS refreshed, $DELETED_RESPECTED previously-deleted skipped"

# Post-process workflows for --no-task mode: strip the Task install step
# and rewrite `task ss:<X> -- args` into `slopstopper run <X> args`. The
# CLI accepts the same bare-positional URL adopters' shims pass through,
# so the resulting workflows are functionally identical — just without
# the Task install step or any `task ss:*` invocation.
#
# Idempotent: re-running install.sh without --no-task re-copies the
# Task-flavour workflow from source on top, so adopters can switch modes
# by re-running with/without the flag.
if [ "$USE_TASK" = "false" ]; then
  python3 - "$WORKFLOWS_DST" <<'PY'
import re
import sys
from pathlib import Path

workflows_dst = Path(sys.argv[1])

# Match the Task install step block we inserted in every workflow.
task_step = re.compile(
    r"\n      - name: Install Task runner\n"
    r"        uses: arduino/setup-task@v2\n"
    r"        with:\n"
    r"          version: 3\.x\n"
    r"          repo-token: \$\{\{ secrets\.GITHUB_TOKEN \}\}\n"
)

# Order matters: handle the `-- ` separator form first, then bare invocations.
# Shim names match CLI check names one-to-one — no alias mapping needed.
invoke_with_args = re.compile(r"task ss:([a-z][a-z0-9_:-]+) -- ")
invoke_bare      = re.compile(r"task ss:([a-z][a-z0-9_:-]+)")

transformed = 0
for path in sorted(workflows_dst.glob("ss-*.yml")):
    text = path.read_text()
    original = text
    text = task_step.sub("\n", text)
    text = invoke_with_args.sub(r"slopstopper run \1 ", text)
    text = invoke_bare.sub(r"slopstopper run \1", text)
    if text != original:
        path.write_text(text)
        transformed += 1

print(f"  ✅ Post-processed {transformed} workflow(s) for --no-task mode (Task install stripped, invocations rewritten to slopstopper-cli)")
PY
fi

# 5. Merge devDependencies into package.json if one exists.
PKG="$TARGET_DIR/package.json"
SRC_PKG="$SCRIPT_DIR/package.json"
if [ -f "$PKG" ] && command -v node &>/dev/null; then
  _TMP_MERGE="$(mktemp)"
  _TMP_ADDED="$(mktemp)"
  node - "$PKG" "$SRC_PKG" "$_TMP_ADDED" >"$_TMP_MERGE" <<'JS' || true
const fs = require('fs');
const [, , dst, src, addedFile] = process.argv;
const d = JSON.parse(fs.readFileSync(dst, 'utf8'));
const s = JSON.parse(fs.readFileSync(src, 'utf8'));
const added = [];
const conflicts = [];
d.devDependencies = d.devDependencies || {};
for (const [k, v] of Object.entries(s.devDependencies || {})) {
  if (!d.devDependencies[k]) { d.devDependencies[k] = v; added.push(k); }
  else if (d.devDependencies[k] !== v) { conflicts.push(`${k}: existing=${d.devDependencies[k]} template=${v}`); }
}
process.stdout.write(JSON.stringify(d, null, 2) + '\n');
fs.writeFileSync(addedFile, JSON.stringify({ added, conflicts }));
JS
  MERGED="$(cat "$_TMP_MERGE" 2>/dev/null || true)"
  rm -f "$_TMP_MERGE"
  if [ -n "$MERGED" ]; then
    echo "$MERGED" > "$PKG"
    if [ -f "$_TMP_ADDED" ]; then
      ADDED_PKGS="$(node -pe "JSON.parse(require('fs').readFileSync('$_TMP_ADDED','utf8')).added.join(', ')" 2>/dev/null || true)"
      CONFLICT_PKGS="$(node -pe "JSON.parse(require('fs').readFileSync('$_TMP_ADDED','utf8')).conflicts.join('; ')" 2>/dev/null || true)"
      rm -f "$_TMP_ADDED"
      if [ -n "$ADDED_PKGS" ]; then
        success "Added devDependencies: $ADDED_PKGS"
      else
        info "No new devDependencies to add"
      fi
      if [ -n "$CONFLICT_PKGS" ]; then
        warn "Version conflicts (your version kept): $CONFLICT_PKGS"
      fi
    fi
  fi
elif [ ! -f "$PKG" ]; then
  cp "$SRC_PKG" "$PKG"
  success "package.json installed"
fi

# 6. Seed adopter-default templates. seed_template() copies <src> to <dst>
# only if <dst> does not exist; never overwrites. The whole point is to
# remove the cliff between "install lands" and "first PR is green" — these
# defaults handle the common cases (no config file, no auto-label config,
# no headers, no .zap suppressions, no gitignore entries) so an adopter's
# first CI run isn't a discovery pass.

seed_template() {
  local label="$1"
  local src="$2"
  local dst="$3"
  if [ ! -f "$src" ]; then
    return 0  # template missing from source (e.g. running an old install.sh against a new repo) — skip silently
  fi
  if [ -f "$dst" ]; then
    info "$label: $dst already exists — leaving it alone"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  success "$label: seeded $dst"
}

# .slopstopper.yml — config carrier. Seeded from the repo-root example
# (which doubles as the schema reference — single source of truth).
seed_template ".slopstopper.yml" \
  "$SCRIPT_DIR/.slopstopper.yml.example" \
  "$TARGET_DIR/.slopstopper.yml"

# .github/labeler.yml — config for ss-hygiene-auto-label-pr.yml
seed_template ".github/labeler.yml" \
  "$SCRIPT_DIR/templates/labeler.yml.example" \
  "$TARGET_DIR/.github/labeler.yml"

# public/_headers — Cloudflare/Netlify static-asset header baseline (commented out)
#
# Idempotent append-with-markers (same pattern as the .gitignore block
# below). Adopters often arrive with a public/_headers that holds only
# cache rules; a plain skip-if-exists would deny them the security
# baseline forever. Instead: detect our begin-marker; append the block
# bracketed by markers if it isn't there yet; leave existing content
# untouched. The block ships fully commented so adopters opt in by
# uncommenting — same default safety as the fresh-install case.
seed_headers_block() {
  if [ ! -d "$TARGET_DIR/public" ]; then
    info "public/_headers: no public/ directory in target — skipping (add one and re-run if you want the baseline)"
    return 0
  fi
  local dst="$TARGET_DIR/public/_headers"
  local src="$SCRIPT_DIR/templates/_headers.example"
  if [ ! -f "$src" ]; then
    return 0
  fi
  if [ -f "$dst" ] && grep -Fq "# slopstopper security headers begin" "$dst" 2>/dev/null; then
    info "public/_headers: slopstopper security headers block already present — leaving it alone"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  if [ -f "$dst" ] && [ -s "$dst" ]; then
    printf '\n' >> "$dst"
    cat "$src" >> "$dst"
    success "public/_headers: appended slopstopper security headers block (commented; uncomment to enable)"
  else
    cat "$src" > "$dst"
    success "public/_headers: seeded $dst"
  fi
}

seed_headers_block

# .zap/rules.tsv — ZAP rule overrides (entries commented; uncomment what applies)
seed_template ".zap/rules.tsv" \
  "$SCRIPT_DIR/templates/zap-rules.tsv.example" \
  "$TARGET_DIR/.zap/rules.tsv"

# .markdownlint.json — defaults that let real docs pass (MD013 off, etc.).
# Adopters invoke markdownlint directly (`npx markdownlint "docs/**/*.md"`);
# markdownlint auto-discovers the closest config upward, so seeding at repo
# root works whether they call it from root or from docs/.
seed_template ".markdownlint.json" \
  "$SCRIPT_DIR/templates/markdownlint.json.example" \
  "$TARGET_DIR/.markdownlint.json"

# .gitignore — append the slopstopper block if not already present.
# Idempotent re-append: the block is bracketed with markers so re-runs
# detect the existing block and skip rather than duplicate.
GI="$TARGET_DIR/.gitignore"
GI_BLOCK_SRC="$SCRIPT_DIR/templates/gitignore.block"
if [ -f "$GI_BLOCK_SRC" ]; then
  if [ -f "$GI" ] && grep -Fq "# slopstopper begin" "$GI" 2>/dev/null; then
    info ".gitignore: slopstopper block already present — leaving it alone"
  else
    [ -f "$GI" ] && [ -s "$GI" ] && printf '\n' >> "$GI"
    cat "$GI_BLOCK_SRC" >> "$GI"
    success ".gitignore: appended slopstopper block"
  fi
fi

# 7. Apply .slopstopper.yml workflows.disabled — remove any matching
# workflows the adopter has opted out of, and remember the deletion via
# .ss/.workflows-installed so a re-run won't re-add them. This lets the
# config file drive deletions instead of "delete file and trust the
# marker" — both work, but config-driven is easier to audit and survive
# clone-and-rebuild.
if [ -f "$TARGET_DIR/.slopstopper.yml" ] && command -v slopstopper &>/dev/null; then
  DISABLED="$(cd "$TARGET_DIR" && slopstopper config get workflows.disabled 2>/dev/null || true)"
  if [ -n "$DISABLED" ]; then
    DISABLED_COUNT=0
    IFS=',' read -ra DISABLED_LIST <<< "$DISABLED"
    for wf_name in "${DISABLED_LIST[@]}"; do
      wf_name="$(echo "$wf_name" | tr -d ' ')"
      [ -z "$wf_name" ] && continue
      # Tolerate both with-extension and without-extension forms
      [[ "$wf_name" != *.yml ]] && wf_name="${wf_name}.yml"
      wf_path="$TARGET_DIR/.github/workflows/$wf_name"
      if [ -f "$wf_path" ]; then
        rm -f "$wf_path"
        (( DISABLED_COUNT++ )) || true
      fi
    done
    if [ "$DISABLED_COUNT" -gt 0 ]; then
      info "Removed $DISABLED_COUNT workflow(s) listed in .slopstopper.yml workflows.disabled"
    fi
  fi
fi

# ── install Claude Code skill trio (best-effort, user-profile level) ─────────

# install-skill.sh writes to ~/.claude/skills/slopstopper-*/ — i.e. the
# user profile, not the target repo. Done as part of install.sh so adopters
# get the trio without a separate command. Skipped silently if Claude Code
# isn't set up on this machine (no ~/.claude directory) or if --no-skills
# / SLOPSTOPPER_NO_SKILLS was passed.

install_claude_skills() {
  if [ "$INSTALL_SKILLS" = "false" ]; then
    info "Skipping Claude Code skill install (--no-skills / SLOPSTOPPER_NO_SKILLS)."
    return 0
  fi
  if [ ! -d "${HOME}/.claude" ]; then
    info "No ~/.claude directory found — skipping Claude Code skill install."
    info "If you set up Claude Code later, run:"
    info "  curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash"
    return 0
  fi
  echo ""
  sep
  echo "  🧠  Installing the SlopStopper Claude Code skill trio…"
  sep
  if ! curl -fsSL "https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh" | bash; then
    warn "Skill install failed (non-fatal). You can re-run it later:"
    info "  curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash"
    return 0
  fi
}

install_claude_skills

# ── post-install guidance ─────────────────────────────────────────────────────

sep
echo ""
echo "  🎉 Installation complete!"
echo ""
echo "  ── SlopStopper status for this repo ──────────────────────────────"
echo ""
echo "  ✅ Active now (no config needed — work on any code):"
echo "       SAST · Secrets · Dependency CVEs · Dependency Review"
echo "       Complexity · Doc Structure · Doc Accuracy · Doc Size"
echo "       Auto-label PRs · Workflow-failure tracker"
echo ""
echo "  ⏳ Active once you point them at your app (edit .slopstopper.yml):"
echo "       Smoke · Accessibility · Core Web Vitals · DAST · SEO · Broken Links"
echo ""
echo "     # in .slopstopper.yml:"
echo "     urls:"
echo "       production: https://your-site.example.com"
echo "       preview:    https://staging.your-site.example.com"
echo ""
echo "     # if you need Node 22+ for your build:"
echo "     node_version: '22'"
echo "     gh variable set SLOPSTOPPER_NODE_VERSION --body 22"
echo ""
echo "  🔐 Inert until you add secrets in your repo settings:"
echo "       Doc Auto-Updater (gh-aw agentic workflow)"
echo "         → COPILOT_GITHUB_TOKEN"
echo "         → Settings → Actions → General →"
echo "           'Allow GitHub Actions to create and approve pull requests'"
echo "         → See docs/hygiene/DOC_UPDATER.md for the full setup"
echo ""
echo "  🚀 Deploy is handled by Cloudflare, not by a workflow in this suite:"
echo "       Cloudflare dash → Workers & Pages → Create → Connect to Git"
echo "       Pushes deploy to prod, PRs get preview URLs, closing a PR"
echo "       cleans up the preview. No GitHub secrets required."
echo "       See docs/deployment/README.md for the full cutover steps."
echo ""
echo "  Don't use the doc-updater? Just delete its workflows from"
echo "  .github/workflows/ — re-running this installer won't bring them"
echo "  back (tracked via .ss/.workflows-installed)."
echo ""
sep
echo ""
if [ "$USE_TASK" = "true" ]; then
  echo "  Canonical invocation: task ss:<check>"
  echo ""
  echo "    Workflows are Task-driven by default — task ss:<check> is the"
  echo "    canonical interface for humans, agents and CI alike, so the"
  echo "    suite sits naturally alongside any other task build / task"
  echo "    deploy tasks in your codebase. The workflows install Task"
  echo "    themselves; locally, install it via:"
  echo ""
  echo "       https://taskfile.dev/installation/"
  echo ""
  echo "    Don't want Task in your CI? Re-run install.sh with --no-task"
  echo "    to get workflows that call slopstopper-cli directly:"
  echo ""
  echo "       bash install.sh --no-task"
  echo ""
  echo "  Next steps:"
  echo "    1. Install the Task runner (if you don't have it):"
  echo "         curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin"
  echo "    2. npm install"
  echo "    3. task --list"
  echo "    4. slopstopper badges          # generate README status badges (paste into README.md)"
  echo "    5. Open a PR — every check runs automatically."
else
  echo "  Installed in --no-task mode."
  echo ""
  echo "    Workflows call slopstopper-cli directly (no Task install step,"
  echo "    no task ss:* invocations). To switch to the canonical Task-driven"
  echo "    flow later, re-run install.sh without --no-task."
  echo ""
  echo "  Next steps:"
  echo "    1. npm install"
  echo "    2. slopstopper checks list      # see every check shipped"
  echo "    3. slopstopper badges           # generate README status badges (paste into README.md)"
  echo "    4. Open a PR — every check runs automatically."
fi
echo ""
sep
