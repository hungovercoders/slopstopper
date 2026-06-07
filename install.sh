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
#   Taskfile.yml                # thin root; created on fresh installs, left
#                               #   alone if you already have one (instructions
#                               #   printed in that case)
#   Taskfile.ss.yml             # all SlopStopper task definitions; always
#                               #   refreshed on re-run so updates flow through
#   .ss/scripts/                # Python/shell analysis scripts; always refreshed
#   .ss/tests/                  # portable Playwright + report-generator specs
#   .ss/playwright.config.js    # Playwright config scoped to .ss/tests/
#   .ss/lighthouserc.json       # Lighthouse CI budgets (PR/dev)
#   .ss/lighthouserc.prod.json  # Lighthouse CI budgets (production)
#   .ss/reports/                # SlopStopper-owned scan/report output dirs
#   .github/workflows/ss-*      # all SlopStopper workflows are ss- prefixed
#                               #   so they group together in the Actions UI
#                               #   and cannot clash with your existing workflows
#
# Workflow set ships in three conceptual layers:
#   1. Static analysis  — work on any code (SAST, Secrets, Trivy, complexity, doc checks)
#   2. Web-app dynamic  — need a URL (Smoke, Accessibility, CWV, Playwright)
#   3. Agentic updater  — needs COPILOT_GITHUB_TOKEN (gh-aw doc-updater)
# Deploy is intentionally not a layer: connect your repo in the Cloudflare
# dash (Workers & Pages → Create → Connect to Git) and you get production
# deploys, PR previews and preview cleanup for free — no workflow needed.
# Don't use one of the layers? Delete its workflows from .github/workflows/.
# Re-running this installer will respect that deletion (it tracks what it
# installed in .ss/.workflows-installed).

set -euo pipefail

REPO_URL="https://github.com/hungovercoders/slopstopper.git"
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
  command -v node    >/dev/null 2>&1 || missing_soft+=("node (Playwright, Lighthouse CI, markdownlint, TypeScript): https://nodejs.org/")
  command -v python3 >/dev/null 2>&1 || missing_soft+=("python3 (analysis scripts under .ss/scripts): https://www.python.org/downloads/")
  command -v task    >/dev/null 2>&1 || missing_soft+=("task (canonical interface — every check is 'task ss:...'): https://taskfile.dev/installation/")
  command -v docker  >/dev/null 2>&1 || info "Docker not found — only needed for DAST (task ss:security:dast). Skipping check."

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

# When piped through curl, BASH_SOURCE is not set and we need to clone.
# Taskfile.ss.yml is the marker file that proves we're in the SlopStopper repo.
if [ -z "$SCRIPT_DIR" ] || [ ! -f "$SCRIPT_DIR/Taskfile.ss.yml" ]; then
  if ! command -v git &>/dev/null; then
    error "git is required when running via curl. Please install git and try again."
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
  cp "$SCRIPT_DIR/Taskfile.yml" "$TARGET_DIR/Taskfile.yml"
  success "Taskfile.yml installed"
fi

# 3. .ss/scripts/, .ss/tests/, playwright + lighthouse configs — all
#    SlopStopper-owned and always refreshed on re-run.
mkdir -p "$TARGET_DIR/.ss"
rm -rf "$TARGET_DIR/.ss/scripts"
cp -r "$SCRIPT_DIR/.ss/scripts" "$TARGET_DIR/.ss/scripts"
success ".ss/scripts/ installed (refreshed)"

rm -rf "$TARGET_DIR/.ss/tests"
cp -r "$SCRIPT_DIR/.ss/tests" "$TARGET_DIR/.ss/tests"
success ".ss/tests/ installed (refreshed)"

cp "$SCRIPT_DIR/.ss/playwright.config.js" "$TARGET_DIR/.ss/playwright.config.js"
cp "$SCRIPT_DIR/.ss/lighthouserc.json" "$TARGET_DIR/.ss/lighthouserc.json"
cp "$SCRIPT_DIR/.ss/lighthouserc.prod.json" "$TARGET_DIR/.ss/lighthouserc.prod.json"
success ".ss/ Playwright + Lighthouse configs installed (refreshed)"

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
  "ss-reliability-core-web-vitals.yml"
  "ss-reliability-seo-check.yml"
  "ss-playwright-tests.yml"
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
  [ -f "$MARKER_FILE" ] && grep -Fxq "$1" "$MARKER_FILE"
}

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
echo "  ⏳ Active once you point them at your app's URL (set env vars):"
echo "       Smoke · Accessibility · Core Web Vitals · DAST · Playwright"
echo ""
echo "     export SMOKE_TEST_URL=https://staging.your-app.com"
echo "     export ACCESSIBILITY_TEST_URL=\$SMOKE_TEST_URL"
echo "     export ACCESSIBILITY_PAGES=/,/about,/pricing   # comma-separated"
echo "     export LIGHTHOUSE_URL=\$SMOKE_TEST_URL"
echo ""
echo "  🔐 Inert until you add secrets in your repo settings:"
echo "       Doc Auto-Updater (gh-aw agentic workflow)"
echo "         → ANTHROPIC_API_KEY"
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
echo "  Next steps:"
echo "    1. Install the Task runner (if you don't have it):"
echo "         curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin"
echo "    2. npm install"
echo "    3. task --list"
echo "    4. Open a PR — every check runs automatically."
echo ""
sep
