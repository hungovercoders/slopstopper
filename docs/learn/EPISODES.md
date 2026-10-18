# Episode conventions

The YouTube title, thumbnail and description conventions for the "From
zero to slopstopper" series, and the recording notes every episode
follows, so the series reads as one thing. Each lesson's own script is
the collapsed "Episode script" at the end of its page; this file is
what those scripts have in common.

## Title

`From zero to slopstopper #N: <lesson title>` for the numbered lessons,
and `From zero to slopstopper: <topic>` for an occasional extra. Keep it
under 60 characters so it survives the mobile crop; a lesson title with
a colon in it drops the part after the colon.

## Thumbnail

Stoppy, the site's mascot (`app/og-image.svg` carries the drawing), the
episode number large, three to five words of the lesson title, and one
frame from the episode's terminal. The site's brand tokens, which
`demos/theme.json` holds as a terminal theme: the cream background, the
ink text and the orange accent, so a row of thumbnails looks like one
series.

## Description

Fill in every `<…>`. Keep the first line under 120 characters; it is the
line search results show.

```text
<One sentence: what you can do after this episode.>

This is lesson <N> of From zero to slopstopper, a course on the quality
gates that keep AI-assisted repos honest: one check per lesson, the slop
it stops, what it looks like when it fires, and the fix. Every lesson
runs in a checkout of the slopstopper repo, so you can follow along with
git, mise and Python.

📄 Lesson page, with every command to copy:
https://github.com/hungovercoders/slopstopper/blob/main/docs/learn/<NN-slug>.md

▶ Add the suite to your own repo in one line:
    curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash

Chapters
0:00 <Why>
<m:ss> <Step 1>
<m:ss> <Step 2>
<m:ss> Checkpoint
<m:ss> Exercise
<m:ss> Next lesson

Links
🏠 Site: https://slopstopper.dev/
📦 Source and issues: https://github.com/hungovercoders/slopstopper
📚 The whole course: https://github.com/hungovercoders/slopstopper/blob/main/docs/learn/README.md
⬅ Previous: <link or "this is the first one">
➡ Next: <link or "coming soon">

slopstopper is MIT licensed and built in the open. If something in this
episode does not work for you, the commands on the lesson page are run
in CI on every change, so it is probably a version difference; open an
issue with the lesson number and what you saw.
```

## Recording notes

- **Every episode opens on its title card**: the series label, the
  lesson's title and one command, then the lesson's cold open. The row
  of episodes reads as one series that way, and a viewer who lands
  mid-course knows where they are before the first terminal appears.
- **One terminal, 100 columns by 30 rows, font size 16**, the site's
  theme from `demos/theme.json`, and nothing else on screen but the
  occasional zoom the lesson's shot list names. The lesson's tape,
  `docs/learn/tapes/NN.tape`, reproduces the terminal parts on demand
  at exactly that size, so b-roll can be re-recorded without re-doing
  the voice.
- **Say the command before typing it**, then pause on the output for a
  beat longer than feels natural. Viewers read slower than you talk,
  and a red line needs a moment to land.
- **Show the report, not just the verdict.** Every check's red line
  names a report; the episode opens it, because that is what the viewer
  will do next week on their own repo.
- **Every episode ends on the checkpoint passing**, then the one-line
  pitch for the next lesson.

## The tapes

`task contributing:learn:tapes` writes every lesson's tape from its
runnable blocks, so a tape cannot drift from the lesson; CI fails when
one is stale. `task contributing:learn:record -- NN` records a tape
into `dist/learn/NN.mp4`, the b-roll for the edit. What each tape needs
and how it differs from the README's demo tapes is in
[docs/contributing/DEMOS.md](../contributing/DEMOS.md#lesson-tapes).

The rest of an episode, the cards, the captions, the filled description
and the thumbnail, is cut by hand for now. apic's course has a generator
that builds all of that from a shot list; whether a port pays for itself
here is decided after the first two episodes are recorded by hand.
