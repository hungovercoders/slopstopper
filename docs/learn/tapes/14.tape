# Lesson 14: SEO and social share.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 14` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/14.mp4.
Output demos/.frames/14/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Serve the site and see it green
Type "mkdir -p scratch" Enter
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Type "sleep 2" Enter
Type "SEO_VERIFY_OG_IMAGE=0 task ss:reliability:seo -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 2. Read what it found
Type "clear" Enter
Type "sed -n '/Tags detected/,/og:url/p' .ss/reports/seo/seo-metatags-report.md | head -12" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 3. Remove the description from one page
Type "clear" Enter
Type `sed -i '/<meta name="description"/d' app/tools.html` Enter
Wait+Line@5m /^\$$/
Sleep 2s

Type "clear" Enter
Type "SEO_VERIFY_OG_IMAGE=0 task ss:reliability:seo -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 4. Fix it
Type "clear" Enter
Type "git checkout app/tools.html" Enter
Type "SEO_VERIFY_OG_IMAGE=0 task ss:reliability:seo -- http://localhost:8099 | grep 'All pages'" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Type 'kill "$(cat scratch/serve.pid)"' Enter
Type "rm -r scratch" Enter
Type "grep '^\*\*Overall:\*\*' .ss/reports/seo/seo-metatags-report.md" Enter
Wait+Line@5m /^\$$/
Sleep 2s
