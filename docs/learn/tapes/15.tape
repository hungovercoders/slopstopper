# Lesson 15: Discoverability: robots, sitemap, llms.txt and links.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 15` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/15.mp4.
Output demos/.frames/15/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Serve the site and see all four green
Type "mkdir -p scratch" Enter
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Type "sleep 2" Enter
Type "task ss:reliability:robots-txt -- http://localhost:8099" Enter
Type "task ss:reliability:sitemap -- http://localhost:8099" Enter
Type "task ss:reliability:llms-txt -- http://localhost:8099" Enter
Type "task ss:reliability:broken-links -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# 2. De-index the site with one word
Type "clear" Enter
Type "sed -i 's|^Allow: /|Disallow: /|' app/robots.txt" Enter
Wait+Line@5m /^\$$/
Sleep 2s

Type "clear" Enter
Type "task ss:reliability:robots-txt -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

Type "clear" Enter
Type "git checkout app/robots.txt" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 3. Add a page and link to it, but do not list it
Type "clear" Enter
Type "cp app/tools.html app/new.html" Enter
Type "python3 - <<'PY'" Enter
Type@8ms "import pathlib, re" Enter
Type@8ms 'path = pathlib.Path("app/index.html")' Enter
Type@8ms "text = path.read_text()" Enter
Type@8ms `end = re.search(r'<a [^>]*href="tools.html"[^>]*>.*?</a>', text).end()` Enter
Type@8ms `path.write_text(text[:end] + ' <a href="new.html">New</a>' + text[end:])` Enter
Type@8ms "PY" Enter
Wait+Line@5m /^\$$/
Sleep 2s

Type "clear" Enter
Type "task ss:reliability:sitemap -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

Type "clear" Enter
Type "sed -n '/Notes/,/---/p' .ss/reports/sitemap/sitemap-report.md" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 4. List it
Type "clear" Enter
Type "sed -i 's|</urlset>|  <url><loc>https://slopstopper.dev/new.html</loc></url>\n</urlset>|' app/sitemap.xml" Enter
Type "task ss:reliability:sitemap -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

Type "clear" Enter
Type "git checkout app/index.html app/sitemap.xml" Enter
Type "rm app/new.html" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 5. Take the title off llms.txt
Type "clear" Enter
Type "sed -i '1d' app/llms.txt" Enter
Wait+Line@5m /^\$$/
Sleep 2s

Type "clear" Enter
Type "task ss:reliability:llms-txt -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

Type "clear" Enter
Type "git checkout app/llms.txt" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 6. Point a link at a page that is not there
Type "clear" Enter
Type `sed -i 's|href="features.html"|href="missing.html"|' app/tools.html` Enter
Wait+Line@5m /^\$$/
Sleep 2s

Type "clear" Enter
Type "task ss:reliability:broken-links -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

Type "clear" Enter
Type "git checkout app/tools.html" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Type "out=$(task ss:reliability:sitemap -- http://localhost:8099 2>&1)" Enter
Type 'kill "$(cat scratch/serve.pid)"' Enter
Type "rm -r scratch" Enter
Type `echo "$out" | grep 'complete'` Enter
Wait+Line@5m /^\$$/
Sleep 2s
