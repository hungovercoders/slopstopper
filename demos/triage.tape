# Recorded by demos/render.sh, which fills in the theme from theme.json
# and starts the shell where this tape expects. Don't run vhs on this file
# directly; `task contributing:demos -- triage` renders it.
Output demos/.frames/triage/
Set Shell bash
Set FontSize 14
Set Width 1100
Set Height 520
Set Padding 20
Set TypingSpeed 50ms
Set Theme @theme.json
Set Framerate 50

# The triage loop: a green check, a change that breaks its budget, the red
# line and the report it points at, and the fix. Runs in a scratch clone.
Sleep 500ms
Type "task ss:hygiene:entry-files"
Sleep 300ms
Enter
Sleep 4s
Type "clear"
Enter
Sleep 300ms
Type "cat docs/README.md >> README.md   # paste a routing table into the README"
Sleep 300ms
Enter
Sleep 1s
Type "task ss:hygiene:entry-files"
Sleep 300ms
Enter
Sleep 5.5s
Type "clear"
Enter
Sleep 300ms
Type "sed -n 12,20p .ss/reports/entry-files/entry-file-size-report.md"
Sleep 300ms
Enter
Sleep 5s
Type "clear"
Enter
Sleep 300ms
Type "git checkout README.md   # move the content into docs/ and route it, or revert"
Sleep 300ms
Enter
Sleep 800ms
Type "task ss:hygiene:entry-files"
Sleep 300ms
Enter
Sleep 4.5s
