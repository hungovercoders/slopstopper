#!/usr/bin/env bash
# Renders the README's demo GIFs and stills from demos/*.tape.
#
#   demos/render.sh                 # everything
#   demos/render.sh hero            # just these
#   task contributing:demos         # the same, via Task (`-- hero` for one)
#
# Needs: vhs (https://github.com/charmbracelet/vhs), ffmpeg, git, ttyd 1.7.7
# or newer (TTYD=/path/to/ttyd picks one), and `slopstopper` + `task` on PATH;
# the editable CLI in cli/.venv is preferred when it exists, so a recording
# shows HEAD rather than a released wheel.
#
# Every tape runs in a scratch clone of this repo (the triage tape edits
# README.md to make a check fail), and the install tape in an empty
# directory beside a `slopstopper` symlink to this checkout, so nothing
# touches the working tree.
#
# Three workarounds live here rather than in the tapes:
#  - ttyd's browser terminal defaults to Unicode 6 widths, which draws
#    emoji one cell wide and knocks every column out of line. A small
#    ttyd wrapper turns on Unicode 11.
#  - vhs writes raw frames and we encode them with ffmpeg ourselves, which
#    keeps GIFs small (15fps, diffed palette) and lets a still keep only
#    its last frame.
#  - vhs moves its frames into place with a plain rename, which fails
#    silently into an existing directory or across filesystems, so the
#    output directory is removed first and its temp files sit next to it.
#    Chromium also crashes when that temp path is long (a Unix socket path
#    tops out at 108 characters), so run this from a short checkout path.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
demos=demos
assets=demos
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# Stills keep only their final frame, as a PNG.
stills=" checks doctor profile "
bg="#FBF5EC"

for tool in vhs ffmpeg git; do
  command -v "$tool" > /dev/null || { echo "missing $tool" >&2; exit 1; }
done
real_ttyd=${TTYD:-$(command -v ttyd || true)}
[ -n "$real_ttyd" ] || { echo "missing ttyd (1.7.7+)" >&2; exit 1; }
if [ -x "$root/cli/.venv/bin/slopstopper" ]; then
  export PATH="$root/cli/.venv/bin:$PATH"
fi
for tool in slopstopper task; do
  command -v "$tool" > /dev/null || { echo "missing $tool on PATH (task contributing:setup installs the CLI)" >&2; exit 1; }
done

mkdir -p "$work/bin"
cat > "$work/bin/ttyd" <<WRAP
#!/bin/sh
exec "$real_ttyd" -t unicodeVersion=11 "\$@"
WRAP
chmod +x "$work/bin/ttyd"

# ttyd starts "bash" from PATH; this one gives vhs's plain prompt the brand
# accent and starts in the directory the tape expects (DEMO_CWD, below).
real_bash=$(command -v bash)
printf '%s\n' "PS1='\\[\\e[38;2;232;81;43m\\]\$\\[\\e[0m\\] '" \
  'cd "$DEMO_CWD"' > "$work/rc"
printf '#!%s\nexec "%s" --noprofile --rcfile "%s" -i +o history\n' \
  "$real_bash" "$real_bash" "$work/rc" > "$work/bin/bash"
chmod +x "$work/bin/bash"

# The scratch clone the checks run against, and the empty directory the
# installer fills. `../slopstopper/install.sh` in the install tape is the
# symlink, so the script sees itself as run from a checkout.
git clone --quiet "$root" "$work/repo"
# doctor asks GitHub (via gh) which ss-* workflows are disabled, keyed on
# the origin URL; the clone's origin is this checkout, so give it the real one.
origin=$(git -C "$root" remote get-url origin 2>/dev/null || true)
[ -z "$origin" ] || git -C "$work/repo" remote set-url origin "$origin"
mkdir -p "$work/adopter"
ln -s "$root" "$work/adopter/slopstopper"

# Keep vhs's temp files next to the output (see the header).
mkdir -p "$demos/.frames/tmp"
export TMPDIR="$root/$demos/.frames/tmp"

export PATH="$work/bin:$PATH"
export VHS_NO_SANDBOX=${VHS_NO_SANDBOX:-true}

# One line of JSON, ready to drop into each tape.
theme=$(tr -d '\n' < "$demos/theme.json" | tr -s ' ')

names=("$@")
if [ ${#names[@]} -eq 0 ]; then
  for tape in "$demos"/*.tape; do names+=("$(basename "$tape" .tape)"); done
fi

for name in "${names[@]}"; do
  echo "🎬 $name"
  frames="$demos/.frames/$name"
  rm -rf "$frames"
  if [ "$name" = install ]; then
    export DEMO_CWD="$work/adopter"
    rm -rf "$work/adopter/demo-site"
  else
    export DEMO_CWD="$work/repo"
    git -C "$work/repo" checkout --quiet -- . && git -C "$work/repo" clean --quiet -fdx
  fi
  # Fill in the shared theme, so theme.json is the only place it lives.
  awk -v theme="$theme" '$0 == "Set Theme @theme.json" { print "Set Theme " theme; next } { print }' \
    "$demos/$name.tape" > "$work/$name.tape"
  vhs "$work/$name.tape" > "$work/$name.log" 2>&1 || { cat "$work/$name.log"; exit 1; }
  [ -e "$frames/frame-text-00001.png" ] || { cat "$work/$name.log"; echo "no frames for $name" >&2; exit 1; }

  # Read the frames back at the rate they were captured.
  fps=$(awk '$1 == "Set" && $2 == "Framerate" { print $3 }' "$demos/$name.tape")
  fps=${fps:-50}
  inputs=(-framerate "$fps" -start_number 1 -i "$frames/frame-text-%05d.png"
          -framerate "$fps" -start_number 1 -i "$frames/frame-cursor-%05d.png")
  pad="pad=iw+48:ih+48:24:24:color=$bg"
  if [[ "$stills" == *" $name "* ]]; then
    last=$(find "$frames" -name 'frame-text-*.png' | sort | tail -1)
    ffmpeg -loglevel error -y -i "$last" -vf "$pad" "$assets/$name.png"
    echo "   → $assets/$name.png"
  else
    ffmpeg -loglevel error -y "${inputs[@]}" -filter_complex \
      "[0][1]overlay,$pad,fps=15,split[a][b];[a]palettegen=max_colors=192:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
      "$assets/$name.gif"
    echo "   → $assets/$name.gif ($(du -h "$assets/$name.gif" | cut -f1))"
  fi
  rm -rf "$frames"
done
rm -rf "$demos/.frames"
