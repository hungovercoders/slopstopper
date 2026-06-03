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
if [ -z "$SCRIPT_DIR" ] || [ ! -f "$SCRIPT_DIR/Taskfile.yml" ]; then
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

# 1. Taskfile.yml
if [ -f "$TARGET_DIR/Taskfile.yml" ]; then
  warn "Taskfile.yml already exists — skipping (back up and remove it to reinstall)"
else
  cp "$SCRIPT_DIR/Taskfile.yml" "$TARGET_DIR/Taskfile.yml"
  success "Taskfile.yml installed"
fi

# 2. .scripts/
if [ -d "$TARGET_DIR/.scripts" ]; then
  warn ".scripts/ already exists — skipping (remove it to reinstall)"
else
  cp -r "$SCRIPT_DIR/.scripts" "$TARGET_DIR/.scripts"
  success ".scripts/ installed"
fi

# 3. .github/workflows/
WORKFLOWS_SRC="$SCRIPT_DIR/.github/workflows"
WORKFLOWS_DST="$TARGET_DIR/.github/workflows"
mkdir -p "$WORKFLOWS_DST"

# Workflows that are generic and safe to install in any repo.
# Netlify-specific and copilot-internal workflows are excluded by default.
GENERIC_WORKFLOWS=(
  "hygiene-complexity-check.yml"
  "hygiene-docs-accuracy-check.yml"
  "hygiene-docs-size-check.yml"
  "hygiene-docs-structure-check.yml"
  "hygiene-auto-label-pr.yml"
  "security-dast-check.yml"
  "security-sast-check.yml"
  "security-secrets-check.yml"
  "security-vulnerability-all-check.yml"
  "security-vulnerability-new-check.yml"
  "reliability-smoke-tests.yml"
  "workflow-failure-issue.yml"
)

INSTALLED_WORKFLOWS=0
SKIPPED_WORKFLOWS=0
for wf in "${GENERIC_WORKFLOWS[@]}"; do
  SRC="$WORKFLOWS_SRC/$wf"
  DST="$WORKFLOWS_DST/$wf"
  [ -f "$SRC" ] || continue
  if [ -f "$DST" ]; then
    warn "Workflow $wf already exists — skipping"
    (( SKIPPED_WORKFLOWS++ )) || true
  else
    cp "$SRC" "$DST"
    (( INSTALLED_WORKFLOWS++ )) || true
  fi
done
success "$INSTALLED_WORKFLOWS workflow(s) installed, $SKIPPED_WORKFLOWS skipped"

# 4. Merge devDependencies into package.json if one exists.
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
echo "       .github/workflows/netlify-deploy.yml"
echo "       .github/workflows/netlify-cleanup-preview.yml"
echo "     and add NETLIFY_AUTH_TOKEN + NETLIFY_SITE_ID to your repo secrets."
echo ""
sep
