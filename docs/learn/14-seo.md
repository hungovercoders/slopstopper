# Lesson 14: SEO and social share

<!-- learn-sandbox: demo -->

**Goal.** Audit the tags a search engine and a link preview read, find
the one the demo's history page is missing, and see which surface it
would have broken.

## Why this check

Every page carries a second page nobody looks at: the `<head>`. A
search engine reads the title, the description and the canonical URL
to decide what the page is and whether it is a duplicate. Slack,
LinkedIn and a dozen chat apps read the OpenGraph and Twitter Card tags
to draw the preview card when someone pastes a link. Generated pages
ship with a placeholder title, a description copied from another page,
or no canonical at all, and the first anyone notices is a link that
unfurls as "Untitled" in a channel, or two URLs for one page competing
in search.

`reliability:seo` fetches each page in `pages.seo` and asserts the
tags are present and non-empty: title, description, viewport and
canonical for search; `og:title`, `og:description`, `og:type`,
`og:url` and `og:image` for previews; `twitter:card`, title,
description and image for the other preview format. It warns on a
title over 70 characters or a description over 160, the lengths
results pages truncate at, and by default it fetches the share image
to prove it answers with an image content type. It is stdlib Python:
one HTTP request per page and a parser, no browser.

Lighthouse's SEO category, which lesson 13's check runs, covers the
basics the search engine cares about. This check covers what Lighthouse
does not look at: the preview tags, and whether the image behind them
exists.

## You will need

- The demo repo from the [syllabus](README.md), with the CLI on PATH.
- `node`, for `slopstopper serve`.

## Steps

### 1. Serve the demo and see it red

The share image tags carry the production URL, because a preview card
is drawn from the live site, not from your laptop. Against a local
server, tell the check not to fetch it; the workflow does the same for
a local build.

<!-- learn: fails 1 -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
SEO_VERIFY_OG_IMAGE=0 slopstopper run reliability:seo -- http://localhost:8099
```

```
🔎 SEO metatag audit against: http://localhost:8099
   Pages: /, /history.html
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ http://localhost:8099/
  ❌ http://localhost:8099/history.html: 1 issue(s)
      - Missing <meta name="description">
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/seo/seo-metatags-report.md for full details.
```

The status page passes every tag. The history page has all of them
but one: whoever copied the `<head>` across dropped the description.
Without it, the search result for that page shows whatever sentence
the engine picks from the body; with a copied one, it would show the
wrong page's. Either is a page that reads as slop before anyone
clicks it.

### 2. Read what it found

The report lists every tag it detected, per page, which is the
quickest way to see what a preview card will say.

<!-- learn -->
```sh
sed -n '/Tags detected/,/og:url/p' .ss/reports/seo/seo-metatags-report.md | head -12
```

```
<details><summary>Tags detected</summary>

| Tag | Value |
|---|---|
| `title` | Lantern: service status |
| `description` | Which services exist, who owns each one, and where to look when one is down. |
| `canonical` | https://lantern.example.com/ |
| `viewport` | width=device-width, initial-scale=1 |
| `og:type` | website |
| `og:title` | Lantern: service status |
| `og:description` | Which services exist, who owns each one, and where to look when one is down. |
| `og:url` | https://lantern.example.com/ |
```

### 3. Fix it

One line in the history page's `<head>`, saying what the page is in
the words a search result should show. The `og:description` already
there is the right text.

<!-- learn -->
```sh
sed -i.bak 's|  <link rel="canonical" href="https://lantern.example.com/history.html">|  <meta name="description" content="Every incident in the last ninety days, which service it hit and how long it lasted.">\n  <link rel="canonical" href="https://lantern.example.com/history.html">|' app/history.html && rm app/history.html.bak
SEO_VERIFY_OG_IMAGE=0 slopstopper run reliability:seo -- http://localhost:8099 | grep 'All pages'
```

```
✅ All pages pass.
```

### 4. Know the knobs

`pages.seo` in `.slopstopper.yml` is the page list, and `SEO_PAGES`
overrides it for a run. `SEO_REQUIRE_OG_IMAGE=0` is for a site with no
share image at all, and `SEO_VERIFY_OG_IMAGE=0` is for runs where the
image URL cannot be fetched, as above. Against production the check
fetches the image, so a share image that 404s fails the daily run and
not a reader's feed.

One tag the check cannot assert is consistency: that the description
says the same thing everywhere it appears. A site whose identity
sentence sits in the hero, the meta tags and `llms.txt` keeps them in
step with a test of its own; that is a site-specific rule, and the
place for it is a test, not a check.

## Checkpoint

<!-- learn -->
```sh
git checkout app/history.html
kill "$(cat scratch/serve.pid)"
rm -r scratch
grep '^\*\*Overall:\*\*' .ss/reports/seo/seo-metatags-report.md
```

```
**Overall:** ✅ PASS
```

The report is from the fixed run; the demo is back to how it shipped,
one tag short.

## Exercise

Make the check warn without failing.

<details>
<summary>Solution</summary>

Serve the demo again and lengthen the status page's description past
160 characters:

```sh
sed -i.bak 's|<meta name="description" content="|<meta name="description" content="A much longer opening sentence that says the same thing again and again until it is well past the length a search result shows. |' app/index.html && rm app/index.html.bak
SEO_VERIFY_OG_IMAGE=0 slopstopper run reliability:seo -- http://localhost:8099
git checkout app/index.html
```

The page still passes, and the report under `.ss/reports/seo/` carries
a warning that the description is over 160 characters. Length is
advisory because the engines truncate rather than reject; a missing
tag is a failure because there is nothing to truncate.

</details>

## Going further

- [SEO and social-share metatags](../reliability/SEO.md): every tag
  asserted, the warnings, and the env vars
- Lesson 15, the files that tell crawlers and agents the pages exist
  at all

<details>
<summary>Episode script</summary>

**Length.** 7 to 9 minutes.

**Cold open (0:00).** A link pasted into a chat. The preview card:
"Untitled", no image.

**Talking points.**

1. Why: the second page nobody looks at; search and previews read it;
   placeholder titles and copied descriptions.
2. Serve; red on the history page; why the share image is not fetched
   locally.
3. The report's tag table: what the preview card will say.
4. The one line; green; what the search result would have shown.
5. Put the demo back. The knobs, and the one rule that belongs in a
   test.
6. Exercise: a warning without a failure.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/14.tape`. Zoom on the tag table.

**Chapters.** `0:00 Why` · `1:30 Red` · `2:30 The tags` ·
`4:00 The line` · `5:30 Knobs` · `7:00 Exercise` · `8:00 Next lesson`.

</details>
