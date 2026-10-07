#!/usr/bin/env bash
# install-skill.sh: install/refresh the SlopStopper Claude Code skills
# into the target repo.
#
# The companion to install.sh: install.sh installs the whole quality suite
# into a repo; this script just covers the skill subset, so you can refresh
# just the playbooks without touching workflows, the Taskfile or the CLI.
#
# Skills are installed at *project level*, into the adopter repo's
# ./.claude/skills/ directory, so every contributor that clones the repo
# gets them automatically (Claude Code auto-discovers project-level skills
# the same way it does user-level ones). Commit the resulting files
# alongside the workflows.
#
# Usage (from inside the target repo):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash
#
# Or, two-step (review first):
#   curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh -o install-skill.sh
#   bash install-skill.sh
#
# Or, explicit target directory:
#   bash install-skill.sh /path/to/repo
#
# What lands:
#   <target>/.claude/skills/slopstopper-install/   # install + refresh (SKILL.md + references/)
#   <target>/.claude/skills/slopstopper-triage/    # diagnose a failing check
#
# Migration:
#   - If a previous version installed a single `install-slopstopper` skill,
#     that obsolete directory is removed from the target repo.
#   - The `slopstopper-update` skill has been folded into `slopstopper-install`
#     (which now covers both first-install and refresh). Any stale
#     `slopstopper-update/` directory in the target is removed.
#   - This script no longer writes to ~/.claude/skills/. If a previous
#     version installed copies there, they'll shadow the project-level ones
#     when Claude Code merges skill paths. Remove them manually with:
#       rm -rf ~/.claude/skills/slopstopper-install \
#              ~/.claude/skills/slopstopper-update \
#              ~/.claude/skills/slopstopper-triage
#
# What this affects:
#   Nothing outside <target>/.claude/skills/slopstopper-*/. Re-running
#   replaces each skill directory only if the upstream content differs,
#   so it is safe to refresh on a schedule.

set -euo pipefail

# Override to fetch from a mirror or a local checkout (file:///path/to/slopstopper).
# install.sh runs this script against its own checkout that way, with
# SLOPSTOPPER_SKILLS_QUIET=1 to drop the banner and closing guidance.
REPO_RAW="${SLOPSTOPPER_REPO_RAW:-https://raw.githubusercontent.com/hungovercoders/slopstopper/main}"
SKILLS=(
  "slopstopper-install"
  "slopstopper-triage"
)
OBSOLETE_SKILLS=(
  "install-slopstopper"
  "slopstopper-update"
)

# ── argument parsing ─────────────────────────────────────────────────────────

TARGET_DIR="${1:-$(pwd)}"

# ── helpers ──────────────────────────────────────────────────────────────────

info()    { echo "  ℹ  $*"; }
success() { echo "  ✅ $*"; }
warn()    { echo "  ⚠️  $*"; }
error()   { echo "  ❌ $*" >&2; exit 1; }

sep() { echo "────────────────────────────────────────────────────────────"; }

# ── preflight ────────────────────────────────────────────────────────────────

case "${REPO_RAW}" in
  file://*) ;;  # a local checkout (install.sh runs us this way) needs no curl
  *) command -v curl >/dev/null 2>&1 || error "curl is required to fetch the skills. Install it and re-run." ;;
esac

if [ ! -d "${TARGET_DIR}" ]; then
  error "Target directory does not exist: ${TARGET_DIR}"
fi

if [ -z "${SLOPSTOPPER_SKILLS_QUIET:-}" ]; then
  sep
  echo "  🧠  SlopStopper: installing the Claude Code skills (project level)"
  echo "  Source : ${REPO_RAW}/.claude/skills/<skill>/  (SKILL.md + references/)"
  echo "  Target : ${TARGET_DIR}/.claude/skills/<skill>/"
  sep
fi

# ── install each skill ──────────────────────────────────────────────────────

SKILLS_RAW="${REPO_RAW}/.claude/skills"
SKILLS_DST="${TARGET_DIR}/.claude/skills"
STAGE_ROOT="$(mktemp -d)"
trap 'rm -rf "${STAGE_ROOT}"' EXIT

fetch() {
  case "$1" in
    file://*) cp "${1#file://}" "$2" ;;
    *) curl -fsSL "$1" -o "$2" ;;
  esac
}

# A skill is a directory: SKILL.md plus the references/*.md files it links
# (the long tables live there and are read on demand, so the skill costs one
# page of context until a step needs detail). Fetch SKILL.md, validate it,
# then fetch every references/<name>.md it mentions. Only linked files, so
# a stray draft or editor file in the source tree never ships.
#
# The result is staged under a directory made with mkdir (so it carries the
# umask's mode, not mktemp's 0700), copied next to the destination, and only
# then moved into place: a failed fetch or copy leaves the installed skill
# untouched. Every step checks its own status, because callers run this on
# the left of `||`, where `set -e` does not apply.
install_skill_dir() {
  local skill="$1"
  local dest_dir="${SKILLS_DST}/${skill}"
  local stage="${STAGE_ROOT}/${skill}"
  local ref

  mkdir -p "${stage}/references" || return 1
  if ! fetch "${SKILLS_RAW}/${skill}/SKILL.md" "${stage}/SKILL.md"; then
    warn "${skill}: failed to download SKILL.md"
    return 1
  fi
  if ! head -n 1 "${stage}/SKILL.md" | grep -q "^---$"; then
    warn "${skill}: SKILL.md does not look like a Claude Code skill (no frontmatter)"
    return 1
  fi
  for ref in $(grep -o 'references/[A-Za-z0-9_.-]*\.md' "${stage}/SKILL.md" | sort -u); do
    if ! fetch "${SKILLS_RAW}/${skill}/${ref}" "${stage}/${ref}"; then
      warn "${skill}: failed to download ${ref}"
      return 1
    fi
  done
  rmdir "${stage}/references" 2>/dev/null || true  # a skill with no references

  if [ -d "${dest_dir}" ] && diff -rq "${stage}" "${dest_dir}" >/dev/null 2>&1; then
    info "${skill}: already up to date"
    return 0
  fi
  local had_it=false
  [ -d "${dest_dir}" ] && had_it=true
  local incoming="${dest_dir}.incoming.$$" outgoing="${dest_dir}.outgoing.$$"
  mkdir -p "${SKILLS_DST}" || return 1
  if ! cp -R "${stage}" "${incoming}"; then
    rm -rf "${incoming}"
    warn "${skill}: could not copy into ${SKILLS_DST}, so the installed copy was left as it was"
    return 1
  fi
  if [ "${had_it}" = true ]; then
    mv "${dest_dir}" "${outgoing}" || { rm -rf "${incoming}"; return 1; }
  fi
  if ! mv "${incoming}" "${dest_dir}"; then
    [ "${had_it}" = true ] && mv "${outgoing}" "${dest_dir}"
    rm -rf "${incoming}"
    return 1
  fi
  rm -rf "${outgoing}"
  if [ "${had_it}" = true ]; then success "${skill}: refreshed"; else success "${skill}: installed"; fi
}

FAILED_SKILLS=()
for skill in "${SKILLS[@]}"; do
  install_skill_dir "${skill}" || FAILED_SKILLS+=("${skill}")
done

# ── clean up obsolete skill directories ──────────────────────────────────────

# Adopters who ran an earlier version of this script have obsolete skills
# at superseded paths. Remove them so their <target>/.claude/skills/ only
# contains the current set. Safe because we never delete anything we didn't
# put there ourselves:
#   - `install-slopstopper` was the single-skill name; replaced by the
#     `slopstopper-install` trio member.
#   - `slopstopper-update` was a separate refresh skill; its content has
#     been folded into `slopstopper-install` (covers both verbs).
for obsolete in "${OBSOLETE_SKILLS[@]}"; do
  obsolete_dir="${TARGET_DIR}/.claude/skills/${obsolete}"
  if [ -d "${obsolete_dir}" ]; then
    rm -rf "${obsolete_dir}"
    info "Removed obsolete skill: ${obsolete}"
  fi
done

# Heads-up: if the adopter ran an old version of install-skill.sh on this
# machine, they likely have stale copies of the same skills at user level
# (~/.claude/skills/slopstopper-*). Those will shadow the project-level
# copies when Claude Code merges skill paths. We don't delete user-level
# state on someone's behalf, but we point at it so they can clean up
# explicitly.
if [ -d "${HOME}/.claude/skills/slopstopper-install" ] \
  || [ -d "${HOME}/.claude/skills/slopstopper-update" ] \
  || [ -d "${HOME}/.claude/skills/slopstopper-triage" ]; then
  warn "Stale user-level skills detected at ~/.claude/skills/slopstopper-*."
  info "They'll shadow the project-level copies you just installed. Clean up with:"
  info "  rm -rf ~/.claude/skills/slopstopper-install \\"
  info "         ~/.claude/skills/slopstopper-update \\"
  info "         ~/.claude/skills/slopstopper-triage"
fi

# ── post-install guidance ────────────────────────────────────────────────────

if [ "${#FAILED_SKILLS[@]}" -gt 0 ]; then
  echo "  ❌ Not installed: ${FAILED_SKILLS[*]} (see the warnings above). Any installed copy was left as it was." >&2
  exit 1
fi

[ -n "${SLOPSTOPPER_SKILLS_QUIET:-}" ] && exit 0

sep
echo ""
echo "  🎉 Skills installed at project level!"
echo ""
echo "  Claude Code auto-discovers the skills under .claude/skills/ for any"
echo "  contributor working in this repo. Commit them alongside the workflows."
echo ""
echo "  Which skill triggers depends on what the prompt asks:"
echo ""
echo "    • \"install / refresh / upgrade slopstopper\" → slopstopper-install"
echo "    • \"fix this failing slopstopper check\"      → slopstopper-triage"
echo ""
echo "  To install the full SlopStopper suite into a fresh repo:"
echo "    cd <your-repo>"
echo "    curl -fsSL ${REPO_RAW}/install.sh | bash"
echo ""
echo "  Re-running this script from inside the repo refreshes the skills to"
echo "  the latest upstream version."
echo ""
sep
