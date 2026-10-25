# Lesson 3: Entry files: the AGENTS.md-first model.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 03` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/03.mp4.
# Sandbox: demo
Output demos/.frames/03/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See it red, and read the table
Type "slopstopper run hygiene:entry-files" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Read the report, then the file
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/How to fix/,$p' .ss/reports/entry-files/entry-file-size-report.md | head -6" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep -n '^## ' README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. Fix it: move the content deeper and route it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 - <<'PY'" Enter
Type@8ms "import pathlib" Enter
Type@8ms "readme = pathlib.Path('README.md'); text = readme.read_text()" Enter
Type@8ms "head, manual = text.split('## Everything you need to know\n', 1)" Enter
Type@8ms "readme.write_text(head.rstrip() + '\n')" Enter
Type@8ms "pathlib.Path('docs/manual.md').write_text('# The manual\n\n' + manual.lstrip())" Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf '\nBefore you look anything up beyond the quick start, read [manual.md](manual.md) for the whole manual.\n' >> docs/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:entry-files" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Put the demo back
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout README.md docs/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm docs/manual.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:entry-files | grep 'README.md'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
