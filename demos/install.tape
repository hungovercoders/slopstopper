# Recorded by demos/render.sh, which fills in the theme from theme.json
# and starts the shell where this tape expects. Don't run vhs on this file
# directly; `task contributing:demos -- install` renders it.
Output demos/.frames/install/
Set Shell bash
Set FontSize 14
Set Width 1100
Set Height 640
Set Padding 20
Set TypingSpeed 50ms
Set Theme @theme.json
Set Framerate 50

# One command into any repo: the installer run from a checkout (the README's
# curl | bash one-liner does the same from GitHub), what it wrote, and the
# pre-push hygiene suite passing on the fresh repo. Runs in an empty
# directory beside a `slopstopper` symlink to this checkout; needs mise.
Sleep 500ms
Type "git init -q demo-site && cd demo-site"
Sleep 300ms
Enter
Sleep 800ms
Type "bash ../slopstopper/install.sh --profile ui"
Sleep 300ms
Enter
Wait+Line@180s /\$$/
Sleep 3s
Type "clear"
Enter
Sleep 300ms
Type "git status --short"
Sleep 300ms
Enter
Sleep 4s
Type "clear"
Enter
Sleep 300ms
Type "task ss:hygiene:test"
Sleep 300ms
Enter
Wait+Line@120s /\$$/
Sleep 4s
