# Lesson 15: Discoverability: robots, sitemap, llms.txt and links

**Goal.** Break each of the four files and links that tell crawlers,
agents and visitors a page exists, and see which check catches which.

## Why these checks

A page can be live, fast and accessible and still be invisible. Four
small things decide whether anyone finds it, and each has its own
check:

- **`robots.txt`** is the first file every crawler reads.
  `reliability:robots-txt` asserts it exists, points at the sitemap,
  and above all does not carry a blanket `Disallow: /` under
  `User-agent: *`. That one line, usually leaked from a staging config,
  removes an entire site from search; it is the highest-blast-radius
  line a site can ship.
- **`sitemap.xml`** is the list of pages a crawler should index.
  `reliability:sitemap` crawls the site from `/`, following links, and
  fails if a reachable page is missing from the sitemap or a sitemap
  entry 404s. A page nothing links to but the sitemap lists is an
  orphan, advisory by default.
- **`llms.txt`** is the file an AI assistant reads first, a curated
  markdown map of the site. `reliability:llms-txt` asserts it exists,
  opens with an H1 and links somewhere. The sitemap check also notes,
  advisorily, any reachable page the map leaves out.
- **Links** between pages are how visitors and crawlers move.
  `reliability:broken-links` loads each page in `pages.broken_links`
  in a browser and follows every same-origin link, failing on any that
  does not answer.

The first three are stdlib Python, one request each. The last is a
bundled Playwright spec. The slop they catch is the same each time: a
page added or renamed, and the files that describe the site left as
they were.

## You will need

- The checkout from the [syllabus](README.md), with the CLI on PATH.
- `node`, the npm dependencies and Playwright's Chromium, from
  `task contributing:setup`, for the server and the link check.

## Steps

### 1. Serve the site and see all four green

<!-- learn -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
task ss:reliability:robots-txt -- http://localhost:8099
task ss:reliability:sitemap -- http://localhost:8099
task ss:reliability:llms-txt -- http://localhost:8099
task ss:reliability:broken-links -- http://localhost:8099
```

```
  ✅ http://localhost:8099/robots.txt
✅ robots.txt is present and healthy.
  ✅ http://localhost:8099 (4 pages crawled)
✅ sitemap.xml is complete and free of dead entries.
  ✅ http://localhost:8099/llms.txt
✅ llms.txt is present and well-formed.
  ✓  1 [chromium] › .ss/.run/tests/broken-links.spec.ts:27:7 › Broken Link Checks › internal links return successful responses (422ms)
  1 passed (1.4s)
```

### 2. De-index the site with one word

<!-- learn -->
```sh
sed -i 's|^Allow: /|Disallow: /|' app/robots.txt
```

<!-- learn: fails -->
```sh
task ss:reliability:robots-txt -- http://localhost:8099
```

```
  ❌ http://localhost:8099/robots.txt
      - `User-agent: *` has a blanket `Disallow: /`, which de-indexes the entire site
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/robots-txt/robots-txt-report.md for full details.
task: Failed to run task "ss:reliability:robots-txt": exit status 1
```

Lighthouse checks that the file parses; this check reads what it says.

<!-- learn -->
```sh
git checkout app/robots.txt
```

### 3. Add a page and link to it, but do not list it

<!-- learn -->
```sh
cp app/tools.html app/new.html
python3 - <<'PY'
import pathlib, re
path = pathlib.Path("app/index.html")
text = path.read_text()
end = re.search(r'<a [^>]*href="tools.html"[^>]*>.*?</a>', text).end()
path.write_text(text[:end] + ' <a href="new.html">New</a>' + text[end:])
PY
```

<!-- learn: fails -->
```sh
task ss:reliability:sitemap -- http://localhost:8099
```

```
  ❌ http://localhost:8099 (5 pages crawled)
      - Reachable page missing from sitemap.xml: /new.html
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/sitemap/sitemap-report.md for full details.
task: Failed to run task "ss:reliability:sitemap": exit status 1
```

The crawler found five pages by following links and the sitemap lists
four. The report also carries the two advisory notes:

<!-- learn -->
```sh
sed -n '/Notes/,/---/p' .ss/reports/sitemap/sitemap-report.md
```

```
**Notes:**
- ⚠️  Sitemap entry not internally linked (orphan): /llms.txt
- ⚠️  Reachable page not listed in llms.txt: /new.html
---
```

### 4. List it

<!-- learn -->
```sh
sed -i 's|</urlset>|  <url><loc>https://slopstopper.dev/new.html</loc></url>\n</urlset>|' app/sitemap.xml
task ss:reliability:sitemap -- http://localhost:8099
```

```
  ✅ http://localhost:8099 (5 pages crawled)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ sitemap.xml is complete and free of dead entries.
```

Green, and the `llms.txt` gap is still a note, because that file is a
curated map and not every page belongs in it. The report's own advice
is the durable fix: generate the sitemap from the route inventory at
build time, so it cannot drift. A hand-edited list is what you have
when the site has four pages.

<!-- learn -->
```sh
git checkout app/index.html app/sitemap.xml
rm app/new.html
```

### 5. Take the title off llms.txt

<!-- learn -->
```sh
sed -i '1d' app/llms.txt
```

<!-- learn: fails -->
```sh
task ss:reliability:llms-txt -- http://localhost:8099
```

```
  ❌ http://localhost:8099/llms.txt
      - Missing H1 title (first line should be `# <name>`)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/llms-txt/llms-txt-report.md for full details.
task: Failed to run task "ss:reliability:llms-txt": exit status 1
```

The bar is deliberately low, because the convention is young: the
file must exist, start with a name and link somewhere. A site without
one is a site an assistant summarises from its HTML, badly.

<!-- learn -->
```sh
git checkout app/llms.txt
```

### 6. Point a link at a page that is not there

<!-- learn -->
```sh
sed -i 's|href="features.html"|href="missing.html"|' app/tools.html
```

<!-- learn: fails -->
```sh
task ss:reliability:broken-links -- http://localhost:8099
```

```
  ✘  1 [chromium] › .ss/.run/tests/broken-links.spec.ts:27:7 › Broken Link Checks › internal links return successful responses (460ms)
    Error: /missing.html returned 404
  1 failed
task: Failed to run task "ss:reliability:broken-links": exit status 1
```

<!-- learn -->
```sh
git checkout app/tools.html
```

## Checkpoint

<!-- learn -->
```sh
out=$(task ss:reliability:sitemap -- http://localhost:8099 2>&1)
kill "$(cat scratch/serve.pid)"
rm -r scratch
echo "$out" | grep 'complete'
```

```
✅ sitemap.xml is complete and free of dead entries.
```

## Exercise

Make the sitemap check fail without changing a single file.

<details>
<summary>Solution</summary>

Serve the site again and escalate the advisory note about orphans:

```sh
task ss:reliability:sitemap -- http://localhost:8099 --strict-orphans
```

`/llms.txt` is in the sitemap and nothing on the site links to it, so
with orphans escalated it is a failure. The same knob is
`reliability.sitemap.allow_orphans: false` in `.slopstopper.yml`, and
`--require-llms-complete` does the same for the `llms.txt` gaps. Both
are off by default because a curated map is allowed to leave things
out; turn them on when you want the files to mirror the site exactly.

</details>

## Going further

- [robots.txt](../reliability/ROBOTS_TXT.md), [sitemap.xml](../reliability/SITEMAP.md)
  and [llms.txt](../reliability/LLMS_TXT.md): every assertion and knob,
  and why generating the files beats editing them
- [Broken-link checks](../reliability/README.md#broken-link-checks) in
  the reliability README
- [llmstxt.org](https://llmstxt.org/), the convention the map follows

<details>
<summary>Episode script</summary>

**Length.** 9 to 11 minutes.

**Cold open (0:00).** A search for the site's name. Nothing. Cut to
`robots.txt`: `Disallow: /`.

**Talking points.**

1. Why: live, fast, accessible and invisible; four files and links,
   who reads each.
2. Serve; four green runs.
3. One word in robots.txt; red; Lighthouse parses, this reads.
4. A new page, linked but unlisted; red; the two notes; list it; why
   generating beats editing.
5. llms.txt without its title; the deliberately low bar.
6. A broken link; red.
7. Exercise: escalate the orphan note.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/15.tape`. Zoom on "5 pages crawled" against four
sitemap entries.

**Chapters.** `0:00 Why` · `1:30 Green` · `2:30 robots.txt` ·
`4:00 The sitemap` · `6:30 llms.txt` · `7:30 Links` ·
`8:30 Exercise` · `9:30 Next lesson`.

</details>
