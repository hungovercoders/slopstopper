# Recorded by demos/render.sh, which fills in the theme from theme.json
# and starts the shell where this tape expects. Don't run vhs on this file
# directly; `task contributing:demos -- checks` renders it.
Output demos/.frames/checks/
Set Shell bash
Set FontSize 14
Set Width 1100
Set Height 580
Set Padding 20
Set TypingSpeed 50ms
Set Theme @theme.json
Set Framerate 50

# Still: every check by name, with the ones this repo's profile holds back.
Type "slopstopper checks list"
Enter
Sleep 2s
