# Lesson 15: Discoverability: robots, sitemap, llms.txt and links.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 15` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/15.mp4.
# Sandbox: demo
Output demos/.frames/15/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Serve the demo and run all four
Type "mkdir -p scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 2" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:robots-txt -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:llms-txt -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:broken-links -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:sitemap -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. List it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -i.bak 's|</urlset>|  <url><loc>https://lantern.example.com/history.html</loc></url>\n</urlset>|' app/sitemap.xml && rm app/sitemap.xml.bak" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:sitemap -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout app/sitemap.xml" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. De-index the site with one word
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -i.bak 's|^Allow: /|Disallow: /|' app/robots.txt && rm app/robots.txt.bak" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:robots-txt -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout app/robots.txt" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 4. Take the title off llms.txt
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -i.bak '1d' app/llms.txt && rm app/llms.txt.bak" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:llms-txt -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout app/llms.txt" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 5. Point a link at a page that is not there
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type `sed -i.bak 's|href="history.html"|href="missing.html"|' app/index.html && rm app/index.html.bak` Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:broken-links -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout app/index.html" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -rf test-results" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "out=$(slopstopper run reliability:sitemap -- http://localhost:8099 2>&1 || true)" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/serve.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -r scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type `echo "$out" | grep 'missing from sitemap'` Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s
