# Recorded by demos/render.sh, which fills in the theme from theme.json
# and starts the shell where this tape expects. Don't run vhs on this file
# directly; `task contributing:demos -- doctor` renders it.
Output demos/.frames/doctor/
Set Shell bash
Set FontSize 14
Set Width 1100
Set Height 340
Set Padding 20
Set TypingSpeed 50ms
Set Theme @theme.json
Set Framerate 50

# Still: which external tools are present, and the install hint for each
# missing one.
Type "slopstopper doctor"
Enter
Sleep 4s
