# Demo recordings

The GIF in `README.md` and the stills beside it are recorded from the
real CLI with [VHS](https://github.com/charmbracelet/vhs), from the tapes
under `demos/`, and live next to them. They are committed, so a reader never
needs the tooling; a contributor re-records when what a command prints
changes.

## Re-recording

```bash
task contributing:demos             # every tape
task contributing:demos -- hero     # one tape
```

The task runs `demos/render.sh`, which needs `vhs`, `ttyd` 1.7.7 or
newer, `ffmpeg` and `git`, plus `slopstopper` and `task` on PATH. It
prefers the editable CLI in `cli/.venv` (what `task contributing:setup`
creates), so a recording shows HEAD rather than a released wheel. The
install tape also needs `mise`, because `install.sh` does, and a network
that reaches the GitHub API, which mise uses to fetch `task`. It has not
been recorded yet: the sandbox this pipeline was built in had neither.

Every tape runs in a scratch clone of this repo, except `install.tape`,
which runs in an empty directory beside a `slopstopper` symlink to this
checkout. Nothing touches the working tree, and a tape can break things
(the triage tape pastes the docs map into `README.md` to blow its budget).

## The tapes

| Tape | Output | Shows |
| ---- | ------ | ----- |
| `hero.tape` | `demos/hero.gif`, embedded in `README.md` | `slopstopper checks list`, `slopstopper doctor`, `task ss:hygiene:entry-files` |
| `triage.tape` | `demos/triage.gif` | a green check, a change that breaks its budget, the red line, the report, the fix |
| `install.tape` | demos/install.gif (not committed yet) | `install.sh --profile ui` into a fresh repo, what it wrote, `task ss:hygiene:test` passing |
| `checks.tape` | `demos/checks.png` (still) | `slopstopper checks list` |
| `doctor.tape` | `demos/doctor.png` (still) | `slopstopper doctor` |
| `profile.tape` | `demos/profile.png` (still) | `slopstopper profile detect` and `profile show` |

A still keeps only its last frame; `render.sh` lists which names are
stills. The shared look lives in `theme.json` (the site's brand tokens as
a terminal theme) and is spliced into each tape at render time, so a tape
carries `Set Theme @theme.json` and nothing else about colour.

`doctor` shows the recording machine's tools, so the hero GIF is a
snapshot of whoever recorded it. A machine with a tool or two missing
makes the better demo, because the hints are the point.

## Adding a tape

1. Copy the header from an existing tape (output directory, size, theme,
   framerate) and type only ASCII: VHS types keystrokes, so an emoji in a
   `Type` line is dropped. Emoji in the picture come from the command's
   output.
2. Name it after what it shows, add it to the table above, and if it is a
   still add its name to `stills` in `render.sh`.
3. Render it, look at the result, and commit the tape with its GIF or PNG.
   Then embed it where it earns its place; `README.md` sits close to its
   entry-files token budget, so the hero is the one GIF there.

## What has bitten

- **The output directory must not exist when VHS starts.** VHS moves its
  frames into place with a plain rename, which fails silently into a
  non-empty directory. `render.sh` removes it first and keeps VHS's temp
  files beside it, never inside it.
- **A long checkout path crashes Chromium.** VHS puts the browser
  profile under its temp directory, and Chromium opens a Unix socket in
  it; a socket path tops out at 108 characters. Clone somewhere short.
- **Emoji one cell wide.** ttyd's terminal defaults to Unicode 6 widths,
  so emoji overlap the next column and every table drifts. The ttyd
  wrapper in `render.sh` turns on Unicode 11; keep it when upgrading.
- **No chrome on PATH.** VHS looks for `chrome`, `google-chrome` or
  `chromium`; a Playwright-installed browser is not on PATH, so a wrapper
  script named `chromium` that execs it does the job.
