# Recorded by demos/render.sh, which fills in the theme from theme.json
# and starts the shell where this tape expects. Don't run vhs on this file
# directly; `task contributing:demos -- hero` renders it.
Output demos/.frames/hero/
Set Shell bash
Set FontSize 14
Set Width 1100
Set Height 600
Set Padding 20
Set TypingSpeed 50ms
Set Theme @theme.json
Set Framerate 50

# What the suite is, and whether this machine can run it: every check by
# name, then doctor's tick-or-hint per tool, then one check going green.
Sleep 500ms
Type "slopstopper checks list"
Sleep 300ms
Enter
Sleep 5s
Type "clear"
Enter
Sleep 300ms
Type "slopstopper doctor"
Sleep 300ms
Enter
Sleep 5.5s
Type "clear"
Enter
Sleep 300ms
Type "task ss:hygiene:entry-files"
Sleep 300ms
Enter
Sleep 5s
