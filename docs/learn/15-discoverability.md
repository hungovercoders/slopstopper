# Lesson 15: Discoverability: robots, sitemap, llms.txt and links

<!-- learn-sandbox: demo -->

**Goal.** Run the four checks that decide whether anyone finds a page,
fix the one the demo ships red, and break the other three to see which
catches what.

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

- The demo repo from the [syllabus](README.md), with the CLI on PATH.
- `node`, and in the demo `npm install` then
  `npx playwright install chromium` (as in lesson 11), for the server
  and the link check.

## Steps

### 1. Serve the demo and run all four

<!-- learn: fails 1 -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
slopstopper run reliability:robots-txt -- http://localhost:8099
slopstopper run reliability:llms-txt -- http://localhost:8099
slopstopper run reliability:broken-links -- http://localhost:8099
slopstopper run reliability:sitemap -- http://localhost:8099
```

```
  ✅ http://localhost:8099/robots.txt
✅ robots.txt is present and healthy.
  ✅ http://localhost:8099/llms.txt
✅ llms.txt is present and well-formed.
  ✓  1 [chromium] › .ss/.run/tests/broken-links.spec.ts:27:7 › Broken Link Checks › internal links return successful responses (82ms)
  1 passed (407ms)
🗺️ sitemap completeness audit against: http://localhost:8099
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ❌ http://localhost:8099 (2 pages crawled)
      - Reachable page missing from sitemap.xml: /history.html
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/sitemap/sitemap-report.md for full details.
```

Three green, one red. The crawler followed the nav from `/` and found
two pages; the sitemap lists one. The history page was added, linked
from the nav, and the file that describes the site was left as it
was. That is the whole lesson in one finding.

### 2. List it

<!-- learn -->
```sh
sed -i.bak 's|</urlset>|  <url><loc>https://lantern.example.com/history.html</loc></url>\n</urlset>|' app/sitemap.xml && rm app/sitemap.xml.bak
slopstopper run reliability:sitemap -- http://localhost:8099
```

```
  ✅ http://localhost:8099 (2 pages crawled)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ sitemap.xml is complete and free of dead entries.
```

The report's own advice is the durable fix: generate the sitemap from
the page list at build time, so it cannot drift. A hand-edited list is
what you have when the site has two pages.

<!-- learn -->
```sh
git checkout app/sitemap.xml
```

### 3. De-index the site with one word

<!-- learn -->
```sh
sed -i.bak 's|^Allow: /|Disallow: /|' app/robots.txt && rm app/robots.txt.bak
```

<!-- learn: fails 1 -->
```sh
slopstopper run reliability:robots-txt -- http://localhost:8099
```

```
  ❌ http://localhost:8099/robots.txt
      - `User-agent: *` has a blanket `Disallow: /`, which de-indexes the entire site
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/robots-txt/robots-txt-report.md for full details.
```

Lighthouse checks that the file parses; this check reads what it says.

<!-- learn -->
```sh
git checkout app/robots.txt
```

### 4. Take the title off llms.txt

<!-- learn -->
```sh
sed -i.bak '1d' app/llms.txt && rm app/llms.txt.bak
```

<!-- learn: fails 1 -->
```sh
slopstopper run reliability:llms-txt -- http://localhost:8099
```

```
  ❌ http://localhost:8099/llms.txt
      - Missing H1 title (first line should be `# <name>`)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/llms-txt/llms-txt-report.md for full details.
```

The bar is deliberately low, because the convention is young: the
file must exist, start with a name and link somewhere. A site without
one is a site an assistant summarises from its HTML, badly.

<!-- learn -->
```sh
git checkout app/llms.txt
```

### 5. Point a link at a page that is not there

<!-- learn -->
```sh
sed -i.bak 's|href="history.html"|href="missing.html"|' app/index.html && rm app/index.html.bak
```

<!-- learn: fails 1 -->
```sh
slopstopper run reliability:broken-links -- http://localhost:8099
```

```
  ✘  1 [chromium] › .ss/.run/tests/broken-links.spec.ts:27:7 › Broken Link Checks › internal links return successful responses (89ms)
    Error: /missing.html returned 404
  1 failed
```

<!-- learn -->
```sh
git checkout app/index.html
rm -rf test-results
```

## Checkpoint

<!-- learn -->
```sh
out=$(slopstopper run reliability:sitemap -- http://localhost:8099 2>&1 || true)
kill "$(cat scratch/serve.pid)"
rm -r scratch
echo "$out" | grep 'missing from sitemap'
```

```
      - Reachable page missing from sitemap.xml: /history.html
```

Red again, with the demo as it shipped, and the fix is one `<url>`
line.

## Exercise

Make the sitemap check pass without listing the history page.

<details>
<summary>Solution</summary>

Serve the demo again and take the page out of the nav instead:

```sh
sed -i.bak 's| · <a href="history.html">History</a>||' app/index.html && rm app/index.html.bak
slopstopper run reliability:sitemap -- http://localhost:8099
git checkout app/index.html
```

Green: the crawler only finds what links reach, so an unlinked page is
not a missing sitemap entry. It is also not a page anyone will find,
which is why the fix in step 2 is the right one and this is the
exercise. `--strict-orphans` and `--require-llms-complete` escalate the
two advisory notes when you want the files to mirror the site exactly.

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
2. Serve; three green, the sitemap red; a page added and a list left
   alone.
3. List it; green; why generating beats editing. Put it back.
4. One word in robots.txt; red; Lighthouse parses, this reads.
5. llms.txt without its title; the deliberately low bar.
6. A broken link; red.
7. Exercise: unlink the page and see why that is the wrong fix.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/15.tape`. Zoom on "2 pages crawled" against one
sitemap entry.

**Chapters.** `0:00 Why` · `1:30 Four runs` · `3:00 The sitemap` ·
`4:30 robots.txt` · `6:00 llms.txt` · `7:00 Links` ·
`8:30 Exercise` · `9:30 Next lesson`.

</details>
