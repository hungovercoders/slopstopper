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
#   Taskfile.yml             # thin root; created on fresh installs, left
#                            #   alone if you already have one (instructions
#                            #   printed in that case)
#   Taskfile.ss.yml          # all SlopStopper task definitions; always
#                            #   refreshed on re-run so updates flow through
#   .ss/scripts/             # Python/shell analysis scripts; always refreshed
#   .ss/reports/             # SlopStopper-owned scan/report output dirs
#   .github/workflows/ss-*   # all SlopStopper workflows are ss- prefixed so
#                            #   they group together in the Actions UI and
#                            #   cannot clash with your existing workflows

set -euo pipefail

REPO_URL="https://github.com/hungovercoders/slopstopper.git"
TARGET_DIR="${1:-$(pwd)}"

# ── helpers ──────────────────────────────────────────────────────────────────

info()    { echo "  ℹ  $*"; }
success() { echo "  ✅ $*"; }
warn()    { echo "  ⚠️  $*"; }
error()   { echo "  ❌ $*" >&2; exit 1; }

sep() { echo "────────────────────────────────────────────────────────────"; }

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

# 3. .ss/scripts/ — SlopStopper-owned; always refreshed.
mkdir -p "$TARGET_DIR/.ss"
rm -rf "$TARGET_DIR/.ss/scripts"
cp -r "$SCRIPT_DIR/.ss/scripts" "$TARGET_DIR/.ss/scripts"
success ".ss/scripts/ installed (refreshed)"

# 4. .github/workflows/ — install ss- prefixed generic workflows.
WORKFLOWS_SRC="$SCRIPT_DIR/.github/workflows"
WORKFLOWS_DST="$TARGET_DIR/.github/workflows"
mkdir -p "$WORKFLOWS_DST"

# Workflows that are generic and safe to install in any repo.
# Netlify-specific and copilot-internal workflows are excluded by default.
GENERIC_WORKFLOWS=(
  "ss-hygiene-complexity-check.yml"
  "ss-hygiene-docs-accuracy-check.yml"
  "ss-hygiene-docs-size-check.yml"
  "ss-hygiene-docs-structure-check.yml"
  "ss-hygiene-auto-label-pr.yml"
  "ss-security-dast-check.yml"
  "ss-security-sast-check.yml"
  "ss-security-secrets-check.yml"
  "ss-security-vulnerability-all-check.yml"
  "ss-security-vulnerability-new-check.yml"
  "ss-reliability-smoke-tests.yml"
  "ss-reliability-accessibility-check.yml"
  "ss-reliability-core-web-vitals.yml"
  "ss-workflow-failure-issue.yml"
)

INSTALLED_WORKFLOWS=0
SKIPPED_WORKFLOWS=0
for wf in "${GENERIC_WORKFLOWS[@]}"; do
  SRC="$WORKFLOWS_SRC/$wf"
  DST="$WORKFLOWS_DST/$wf"
  [ -f "$SRC" ] || continue
  if [ -f "$DST" ]; then
    # ss- prefix means we own it; refresh on update.
    cp "$SRC" "$DST"
    (( SKIPPED_WORKFLOWS++ )) || true
  else
    cp "$SRC" "$DST"
    (( INSTALLED_WORKFLOWS++ )) || true
  fi
done
success "$INSTALLED_WORKFLOWS workflow(s) installed, $SKIPPED_WORKFLOWS refreshed"

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
echo "  Everything SlopStopper owns lives under the 'ss' namespace:"
echo "    Taskfile.ss.yml       — task definitions"
echo "    .ss/scripts/          — analysis scripts"
echo "    .ss/reports/          — generated reports (git-ignored)"
echo "    .github/workflows/ss-*— CI workflows"
echo ""
echo "  Run any task with 'task ss:<name>', e.g.:"
echo "    task ss:hygiene:complexity"
echo "    task ss:security:sast"
echo "    task ss:reliability:accessibility"
echo ""
echo "  Re-run this installer any time to pull in updates — .ss/ and"
echo "  Taskfile.ss.yml are refreshed; your Taskfile.yml is left alone."
echo ""
echo "  Next steps:"
echo ""
echo "  1. Install the Task runner (if not already installed):"
echo "       curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin"
echo ""
echo "  2. Install npm dependencies:"
echo "       npm install"
echo ""
echo "  3. View available tasks:"
echo "       task --list"
echo ""
echo "  4. (Optional) For Netlify deployment workflows, also copy:"
echo "       .github/workflows/ss-netlify-deploy.yml"
echo "       .github/workflows/ss-netlify-cleanup-preview.yml"
echo "     and add NETLIFY_AUTH_TOKEN + NETLIFY_SITE_ID to your repo secrets."
echo ""
sep
