# Lesson 21: Across an organisation: the steward.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 21` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/21.mp4.
# Sandbox: demo
Output demos/.frames/21/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Install the suite, and see what the steward can see
Type "slopstopper --quiet install --no-topic --no-hooks" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep slopstopper-cli mise.toml" Enter
Wait+Line@5m /(^|\s)\$$/
Type "cat .ss/.installed-from" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. The finding it works
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:complexity --json" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 3. The rest of the contract
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper profile expand library --json | head -4" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper checks list --json | head -7" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper doctor --json | python3 -c "' Enter
Wait+Line@5m /(^|\s)\$$/
Type "import json, sys" Enter
Wait+Line@5m /(^|\s)\$$/
Type "for t in json.load(sys.stdin)['tools']:" Enter
Wait+Line@5m /(^|\s)\$$/
Type `    if t['tool'] == 'semgrep': print(t['needed_by'], t['status'])"` Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. The marker a workaround leaves
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep -rho 'slopstopper-workaround: hungovercoders/slopstopper#<N>' .claude/skills | sort -u" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 5. What an upgrade order changes
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type `sed -i.bak 's/"pipx:slopstopper-cli" = ".*"/"pipx:slopstopper-cli" = "0.28.0"/' mise.toml && rm mise.toml.bak` Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep slopstopper-cli mise.toml" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper doctor --json | python3 -c "' Enter
Wait+Line@5m /(^|\s)\$$/
Type "import json, sys" Enter
Wait+Line@5m /(^|\s)\$$/
Type `print(sorted({t['needed_by'] for t in json.load(sys.stdin)['tools'] if t['needed_by']}))"` Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout .gitignore package.json" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git clean -fdq" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s
