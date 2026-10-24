# Changelog

All notable changes to **slopstopper-cli** are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The release workflow (`.github/workflows/ss-release.yml`) reads the section matching the pushed tag and posts it as the GitHub Release notes. To cut a release: bump `version` in `cli/pyproject.toml` and `__version__` in `cli/slopstopper/__init__.py`, move the `## [Unreleased]` block down to a new `## [X.Y.Z] - YYYY-MM-DD`, push a `vX.Y.Z` tag.

## [0.25.0](https://github.com/hungovercoders/slopstopper/compare/v0.24.0...v0.25.0) (2026-10-24)


### Features

* **site:** privacy page and footer note for slopstopper.dev ([#539](https://github.com/hungovercoders/slopstopper/issues/539)) ([f20bd89](https://github.com/hungovercoders/slopstopper/commit/f20bd892cacd7c91752f062c392112a97fa8722f)), closes [#533](https://github.com/hungovercoders/slopstopper/issues/533)
* **site:** Workers Logs off and Giscus loads on click ([#540](https://github.com/hungovercoders/slopstopper/issues/540)) ([f9e923c](https://github.com/hungovercoders/slopstopper/commit/f9e923cdd47a696b9a36081e7ad3975fa5d6ebeb))
* **skills:** adopter feedback loop: repo topic, label, upstream issues, workaround markers ([#534](https://github.com/hungovercoders/slopstopper/issues/534)) ([d1020e1](https://github.com/hungovercoders/slopstopper/commit/d1020e13086537b4c5a2a1e79d184184d8024c7c))


### Bug Fixes

* **ci:** run Playwright's apt phase outside the timed retry loop ([#532](https://github.com/hungovercoders/slopstopper/issues/532)) ([c2df019](https://github.com/hungovercoders/slopstopper/commit/c2df01986a56fb1ec7ba7204d71be14aad84be25))

## [0.24.0](https://github.com/hungovercoders/slopstopper/compare/v0.23.0...v0.24.0) (2026-10-24)


### Features

* **cli:** slopstopper demo writes a small repo two checks fail on ([#516](https://github.com/hungovercoders/slopstopper/issues/516)) ([085be0c](https://github.com/hungovercoders/slopstopper/commit/085be0cab241ad77933b3a9ef24bb16ea8c6405e))

## [0.23.0](https://github.com/hungovercoders/slopstopper/compare/v0.22.0...v0.23.0) (2026-10-24)


### Features

* **security:** a seeded licence allowlist for dependency review ([#482](https://github.com/hungovercoders/slopstopper/issues/482)) ([7a14ece](https://github.com/hungovercoders/slopstopper/commit/7a14ece7a94c32932ee12029ce2e73b475594fd0)), closes [#481](https://github.com/hungovercoders/slopstopper/issues/481)
* **sitemap:** llms_ignore_paths leaves a section out of the llms.txt diff only ([#522](https://github.com/hungovercoders/slopstopper/issues/522)) ([12f4853](https://github.com/hungovercoders/slopstopper/commit/12f4853ea7a7a505e80a279cc73a387c28546df0)), closes [#456](https://github.com/hungovercoders/slopstopper/issues/456)


### Bug Fixes

* **cloudflare:** read the preview URL from the bot's Markdown table too ([#523](https://github.com/hungovercoders/slopstopper/issues/523)) ([ca3dc46](https://github.com/hungovercoders/slopstopper/commit/ca3dc46bdb14690f627b545d045eb972f2fc1765)), closes [#459](https://github.com/hungovercoders/slopstopper/issues/459)
* what installing on apic surfaced (nested wrangler, SEO env var, licence ids, workflow hardening, ignore_refs) ([#478](https://github.com/hungovercoders/slopstopper/issues/478)) ([7e3debc](https://github.com/hungovercoders/slopstopper/commit/7e3debc4bcc1547cc55cc151a39b26da2a863d49))

## [0.22.0](https://github.com/hungovercoders/slopstopper/compare/v0.21.0...v0.22.0) (2026-10-12)


### Features

* **docs:** generate the check tables and the README badges from the registry ([#475](https://github.com/hungovercoders/slopstopper/issues/475)) ([453c36e](https://github.com/hungovercoders/slopstopper/commit/453c36e0012c5ee6e0320b36cc673a9f532c2432)), closes [#469](https://github.com/hungovercoders/slopstopper/issues/469)

## [0.21.0](https://github.com/hungovercoders/slopstopper/compare/v0.20.5...v0.21.0) (2026-10-12)


### Features

* **site:** draw the hero's terminal demo as animated SVG from real CLI output ([#474](https://github.com/hungovercoders/slopstopper/issues/474)) ([74c1baa](https://github.com/hungovercoders/slopstopper/commit/74c1baaec86dafd45fba480b01dafee8b856c4c4)), closes [#466](https://github.com/hungovercoders/slopstopper/issues/466)
* VHS demos, colour-safe output, a CLI surface test and --json on reporting commands ([#472](https://github.com/hungovercoders/slopstopper/issues/472)) ([c6341b3](https://github.com/hungovercoders/slopstopper/commit/c6341b34a9d5a1f9e916d5f33c8702fe138dae66))


### Bug Fixes

* **dast:** hand ZAP only the plugin-id rows of .zap/rules.tsv ([#463](https://github.com/hungovercoders/slopstopper/issues/463)) ([e6039e6](https://github.com/hungovercoders/slopstopper/commit/e6039e66def8530f9b28955af202dbc1f2f938e5)), closes [#454](https://github.com/hungovercoders/slopstopper/issues/454)
* **dast:** report a crashed ZAP scan with its cause and fail the scan step ([#464](https://github.com/hungovercoders/slopstopper/issues/464)) ([fd71f3d](https://github.com/hungovercoders/slopstopper/commit/fd71f3ddf08d18d6053298ffebee800d396cb23b)), closes [#455](https://github.com/hungovercoders/slopstopper/issues/455)
* **install:** leave an already-configured public/_headers alone on refresh ([#462](https://github.com/hungovercoders/slopstopper/issues/462)) ([f579d90](https://github.com/hungovercoders/slopstopper/commit/f579d90dcda19359085fd5745de0aa0aeb73f7a4)), closes [#453](https://github.com/hungovercoders/slopstopper/issues/453)
* **profiles:** keep workflow names that already have an extension under workflows.disabled ([#461](https://github.com/hungovercoders/slopstopper/issues/461)) ([99a29b4](https://github.com/hungovercoders/slopstopper/commit/99a29b401079868d32cafa1b8d85d67c9fb9fa56)), closes [#452](https://github.com/hungovercoders/slopstopper/issues/452)

## [0.20.5](https://github.com/hungovercoders/slopstopper/compare/v0.20.4...v0.20.5) (2026-10-11)


### Bug Fixes

* **deploy:** skip stale Cloudflare deploys and branches with no PR ([#457](https://github.com/hungovercoders/slopstopper/issues/457)) ([a11f3fd](https://github.com/hungovercoders/slopstopper/commit/a11f3fd2ee6c1a72a0a03b8d92ba2064c9effca2))

## [0.20.4](https://github.com/hungovercoders/slopstopper/compare/v0.20.3...v0.20.4) (2026-10-11)


### Bug Fixes

* **robots-txt:** stop asking for an Llms: line, which Lighthouse scores robots.txt 0 for ([#450](https://github.com/hungovercoders/slopstopper/issues/450)) ([9ed5cfa](https://github.com/hungovercoders/slopstopper/commit/9ed5cfa3424a3832c2163285ab1dbd6cbfb8d505)), closes [#448](https://github.com/hungovercoders/slopstopper/issues/448)

## [0.20.3](https://github.com/hungovercoders/slopstopper/compare/v0.20.2...v0.20.3) (2026-10-11)


### Bug Fixes

* **cwv:** previews are audited with the dev config, which skips is-crawlable ([#447](https://github.com/hungovercoders/slopstopper/issues/447)) ([ce45cbb](https://github.com/hungovercoders/slopstopper/commit/ce45cbb06bdc7aad8e303d5923584f30ad8c42e5))

## [0.20.2](https://github.com/hungovercoders/slopstopper/compare/v0.20.1...v0.20.2) (2026-10-11)


### Bug Fixes

* **ci:** guard builds, one issue-gate rule, and a Cloudflare trigger that survives PR-only problems ([#439](https://github.com/hungovercoders/slopstopper/issues/439)) ([566fc97](https://github.com/hungovercoders/slopstopper/commit/566fc9797106928b58411d8816fa813a7b710f36))
* **cli:** issue dedup after the no-labels fallback, an honest API signal, and the review's CLI fallout ([#441](https://github.com/hungovercoders/slopstopper/issues/441)) ([1d08140](https://github.com/hungovercoders/slopstopper/commit/1d08140791c0635f8e0f718c101b94c66958d0f8))

## [0.20.1](https://github.com/hungovercoders/slopstopper/compare/v0.20.0...v0.20.1) (2026-10-11)


### Bug Fixes

* **deploy:** the Cloudflare trigger skips checks the repo has disabled ([#435](https://github.com/hungovercoders/slopstopper/issues/435)) ([480dbbf](https://github.com/hungovercoders/slopstopper/commit/480dbbfdf7fa47c9928f0b8212767e1b328b534b))

## [0.20.0](https://github.com/hungovercoders/slopstopper/compare/v0.19.0...v0.20.0) (2026-10-10)


### Features

* **deploy:** check every Cloudflare Workers Builds deploy, previews and the live site ([#433](https://github.com/hungovercoders/slopstopper/issues/433)) ([ac37f7d](https://github.com/hungovercoders/slopstopper/commit/ac37f7d1516c6fe25e8f22a27161451c8eead339)), closes [#425](https://github.com/hungovercoders/slopstopper/issues/425)
* **security:** DAST scans the deployed site after deploys, daily and on demand ([#431](https://github.com/hungovercoders/slopstopper/issues/431)) ([f9a2aed](https://github.com/hungovercoders/slopstopper/commit/f9a2aed2f3929e865533d7a22c369a4b982a56b3)), closes [#426](https://github.com/hungovercoders/slopstopper/issues/426)

## [0.19.0](https://github.com/hungovercoders/slopstopper/compare/v0.18.0...v0.19.0) (2026-10-10)


### Features

* **headers:** headers.format meta reads each built page's &lt;meta&gt; CSP for the drift check ([#430](https://github.com/hungovercoders/slopstopper/issues/430)) ([59b1b3c](https://github.com/hungovercoders/slopstopper/commit/59b1b3cbdc72c8416228fb1e87ad129eb1a54968)), closes [#422](https://github.com/hungovercoders/slopstopper/issues/422)
* **hygiene:** hygiene.docs.exclude takes paths out of all three docs checks ([#421](https://github.com/hungovercoders/slopstopper/issues/421)) ([0c2075e](https://github.com/hungovercoders/slopstopper/commit/0c2075ecf57b4449f018f634fc8d31dbd532b71b)), closes [#403](https://github.com/hungovercoders/slopstopper/issues/403)
* **profiles:** ui holds back the API checks until the repo shows an API ([#418](https://github.com/hungovercoders/slopstopper/issues/418)) ([0388c85](https://github.com/hungovercoders/slopstopper/commit/0388c8594c4f27fafb3124af3e52ffe732fd91ba)), closes [#408](https://github.com/hungovercoders/slopstopper/issues/408)
* **security:** rules.tsv accepts alert refs, and the DAST gate names what swallowed each finding ([#423](https://github.com/hungovercoders/slopstopper/issues/423)) ([81d7f7d](https://github.com/hungovercoders/slopstopper/commit/81d7f7d99f0bc31638e345dac19bff867f92d776)), closes [#406](https://github.com/hungovercoders/slopstopper/issues/406) [#407](https://github.com/hungovercoders/slopstopper/issues/407)


### Bug Fixes

* **alerts:** a workflow-failure issue is suppressed only by the failing workflow's own issue ([#428](https://github.com/hungovercoders/slopstopper/issues/428)) ([7e1c311](https://github.com/hungovercoders/slopstopper/commit/7e1c311c577d8657fd75e6affe60d162c0442996)), closes [#412](https://github.com/hungovercoders/slopstopper/issues/412)
* **cwv:** keep Lighthouse reports local unless public upload is opted in ([#410](https://github.com/hungovercoders/slopstopper/issues/410)) ([5f74ef3](https://github.com/hungovercoders/slopstopper/commit/5f74ef3e6f34ebb7e023ad8f3e6a7dc625b98687)), closes [#405](https://github.com/hungovercoders/slopstopper/issues/405)
* **doc-updater:** the shipped prompt learns the project from the repo, not from slopstopper ([#429](https://github.com/hungovercoders/slopstopper/issues/429)) ([218134d](https://github.com/hungovercoders/slopstopper/commit/218134dbb93fb47c9bcf6769d9ae1637e7d9529d)), closes [#411](https://github.com/hungovercoders/slopstopper/issues/411)
* **emit:** create missing labels before opening an issue, and never lose the issue over one ([#424](https://github.com/hungovercoders/slopstopper/issues/424)) ([4007f0f](https://github.com/hungovercoders/slopstopper/commit/4007f0f393a8201367c20ca00c9d09848ca8f891)), closes [#417](https://github.com/hungovercoders/slopstopper/issues/417)
* **hygiene:** complexity skips test files and gitignored output ([#419](https://github.com/hungovercoders/slopstopper/issues/419)) ([fc00e65](https://github.com/hungovercoders/slopstopper/commit/fc00e6547c6274918f4996d039c114a3c0135b41)), closes [#404](https://github.com/hungovercoders/slopstopper/issues/404)
* **hygiene:** docs-accuracy resolves bare filenames anywhere in the repo ([#420](https://github.com/hungovercoders/slopstopper/issues/420)) ([4583855](https://github.com/hungovercoders/slopstopper/commit/458385560f5b2a57a9f0cce8d5ad09657a48818d)), closes [#402](https://github.com/hungovercoders/slopstopper/issues/402)
* **install:** own package.json seed, refresh the .gitignore block, detect Cloudflare ([#415](https://github.com/hungovercoders/slopstopper/issues/415)) ([96f41f2](https://github.com/hungovercoders/slopstopper/commit/96f41f244626931cda80355fd0ed104913c7450c)), closes [#398](https://github.com/hungovercoders/slopstopper/issues/398) [#399](https://github.com/hungovercoders/slopstopper/issues/399) [#409](https://github.com/hungovercoders/slopstopper/issues/409)
* **reliability:** audit a deployment's environment_url, never its Actions log ([#427](https://github.com/hungovercoders/slopstopper/issues/427)) ([90badd2](https://github.com/hungovercoders/slopstopper/commit/90badd25c453b0b37b2e3298cc72a96d68bcc5d9)), closes [#416](https://github.com/hungovercoders/slopstopper/issues/416)
* **reliability:** resolve page paths under the base URL and relative hrefs from the clicked page ([#413](https://github.com/hungovercoders/slopstopper/issues/413)) ([d4f58c1](https://github.com/hungovercoders/slopstopper/commit/d4f58c133de9682b8001ff9a9c080bba02edbd47)), closes [#400](https://github.com/hungovercoders/slopstopper/issues/400) [#401](https://github.com/hungovercoders/slopstopper/issues/401)

## [0.18.0](https://github.com/hungovercoders/slopstopper/compare/v0.17.0...v0.18.0) (2026-10-10)


### Features

* **doctor:** flag broken tools and ss-* workflows GitHub disabled ([#395](https://github.com/hungovercoders/slopstopper/issues/395)) ([4c9ff4e](https://github.com/hungovercoders/slopstopper/commit/4c9ff4e0dc226611aefa8d6f862570c26ff9aa11))


### Bug Fixes

* **hygiene:** label soft routes by source file, line and target ([#393](https://github.com/hungovercoders/slopstopper/issues/393)) ([480d7f4](https://github.com/hungovercoders/slopstopper/commit/480d7f40802cb14a3a6522a3ddd4fa244d7a9a9a)), closes [#392](https://github.com/hungovercoders/slopstopper/issues/392)
* **install:** warn when the shell still runs the old CLI after a pin move ([#396](https://github.com/hungovercoders/slopstopper/issues/396)) ([94e89e4](https://github.com/hungovercoders/slopstopper/commit/94e89e4fb583cfd79b3fb967fa0d95787e6ff8d7)), closes [#390](https://github.com/hungovercoders/slopstopper/issues/390)
* **reliability:** stage Playwright run files in .ss/.run, not .ss/ ([#394](https://github.com/hungovercoders/slopstopper/issues/394)) ([a5cd5a8](https://github.com/hungovercoders/slopstopper/commit/a5cd5a84a42143e422fc2617ac8e51f37b77518e)), closes [#389](https://github.com/hungovercoders/slopstopper/issues/389)

## [0.17.0](https://github.com/hungovercoders/slopstopper/compare/v0.16.0...v0.17.0) (2026-10-10)


### Features

* **site:** self-host Nunito so every platform gets the rounded face ([#379](https://github.com/hungovercoders/slopstopper/issues/379)) ([9632e8a](https://github.com/hungovercoders/slopstopper/commit/9632e8a5779ac2e7d22abdcc0a8e67a9d27823ae)), closes [#370](https://github.com/hungovercoders/slopstopper/issues/370)


### Bug Fixes

* **ci:** time-box the Playwright browser install so a stalled download fails fast ([#387](https://github.com/hungovercoders/slopstopper/issues/387)) ([dc01f2c](https://github.com/hungovercoders/slopstopper/commit/dc01f2caad5971d271c477de02a214438d15c223)), closes [#386](https://github.com/hungovercoders/slopstopper/issues/386)
* **site:** give the Features page a jump row and a way back to the top ([#378](https://github.com/hungovercoders/slopstopper/issues/378)) ([67d486a](https://github.com/hungovercoders/slopstopper/commit/67d486a72f67f024e1abb770d16297341f0670b8))
* **site:** group the Tools cards by loop and let each size to its content ([#376](https://github.com/hungovercoders/slopstopper/issues/376)) ([7ab5fa6](https://github.com/hungovercoders/slopstopper/commit/7ab5fa6d9a4ddbcd76455a97d1a86c5b63f01c1e)), closes [#366](https://github.com/hungovercoders/slopstopper/issues/366)
* **site:** keep each highlighted headline phrase on one line ([#374](https://github.com/hungovercoders/slopstopper/issues/374)) ([266d315](https://github.com/hungovercoders/slopstopper/commit/266d315b68b661913399ae1bd3ffe85c8e6ab291)), closes [#369](https://github.com/hungovercoders/slopstopper/issues/369)
* **site:** keep the home install section short, with the runbook detail one click away ([#377](https://github.com/hungovercoders/slopstopper/issues/377)) ([65023ce](https://github.com/hungovercoders/slopstopper/commit/65023ce373070f3ca7e6116e22777e2364083d28)), closes [#367](https://github.com/hungovercoders/slopstopper/issues/367)
* **site:** mobile header, tap targets, touch copy buttons, color-scheme, comments placeholder, tablet overflow ([#375](https://github.com/hungovercoders/slopstopper/issues/375)) ([ea13f51](https://github.com/hungovercoders/slopstopper/commit/ea13f51cc729a2bbcf030fbd5ae6809e3ebf618d)), closes [#371](https://github.com/hungovercoders/slopstopper/issues/371)
* **site:** show the --profile flag in the home install block without scrolling ([#372](https://github.com/hungovercoders/slopstopper/issues/372)) ([2bdb94b](https://github.com/hungovercoders/slopstopper/commit/2bdb94b4dfe3be0926cc525bf3a739533b4ebd62)), closes [#365](https://github.com/hungovercoders/slopstopper/issues/365)

## [0.16.0](https://github.com/hungovercoders/slopstopper/compare/v0.15.0...v0.16.0) (2026-10-05)


### Features

* **reliability:** add reliability:e2e, portable user-journey check ([#362](https://github.com/hungovercoders/slopstopper/issues/362)) ([dafdb3c](https://github.com/hungovercoders/slopstopper/commit/dafdb3c20dff9fe33964ef8d34047a814666433e)), closes [#355](https://github.com/hungovercoders/slopstopper/issues/355) [#349](https://github.com/hungovercoders/slopstopper/issues/349)


### Bug Fixes

* **ci:** rewrite this repo's labeler.yml for the ss- prefix and the CLI layout ([#358](https://github.com/hungovercoders/slopstopper/issues/358)) ([b0754d6](https://github.com/hungovercoders/slopstopper/commit/b0754d61bce679922eaba46448019d68b23fa702))
* **site:** lay the five loop cards out in two columns ([#361](https://github.com/hungovercoders/slopstopper/issues/361)) ([800f3d7](https://github.com/hungovercoders/slopstopper/commit/800f3d709c88887e3b58b241f406bd74809358d1))

## [0.15.0](https://github.com/hungovercoders/slopstopper/compare/v0.14.0...v0.15.0) (2026-10-03)


### ⚠ BREAKING CHANGES

* **hygiene:** a repo on the pre-0.15 Map Pattern fails hygiene:entry-files and hygiene:docs-structure after moving its CLI pin: docs/index.md must become docs/README.md with trigger-first rows, CLAUDE.md must be exactly `@AGENTS.md`, every .md link in AGENTS.md must say when to read it, and every doc under docs/ needs an explicit route. `hygiene.entry_files.max_words` is no longer read (use max_tokens); `hygiene.docs_structure.require_indexed_docs` is read as require_routed_docs. Each report carries the paste-ready fix; the slopstopper-install skill's Step 5 carries the migration.

### Features

* **api:** add reliability:api-latency and hygiene:openapi checks ([#333](https://github.com/hungovercoders/slopstopper/issues/333)) ([f693490](https://github.com/hungovercoders/slopstopper/commit/f693490d9e85c29115c7e2c36e5afc008c87a3cc))
* **ci:** one PR summary comment, compact per-check detail ([#329](https://github.com/hungovercoders/slopstopper/issues/329)) ([7bd97aa](https://github.com/hungovercoders/slopstopper/commit/7bd97aae6edd46812f860de7504985af688addab))
* **hygiene:** enforce AGENTS.md-first docs — token budgets, explicit routes, docs/README.md map ([#346](https://github.com/hungovercoders/slopstopper/issues/346)) ([a215d84](https://github.com/hungovercoders/slopstopper/commit/a215d8499a7bbaee205fc988862ca5bcd981b15b))
* **install:** seed a short starter config, not the 430-line schema ([#341](https://github.com/hungovercoders/slopstopper/issues/341)) ([bf6b24b](https://github.com/hungovercoders/slopstopper/commit/bf6b24bfa1e37c09bff3e9abda96d46b9a0d7a14))
* **security:** scan APIs with ZAP's OpenAPI mode ([#332](https://github.com/hungovercoders/slopstopper/issues/332)) ([5618969](https://github.com/hungovercoders/slopstopper/commit/5618969f933000c33ea0bfb1dbfc08984b3a4acc))
* tailor the installed check set to the repo's shape via profiles ([#326](https://github.com/hungovercoders/slopstopper/issues/326)) ([0f6af67](https://github.com/hungovercoders/slopstopper/commit/0f6af675be3fc4f47c2de72bf3316f5716835cda))
* tailor the installed check set to the repo's shape via profiles ([#327](https://github.com/hungovercoders/slopstopper/issues/327)) ([322b7b7](https://github.com/hungovercoders/slopstopper/commit/322b7b785dec9968324f8101fd1816ee107e1fa7))


### Bug Fixes

* **cli:** one exit-code contract, honoured by every check ([#337](https://github.com/hungovercoders/slopstopper/issues/337)) ([e73a4e7](https://github.com/hungovercoders/slopstopper/commit/e73a4e75290a82756b939fbed6b0c78bf9853660))
* **contributing:** make every contributor task do real work in this repo ([#343](https://github.com/hungovercoders/slopstopper/issues/343)) ([d018d96](https://github.com/hungovercoders/slopstopper/commit/d018d96ee37efd678c4085bc0824046a6c2663e3))
* nine drift fixes from the repo review ([#335](https://github.com/hungovercoders/slopstopper/issues/335)) ([fa98432](https://github.com/hungovercoders/slopstopper/commit/fa9843266962114f51f6ef07b3b331a1d12549ae))
* **security:** redact secret values from the gitleaks JSON report ([#334](https://github.com/hungovercoders/slopstopper/issues/334)) ([9b52539](https://github.com/hungovercoders/slopstopper/commit/9b5253997fc17396ea74d2d347ce16482c5f8173))

## [0.14.0](https://github.com/hungovercoders/slopstopper/compare/v0.13.0...v0.14.0) (2026-07-10)


### Features

* **reliability:** add sitemap.xml completeness + drift check ([#308](https://github.com/hungovercoders/slopstopper/issues/308)) ([4b0b5ae](https://github.com/hungovercoders/slopstopper/commit/4b0b5ae66979e49a4e5b82cbf391b3240d7be7cf))


### Bug Fixes

* **hygiene:** make the complexity check gate in the CLI, fail at CCN 15 ([#309](https://github.com/hungovercoders/slopstopper/issues/309)) ([802f9ee](https://github.com/hungovercoders/slopstopper/commit/802f9eeeb7084cce1f1a7ee441e1497c4169124c))

## [0.13.0](https://github.com/hungovercoders/slopstopper/compare/v0.12.0...v0.13.0) (2026-07-08)


### Features

* **reliability:** add robots.txt discoverability + de-index guard check ([#306](https://github.com/hungovercoders/slopstopper/issues/306)) ([dc3d57d](https://github.com/hungovercoders/slopstopper/commit/dc3d57d9906236abb7dcc65e9d7ae2c4b2eefc6d))

## [0.12.0](https://github.com/hungovercoders/slopstopper/compare/v0.11.0...v0.12.0) (2026-07-06)


### Features

* **install:** add pre-push hook for the fast hygiene checks ([#302](https://github.com/hungovercoders/slopstopper/issues/302)) ([376d86c](https://github.com/hungovercoders/slopstopper/commit/376d86c1a5eebe3d6d7a38d810e9d2615092ed58))
* **reliability:** add llms.txt AI-discoverability check + ship the site's own ([#301](https://github.com/hungovercoders/slopstopper/issues/301)) ([59a0568](https://github.com/hungovercoders/slopstopper/commit/59a0568a9ec9591d236245755aa2f4e2284e2af7))


### Bug Fixes

* **app:** bump actions/checkout@v4 → [@v6](https://github.com/v6) in workflow excerpts ([#290](https://github.com/hungovercoders/slopstopper/issues/290)) ([b21f049](https://github.com/hungovercoders/slopstopper/commit/b21f0492cb7c7ebb99c9449e4290a7427f3aaf26))
* correct ATTRIBUTIONS record and enforce dependency licence gate ([#298](https://github.com/hungovercoders/slopstopper/issues/298)) ([760dff4](https://github.com/hungovercoders/slopstopper/commit/760dff4439ae4c157b694792a7c830bf60705e9c))

## [0.11.0](https://github.com/hungovercoders/slopstopper/compare/v0.10.0...v0.11.0) (2026-06-21)


### Features

* **install:** pin slopstopper-cli via mise (replace cli_version) ([eb943d2](https://github.com/hungovercoders/slopstopper/commit/eb943d2f081d0cc4776a8a5d91bb2ea3e7422813))
* **install:** pin slopstopper-cli via mise, not .slopstopper.yml cli_version ([b84cbe9](https://github.com/hungovercoders/slopstopper/commit/b84cbe96c008b75ac0bc0de2b155e32a9ff6e095))

## [0.10.0](https://github.com/hungovercoders/slopstopper/compare/v0.9.0...v0.10.0) (2026-06-20)


### Features

* **install:** pin slopstopper-cli per-repo via cli_version ([0760acb](https://github.com/hungovercoders/slopstopper/commit/0760acb5d15442c806f92bb61f958bc29db5c4d4))
* **install:** pin slopstopper-cli per-repo via cli_version ([c0e3f18](https://github.com/hungovercoders/slopstopper/commit/c0e3f188b0fdcfffb0e9ca08fb68fa5852c3a087))

## [0.9.0](https://github.com/hungovercoders/slopstopper/compare/v0.8.0...v0.9.0) (2026-06-20)


### Features

* **install:** surface what's-new on CLI upgrade ([683f1a2](https://github.com/hungovercoders/slopstopper/commit/683f1a2e0362000e3934cd97a510b4cfbe77d38e))


### Bug Fixes

* **install:** detect and remediate silently-stale CLI on refresh ([4005153](https://github.com/hungovercoders/slopstopper/commit/400515374b5fd2bb8caf3dc7f97915bb23b3208a))
* **install:** detect and remediate silently-stale CLI on refresh ([b01ca11](https://github.com/hungovercoders/slopstopper/commit/b01ca1187f8db6c8e8d94854c78908b2ce8c5282))
* **skill:** stop drift check flagging ss-release.yml; lead with two-step install ([7abd5be](https://github.com/hungovercoders/slopstopper/commit/7abd5be4753816d6d623de6a24d6582b63f0fa91))
* **skill:** stop drift check flagging ss-release.yml; lead with two-step install ([99a8b89](https://github.com/hungovercoders/slopstopper/commit/99a8b89d3c5d21aa2074558aac28b58df81dba10))

## [0.8.0](https://github.com/hungovercoders/slopstopper/compare/v0.7.1...v0.8.0) (2026-06-20)


### Features

* **hygiene:** enforce and remediate the Map Pattern in entry-files check ([#276](https://github.com/hungovercoders/slopstopper/issues/276)) ([cc6de07](https://github.com/hungovercoders/slopstopper/commit/cc6de07b13a8f89e65fbe03110f8142c10136c23))
* **skills:** install at project level and merge update into install ([3bd27f9](https://github.com/hungovercoders/slopstopper/commit/3bd27f9a40c3b8f7906631fc8b433b5c2187d956))
* **skills:** install at project level and merge update into install ([5c58f81](https://github.com/hungovercoders/slopstopper/commit/5c58f81f1262ead4faf0e95104537a9a2a9ce7a4))

## [0.7.1](https://github.com/hungovercoders/slopstopper/compare/v0.7.0...v0.7.1) (2026-06-19)


### Bug Fixes

* **reliability:** read scheduled-run URL from .slopstopper.yml urls.production ([f4c36b7](https://github.com/hungovercoders/slopstopper/commit/f4c36b77a8aab0272e5cb3905ed126de123659b2))
* **reliability:** read scheduled-run URL from .slopstopper.yml urls.production ([c91136f](https://github.com/hungovercoders/slopstopper/commit/c91136f28aa441c66842dd3e394bd8b007c03e9e))

## [0.7.0](https://github.com/hungovercoders/slopstopper/compare/v0.6.0...v0.7.0) (2026-06-16)


### Features

* **checks:** META + markdown reports for smoke/accessibility/broken-links ([621ff93](https://github.com/hungovercoders/slopstopper/commit/621ff937d801b8040007b69641982b6750af76de))
* **checks:** META + markdown reports for smoke/accessibility/broken-links ([1da48df](https://github.com/hungovercoders/slopstopper/commit/1da48dfbe49d9e378f90ca45bf7dcb86dea40d72))
* **cli:** add `slopstopper badges` to generate README status block ([44f5521](https://github.com/hungovercoders/slopstopper/commit/44f55211feba04723c7baaf1d54203867c03e4ae))
* **cli:** add slopstopper badges to generate README status block ([3085dea](https://github.com/hungovercoders/slopstopper/commit/3085deaabf709a98c35b9116766996d666ba0567))
* **emit:** add --on-pass=close to slopstopper emit ([ada4ce1](https://github.com/hungovercoders/slopstopper/commit/ada4ce19690bbbf094cd27e121121fcdaad7135c))
* **emit:** add --on-pass=close to slopstopper emit ([7b0564d](https://github.com/hungovercoders/slopstopper/commit/7b0564ddc9289474667f856759a688a0f7a53211))
* **emit:** brand emitted issues with slopstopper label + body marker ([787d2ef](https://github.com/hungovercoders/slopstopper/commit/787d2efcb0b20c7fef75bca3665232f1e6492f4b))
* **emit:** brand emitted issues with slopstopper label + body marker ([12272da](https://github.com/hungovercoders/slopstopper/commit/12272dacbab5650090e31e0fc6fda709d39b431c))
* **install:** bundle Claude Code skill trio into install.sh ([bcae4aa](https://github.com/hungovercoders/slopstopper/commit/bcae4aa988f7ed1a2ff0e0ee7c648131183113a5))
* **install:** bundle Claude Code skill trio into install.sh ([9c5e81b](https://github.com/hungovercoders/slopstopper/commit/9c5e81bbf47c489ad943792d6897068a5272f915))
* **workflows:** unify issue lifecycle through `slopstopper emit` ([a95ca38](https://github.com/hungovercoders/slopstopper/commit/a95ca38526885c6a6d74b946647ddccb9070d5aa))
* **workflows:** unify issue lifecycle through slopstopper emit ([1d70ece](https://github.com/hungovercoders/slopstopper/commit/1d70eced847c829bb418109aab45b9ac5075bcdb))


### Bug Fixes

* **workflows:** dedupe failure-issue against slopstopper body marker ([648de14](https://github.com/hungovercoders/slopstopper/commit/648de14b984444ebf7734b24382500ea4175282f))
* **workflows:** dedupe failure-issue against slopstopper body marker ([d5e985e](https://github.com/hungovercoders/slopstopper/commit/d5e985e7f0a71ba7279bbdbb2bd77afff59bf926))

## [0.6.0](https://github.com/hungovercoders/slopstopper/compare/v0.5.1...v0.6.0) (2026-06-15)


### Features

* **canonical:** make task ss:* the single invocation surface — CI included ([821ddd3](https://github.com/hungovercoders/slopstopper/commit/821ddd3de3c04d5dda98f3c6d8126c88e7172ca5))
* **canonical:** make task ss:* the single invocation surface — CI included ([392b729](https://github.com/hungovercoders/slopstopper/commit/392b729faaa790926a7254a1fd685de1dfde1ddd))


### Bug Fixes

* **canonical:** emit + docs-accuracy follow-ups for the alignment refactor ([5fdc656](https://github.com/hungovercoders/slopstopper/commit/5fdc65635be55b57b2bd1ed6f595d272b3a4e8f8))
* **canonical:** handle shim/CLI name aliases in workflow + --no-task transform ([ba92c75](https://github.com/hungovercoders/slopstopper/commit/ba92c75f4cb315df3a938980c0f628222b29bdd8))

## [0.5.1](https://github.com/hungovercoders/slopstopper/compare/v0.5.0...v0.5.1) (2026-06-14)


### Bug Fixes

* **cli:** exit non-zero on HIGH+ vulnerabilities to match CI gate behaviour ([2f5854b](https://github.com/hungovercoders/slopstopper/commit/2f5854bdba7e9013bc7819de51b43b1755a9b62d))
* **cli:** exit non-zero on HIGH+ vulnerabilities to match CI gate behaviour ([80be098](https://github.com/hungovercoders/slopstopper/commit/80be098886f2edd9549b331115b0cce8d56e25a9))
* **cli:** make complexity, playwright, serve work out of the box ([07ee735](https://github.com/hungovercoders/slopstopper/commit/07ee735d19b44443fa396ef01de79020860452ff))
* **cli:** make complexity, playwright, serve work out of the box ([70cf72e](https://github.com/hungovercoders/slopstopper/commit/70cf72e64e7a6473457fb24c7f375e29c1e2ad7f))
* **install:** three install.sh issues found by first real adopter ([29bbff8](https://github.com/hungovercoders/slopstopper/commit/29bbff8eb5381e3092365c491144ab04439fce33))
* **install:** three install.sh issues found by first real adopter ([f3ddb84](https://github.com/hungovercoders/slopstopper/commit/f3ddb8497b6db9d188da882a33eecab99ef0fad2))
* **server.js:** split parseCloudflareHeaders to satisfy CCN &lt; 10 ([f7d059c](https://github.com/hungovercoders/slopstopper/commit/f7d059c4d02b74d1feb68eb60a02b1462148d323))

## [0.5.0](https://github.com/hungovercoders/slopstopper/compare/v0.4.1...v0.5.0) (2026-06-14)


### Features

* **release-please:** mint App token to eliminate manual touch points ([#251](https://github.com/hungovercoders/slopstopper/issues/251)) ([20365a3](https://github.com/hungovercoders/slopstopper/commit/20365a3f5f20d12564692655ef57c28d30fabfcb))

## [0.4.1](https://github.com/hungovercoders/slopstopper/compare/v0.4.0...v0.4.1) (2026-06-14)


### Bug Fixes

* **release:** tighten sanity-check sed to handle trailing marker comment ([#248](https://github.com/hungovercoders/slopstopper/issues/248)) ([29cdd07](https://github.com/hungovercoders/slopstopper/commit/29cdd0705f24c3fe400bb7fff07d8463072f18d0))

## [0.4.0](https://github.com/hungovercoders/slopstopper/compare/v0.3.0...v0.4.0) (2026-06-14)


### Features

* **release:** automate version bumps + tagging via release-please ([#245](https://github.com/hungovercoders/slopstopper/issues/245)) ([b7c1944](https://github.com/hungovercoders/slopstopper/commit/b7c1944a04a6667228236f6f121bae7ad25c0814))


### Bug Fixes

* **release-please:** switch to release-type simple with extra-files ([#246](https://github.com/hungovercoders/slopstopper/issues/246)) ([6ffd25e](https://github.com/hungovercoders/slopstopper/commit/6ffd25ec4468860d04ab802e2fdad98b65c328e7))

## [Unreleased]

Nothing yet.

## [0.3.0] - 2026-06-14

First release published to PyPI. Adopter docs, the website, `install.sh` and every `ss-*-check.yml` workflow stop pinning a wheel URL — they all install `slopstopper-cli` by name, so future releases land everywhere automatically with no doc churn.

### Added

- **PyPI distribution.** `pipx install slopstopper-cli` (and `pipx upgrade slopstopper-cli`) is now the canonical install. Released to PyPI on every `v*.*.*` tag via the OIDC Trusted Publisher flow — no API tokens, no manual `twine upload`. The release workflow's new `Publish to PyPI` step uses `pypa/gh-action-pypi-publish@release/v1` with `skip-existing: true` for idempotent re-runs.
- **LICENSE bundled in the wheel.** Added `cli/LICENSE` (verbatim copy of the root MIT licence) and `license-files = ["LICENSE"]` to `cli/pyproject.toml`. PyPI displays the licence correctly and `python -m zipfile -l` confirms it ships at the wheel root.
- **`ATTRIBUTIONS.md` at repo root.** Canonical third-party crediting for every tool slopstopper-cli subprocess-invokes (Semgrep, Gitleaks, Trivy, OWASP ZAP, Playwright, axe-core, Lighthouse CI, Lizard, markdownlint-cli, Docker, GitHub CLI, Node.js) plus build-time GitHub Actions. Linked from `README.md`, `cli/README.md`, `app/tools.html`, and `cli/pyproject.toml`'s `Acknowledgements` URL.
- **`maintainers` field** on `cli/pyproject.toml` so PyPI has a contact for the project.
- **`Changelog` + `Acknowledgements` URLs** on the PyPI project page (`[project.urls]`).
- **Per-tool licence badges** on every card in `app/tools.html` plus a footer linking to `ATTRIBUTIONS.md`.

### Changed

- **`install.sh`** no longer carries a pinned wheel URL constant. Installs/refreshes from PyPI directly via `pipx install slopstopper-cli` (or `python3 -m pip install --user --upgrade slopstopper-cli` fallback).
- **All 15 `ss-*-check.yml` workflows** install with `pip install slopstopper-cli` instead of the pinned `releases/download/v0.2.1/slopstopper_cli-0.2.1-py3-none-any.whl` URL. Adopter CI tracks the latest release automatically.
- **`docs/runbooks/RELEASE.md`** rewritten around the new flow. The "Bump the pinned wheel URL" step and its `sed` one-liner are gone. The "Manual PyPI publish" section is gone (automated). New section: "One-time PyPI Trusted Publisher setup".
- **READMEs + website install commands** all show `pipx install slopstopper-cli`; release-tag links go to `releases/latest` rather than a pinned version.

### Notes for adopters

Existing adopter repos keep working — their installed workflows still install slopstopper-cli 0.2.1 from the GitHub Release URL until they next run `install.sh`, which rewrites their workflows to the new `pip install slopstopper-cli` shape. No forced migration.

## [0.2.1] - 2026-06-14

### Added

- **Build provenance attestations** on release artifacts. The release workflow now signs every wheel and sdist with `actions/attest-build-provenance@v2` (Sigstore keyless OIDC). Adopters verify with `gh attestation verify <wheel> --owner hungovercoders` — proves the artifact came from this repo's release pipeline, not a tampered upload. See [`docs/runbooks/RELEASE.md`](docs/runbooks/RELEASE.md#verifying-build-provenance).

## [0.2.0] - 2026-06-13

First release with a real product surface. Phase 2 of the CLI pivot is complete — every check runs through `slopstopper-cli` and adopter `.ss/` directories shrink to `reports/` + the workflow manifest. The CLI now has a polished UX (bare-invocation banner, `checks list`, `doctor`, consistent output module, `--quiet`).

### Added

- `slopstopper checks list [--category <c>] [--json]` — walk the registry and print every check with its one-line summary.
- `slopstopper doctor` — verify external tools (`node`, `gh`, `lizard`, `semgrep`, `gitleaks`, `trivy`, `docker`) are installed; exit 1 only when a required-and-enabled tool is missing.
- `slopstopper templates {list, path, eject}` — inspect and customise bundled templates (Playwright specs, lighthouserc dev/prod, server.js).
- `slopstopper serve` — runs the bundled static server via `execvp(node)` so backgrounded `slopstopper serve &` gives bash the right PID for kill.
- `slopstopper config get <key> [<default>]` — read `.slopstopper.yml` values for shell scripting.
- `slopstopper discover <check> --event <e>` — resolve `pages.<check>` via sitemap / changed / explicit list.
- Bare `slopstopper` prints a friendly command grid + Quick-start block (no longer errors).
- `--quiet` / `-q` global flag suppresses decorative output while preserving reports.
- Shared output module (`slopstopper.output`) with consistent `running` / `success` / `warn` / `error` / `info` / `status` / `section` / `separator` / `footer` formatters.

### Changed

- `lighthouserc.prod.json` lifted into the wheel; `--prod` flag on `cwv.py` selects it.
- `server.js` lifted into the wheel; CWV/smoke/accessibility/SEO/broken-links/DAST workflows all use `slopstopper serve &` instead of `node server.js &`.
- `.ss/` in a fresh adopter install now contains only `reports/` and `.workflows-installed`.
- `install.sh` pip-installs `slopstopper-cli` (pipx-preferred) and scrubs legacy byte-equal copies of bundled templates from existing adopter `.ss/` directories.
- Workflows now emit PR comments and tracking issues via `slopstopper emit --target {pr-comment, issue}` instead of inline `actions/github-script@v7` JS.

### Removed

- Every Python/bash script previously seeded into adopter repos under `.ss/scripts/` — logic lives in `slopstopper-cli` now.
- `templates-sync-check` CI job — `.ss/` no longer ships byte-equal duplicates of `cli/slopstopper/data/`.

## [0.1.0] - 2026-06-12

Initial CLI pivot. Bash + Python scripts under `.ss/scripts/` remain authoritative; the Python `slopstopper-cli` package reproduces them check-by-check while CI runs both paths in parallel via the `bash↔cli parity` job.

### Added

- `slopstopper run <category>:<check>` dispatcher and the 15 check modules under `cli/slopstopper/checks/`.
- `slopstopper emit <check> --target {pr-comment, issue}` with find-or-update semantics.
- Templates resolver: `.ss/<filename>` override → package-data fallback.
