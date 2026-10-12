# Recorded by demos/render.sh, which fills in the theme from theme.json
# and starts the shell where this tape expects. Don't run vhs on this file
# directly; `task contributing:demos -- profile` renders it.
Output demos/.frames/profile/
Set Shell bash
Set FontSize 14
Set Width 1100
Set Height 320
Set Padding 20
Set TypingSpeed 50ms
Set Theme @theme.json
Set Framerate 50

# Still: the project-shape profile the repo contents suggest, and what the
# active one holds back.
Type "slopstopper profile detect"
Enter
Sleep 1.5s
Type "slopstopper profile show"
Enter
Sleep 2s
