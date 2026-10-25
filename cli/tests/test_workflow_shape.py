"""Guard: the ss-* workflows share their plumbing through the composite actions.

Before `.github/actions/ss-setup` and `ss-resolve-url` existed, the same
three toolchain steps were copied into 24 workflows and the same
`validate_url()` shell function into 12, with four mutually incompatible
`if:` dialects on the emit step growing around them. Copies drift, and that
is how two workflows ended up never deleting their PR comment.

These tests keep the plumbing in one place: no ss-* workflow may inline
what the actions provide, every local `uses:` must resolve, and every
`steps.<id>.outputs` reference must name a step that exists (a renamed
step id fails silently in Actions, where the expression just evaluates empty).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github/workflows"
ACTIONS_DIR = REPO_ROOT / ".github/actions"

# Not built on the composite actions: they aren't checks and don't need the
# CLI toolchain (or, for the release, need a different Python setup).
EXEMPT = {
    "ss-release.yml",
    "ss-hygiene-auto-label-pr.yml",
    "ss-hygiene-doc-updater.lock.yml",
    "ss-security-vulnerability-new-check.yml",
    "ss-workflow-failure-issue.yml",
}

WORKFLOWS = sorted(p.name for p in WORKFLOWS_DIR.glob("ss-*.yml"))
BUILT_ON_ACTIONS = [w for w in WORKFLOWS if w not in EXEMPT]


def _text(name: str) -> str:
    return (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def test_the_composite_actions_exist():
    for action in ("ss-setup", "ss-resolve-url", "ss-playwright"):
        assert (ACTIONS_DIR / action / "action.yml").is_file(), action


def test_the_fixture_finds_workflows():
    assert len(BUILT_ON_ACTIONS) >= 15


@pytest.mark.parametrize("workflow", BUILT_ON_ACTIONS)
def test_workflow_sets_up_through_the_composite_action(workflow):
    text = _text(workflow)
    assert "uses: ./.github/actions/ss-setup" in text, f"{workflow} does not use ss-setup"
    for inlined in ("jdx/mise-action", "actions/setup-python", "pip install -e ./cli"):
        assert inlined not in text, (
            f"{workflow} inlines `{inlined}`, but that step lives in .github/actions/ss-setup"
        )


@pytest.mark.parametrize("workflow", BUILT_ON_ACTIONS)
def test_workflow_does_not_inline_url_resolution(workflow):
    assert "validate_url()" not in _text(workflow), (
        f"{workflow} defines validate_url(), but URL resolution lives in .github/actions/ss-resolve-url"
    )


@pytest.mark.parametrize("workflow", BUILT_ON_ACTIONS)
def test_ss_setup_follows_checkout(workflow):
    """A later `pip install <tool>` or `npm ci` relies on the Python and
    node that ss-setup puts on PATH, so it has to come first."""
    names = re.findall(r"^      - name: (.+)$", _text(workflow), re.M)
    assert names[0].startswith("Checkout"), workflow
    assert names[1] == "Set up slopstopper", f"{workflow}: second step is {names[1]!r}"


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_every_local_action_reference_resolves(workflow):
    for ref in re.findall(r"uses: \./\.github/actions/([A-Za-z0-9_-]+)", _text(workflow)):
        assert (ACTIONS_DIR / ref / "action.yml").is_file(), f"{workflow} uses missing action {ref}"


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_every_step_output_reference_names_a_real_step(workflow):
    text = _text(workflow)
    ids = set(re.findall(r"^\s+id:\s*(\S+)\s*$", text, re.M))
    refs = set(re.findall(r"steps\.([A-Za-z0-9_-]+)\.", text))
    assert refs <= ids, f"{workflow} references steps that don't exist: {sorted(refs - ids)}"


@pytest.mark.parametrize("workflow", BUILT_ON_ACTIONS)
def test_resolved_urls_reach_shell_commands_through_environment(workflow):
    for step in re.split(r"(?m)^      - ", _text(workflow)):
        if "outputs.url" not in step:
            continue
        run = step.find("run:")
        if run >= 0:
            assert re.search(
                r"(?m)^\s+[A-Za-z_]+:\s*\$\{\{\s*steps\.[^}]+\.outputs\.url\s*\}\}",
                step[:run],
            ), workflow
            assert not re.search(r"\$\{\{\s*steps\.[^}]+\.outputs\.url", step[run:]), workflow


def test_the_dependency_review_reads_the_seeded_allowlist():
    """`deny-licenses` is deprecated by the action and mutually exclusive with
    an allowlist, so the policy lives in the seeded config file, and that
    default leaves out every GPL, LGPL and AGPL id."""
    workflow = _text("ss-security-vulnerability-new-check.yml")
    assert not re.search(r"(?m)^\s+deny-licenses:", workflow)
    assert "config-file:" in workflow and ".github/dependency-review-config.yml" in workflow
    template = (REPO_ROOT / "templates" / "dependency-review-config.yml.example").read_text()
    allowed = re.findall(r"(?m)^  - (\S+)$", template.split("allow-licenses:", 1)[1].split("\n\n", 1)[0])
    assert "MIT" in allowed and "Apache-2.0" in allowed
    assert not [lic for lic in allowed if re.match(r"(A|L)?GPL-", lic)], allowed
    own = (REPO_ROOT / ".github" / "dependency-review-config.yml").read_text()
    assert own == template, "this repository runs the default it ships"


def test_a_missing_licence_allowlist_is_announced_not_silent():
    """Deleting the allowlist turns the licence check off; the run must say
    so rather than pass as if licences had been checked."""
    workflow = _text("ss-security-vulnerability-new-check.yml")
    step = re.search(
        r"- name: 'Warn when the licence allowlist is missing'\n"
        r"\s+if: hashFiles\('\.github/dependency-review-config\.yml'\) == ''\n"
        r"\s+run: \|\n((?:\s{10}.*\n)+)",
        workflow,
    )
    assert step, "no warning step guarded on the missing allowlist"
    assert "::warning" in step.group(1) and "GITHUB_STEP_SUMMARY" in step.group(1)
    assert workflow.index("Warn when the licence allowlist") < workflow.index("name: 'Dependency Review'")


def test_resolve_url_declares_the_outputs_the_workflows_read():
    action = (ACTIONS_DIR / "ss-resolve-url" / "action.yml").read_text(encoding="utf-8")
    # Only the `outputs:` block: an input name read as an output evaluates
    # empty just as silently as a typo would.
    outputs_block = re.search(r"^outputs:\n((?:  .*\n|\n)+)", action, re.M)
    assert outputs_block, "ss-resolve-url declares no outputs"
    declared = set(re.findall(r"^  ([a-z_]+):\n    description", outputs_block.group(1), re.M))
    assert declared == {"url", "skip", "use_local", "prod"}, declared
    used: set[str] = set()
    for workflow in BUILT_ON_ACTIONS:
        text = _text(workflow)
        if "ss-resolve-url" not in text:
            continue
        step_id = re.search(r"id: (\S+)\n(?:.*\n){0,5}?\s+uses: \./\.github/actions/ss-resolve-url", text)
        assert step_id, workflow
        used |= set(re.findall(rf"steps\.{re.escape(step_id.group(1))}\.outputs\.([a-z_]+)", text))
    assert used <= declared, f"workflows read outputs ss-resolve-url doesn't declare: {sorted(used - declared)}"


@pytest.mark.parametrize("workflow", BUILT_ON_ACTIONS)
def test_local_build_steps_follow_the_resolved_url(workflow):
    """The event → local-build table lives in ss-resolve-url. A workflow that
    gates its build/serve steps on `github.event_name` instead keeps a second
    copy, which drifts: the serve step stops matching the URL being audited."""
    text = _text(workflow)
    if "ss-resolve-url" not in text:
        return
    hand_rolled = re.findall(
        r"- name: ((?:Build|Start|Stop)[^\n]*)\n\s+if: [^\n]*github\.event_name == 'pull_request' \|\| github\.event_name == 'push'",
        text,
    )
    assert not hand_rolled, f"{workflow}: gate {hand_rolled} on steps.<id>.outputs.use_local"


# ── the Playwright install lives in one composite action (#535) ──
#
# The apt phase, the time-boxed browser download and the browser cache were
# once copied into seven workflow steps; #386 and #527 each edited all seven
# in lockstep. They live in .github/actions/ss-playwright now, and a
# workflow that needs Chromium `uses:` it after `npm ci`.

PLAYWRIGHT_ACTION = ACTIONS_DIR / "ss-playwright" / "action.yml"
ALL_WORKFLOWS = sorted(p.name for p in WORKFLOWS_DIR.glob("*.yml"))
PLAYWRIGHT_CALLERS = [w for w in ALL_WORKFLOWS if "uses: ./.github/actions/ss-playwright" in _text(w)]


def _steps(text: str) -> list[str]:
    """Each step block, from the line that opens it (`- name:`, `- uses:`
    or `- run:`) to the next step; the file header is dropped. An unnamed
    step after the one under test must not fold into it."""
    return re.split(r"(?m)^(?=\s+- (?:name|uses|run): )", text)[1:]


def test_the_fixture_finds_playwright_callers():
    """The four browser checks, the CLI's own CI and the Copilot environment,
    exactly: a caller added or dropped is a deliberate change to this list."""
    assert PLAYWRIGHT_CALLERS == [
        "ci-cli.yml",
        "copilot-setup-steps.yml",
        "ss-reliability-accessibility-check.yml",
        "ss-reliability-broken-links-check.yml",
        "ss-reliability-e2e-check.yml",
        "ss-reliability-smoke-tests.yml",
    ]


def test_playwright_install_is_time_boxed():
    # A stalled browser download once held two PR jobs for hours, because
    # nothing bounded the step short of GitHub's six-hour job limit (#386).
    action = PLAYWRIGHT_ACTION.read_text(encoding="utf-8")
    steps = [s for s in _steps(action) if "playwright install" in s]
    assert len(steps) == 1, "one install step in the action"
    step = steps[0]
    assert "timeout " in step, "each download attempt is bounded with `timeout`"
    # `timeout` kills npx but not the apt-get it spawned, which keeps the
    # dpkg lock, so the retry fails on the lock instead of downloading
    # (#527). apt runs once, un-timed; only the browser download retries.
    assert "--with-deps" not in step, "run `playwright install-deps` outside the timed loop, not `--with-deps` inside it"
    # apt gets one un-timed retry of its own: a transient mirror error
    # exits cleanly and leaves no lock, so a second try is safe.
    assert re.search(
        r'(?m)^\s+npx playwright install-deps "\$BROWSER" \|\| npx playwright install-deps "\$BROWSER"\s*$', step
    ), "the install step has no un-timed `install-deps || install-deps` line"


def test_playwright_browsers_are_cached_before_the_install():
    # A warm run never touches the download CDN (#536): the browser directory
    # is cached on the Playwright version resolved from node_modules, so a
    # lockfile bump misses and a repeat on the same version is a no-op.
    action = PLAYWRIGHT_ACTION.read_text(encoding="utf-8")
    names = re.findall(r"^\s+- name: (.+)$", action, re.M)
    cache = next(i for i, n in enumerate(names) if n.startswith("Cache Playwright"))
    install = next(i for i, n in enumerate(names) if n.startswith("Install Playwright"))
    assert cache < install, names
    cache_step = [s for s in _steps(action) if "actions/cache@" in s][0]
    assert "path: ~/.cache/ms-playwright" in cache_step
    assert "steps.pw.outputs.version" in cache_step, "the key carries the resolved Playwright version"
    assert "restore-keys" not in cache_step, "a partial match would mask a lockfile bump"
    assert "npx --no-install playwright --version" in action, "the version comes from node_modules, never the registry"
    assert "${{ runner.arch }}" in action, "one cache per architecture, or an x64 Chromium is restored on arm"


@pytest.mark.parametrize("workflow", ALL_WORKFLOWS)
def test_no_workflow_inlines_the_playwright_install(workflow):
    assert "playwright install" not in _text(workflow), (
        f"{workflow} inlines `playwright install`, but that step lives in .github/actions/ss-playwright"
    )


@pytest.mark.parametrize("workflow", PLAYWRIGHT_CALLERS)
def test_playwright_caller_bounds_the_step_and_follows_npm_ci(workflow):
    """Composite steps cannot carry `timeout-minutes`, so the calling step
    does; and the action reads the Playwright version from node_modules, so
    `npm ci` has to come first."""
    text = _text(workflow)
    for step in _steps(text):
        if "uses: ./.github/actions/ss-playwright" not in step:
            continue
        assert re.search(r"(?m)^\s+timeout-minutes:\s*\d+", step), (
            f"{workflow}: the ss-playwright step has no `timeout-minutes`"
        )
    for job in re.split(r"(?m)^  [A-Za-z0-9_-]+:\n", text)[1:]:
        if "uses: ./.github/actions/ss-playwright" not in job:
            continue
        # The step itself, not a comment that mentions it.
        npm_ci = re.search(r"(?m)^\s+(?:- )?run: npm ci\s*$", job)
        assert npm_ci, f"{workflow}: no `run: npm ci` step in the job that calls ss-playwright"
        assert npm_ci.start() < job.index("uses: ./.github/actions/ss-playwright"), (
            f"{workflow}: ss-playwright runs before `npm ci`"
        )


# ── the doc updater ships to adopters (#411) ─────────────────────
#
# Its prompt is runtime-imported from the adopter's own copy of the .md,
# so anything slopstopper-specific in it would steer an agent to edit a
# project that isn't there. Project context comes from the adopter's
# AGENTS.md and docs map instead.

DOC_UPDATER = REPO_ROOT / ".github" / "workflows" / "ss-hygiene-doc-updater.md"
DOC_UPDATER_LOCK = DOC_UPDATER.with_suffix(".lock.yml")
SLOPSTOPPER_ONLY = ("app/", "worker/", "Cloudflare", "wrangler", "slopstopper.dev", "task decisions:new")


@pytest.mark.parametrize("path", [DOC_UPDATER, DOC_UPDATER_LOCK], ids=lambda p: p.name)
def test_the_doc_updater_names_nothing_slopstopper_only(path):
    text = path.read_text()
    assert not [term for term in SLOPSTOPPER_ONLY if term in text]


def test_the_doc_updater_learns_the_project_from_the_repo():
    body = DOC_UPDATER.read_text().split("\n---\n", 1)[1]
    assert "cat AGENTS.md" in body and "cat docs/README.md" in body
    assert "{{#runtime-import .github/workflows/ss-hygiene-doc-updater.md}}" in DOC_UPDATER_LOCK.read_text()


# ── what a dispatched run may report (#425) ──────────────────────
#
# ss-cloudflare-deployed.yml dispatches the URL-driven checks on the
# deployed branch: a preview on its PR branch, the live site on main. A
# per-check issue means production is broken, so it opens and closes only
# for a non-PR run on main; a preview's result stays on its commit.

def _dispatched_by_cloudflare() -> set[str]:
    text = _text("ss-cloudflare-deployed.yml")
    return set(re.findall(r"(ss-[a-z0-9-]+\.yml)", text[text.index("checks=("):]))


def _issue_step_conditions(text: str) -> list[str]:
    """The `if:` text of every step that runs `slopstopper emit … --target issue`."""
    steps = re.split(r"\n      - ", text)
    return [step.split("if:", 1)[1].split("run:", 1)[0] for step in steps
            if "--target issue" in step and "if:" in step]


# One rule for every check that raises its own issue, dispatched or not: a
# branch dispatch never opens the main issue, and a dispatch on main
# opens or closes it like a push does.
@pytest.mark.parametrize("workflow", [w for w in WORKFLOWS if re.search(r"run: slopstopper emit \S+ --target issue", _text(w))])
def test_per_check_issues_come_only_from_non_pr_runs_on_main(workflow):
    conditions = _issue_step_conditions(_text(workflow))
    assert conditions, workflow
    for cond in conditions:
        assert "github.event_name != 'pull_request'" in cond and "github.ref == 'refs/heads/main'" in cond, (workflow, cond)


def test_the_csp_build_step_reads_both_header_keys_without_swallowing_a_cli_failure():
    """`format: auto` picks the meta adapter for a built HTML root, which only
    exists after a build, so the step must look at the source too; and a
    `$(…)` inside `[ ]` would hide a broken CLI."""
    text = _text("ss-hygiene-csp-exceptions-check.yml")
    step = text[text.index("- name: Build the site"):text.index("- name: Run CSP exceptions check")]
    assert 'format="$(slopstopper config get headers.format)"' in step
    assert 'source="$(slopstopper config get headers.source)"' in step
    assert '[ "$(slopstopper' not in step


def test_the_cloudflare_trigger_dispatches_only_workflows_that_take_a_url():
    text = _text("ss-cloudflare-deployed.yml")
    block = text[text.index("checks=(") : text.index(")", text.index("checks=("))]
    dispatched = set(re.findall(r"(ss-[a-z0-9-]+\.yml)", text[text.index("checks=("):]))
    assert "ss-security-dast-check.yml" in dispatched and "ss-security-dast-check.yml" not in block
    for workflow in dispatched:
        assert re.search(r"workflow_dispatch:\n\s+inputs:\n\s+url:", _text(workflow)), workflow


def test_the_cloudflare_trigger_skips_workflows_the_repo_disables():
    text = _text("ss-cloudflare-deployed.yml")
    loop = text[text.index('for wf in "${checks[@]}"'):]
    assert "slopstopper profile disabled" in text
    assert loop.index("grep -Fxq") < loop.index("gh workflow run")


def test_every_url_driven_check_is_dispatched_after_a_cloudflare_deploy():
    """CHANGE_MAP: a check that takes a `url` on dispatch belongs in the
    trigger's list, or Cloudflare repos never run it against a deploy."""
    url_driven = {
        w for w in WORKFLOWS
        if w not in {"ss-cloudflare-deployed.yml"}
        and re.search(r"workflow_dispatch:\n\s+inputs:\n\s+url:", _text(w))
    }
    assert url_driven <= _dispatched_by_cloudflare(), sorted(url_driven - _dispatched_by_cloudflare())


# ── everything the suite raises carries the `slopstopper` label (#526) ──
#
# `slopstopper emit --target issue` already labels its issues; the two
# workflows that open issues or PRs without going through emit must too,
# so `gh issue list --label slopstopper` finds all of the suite's output.


def test_the_failure_tracker_labels_its_issues_slopstopper():
    text = _text("ss-workflow-failure-issue.yml")
    assert "labels: [label, 'slopstopper']" in text
    # A pre-existing issue is relabelled on its next failure, not left behind.
    assert "issues.addLabels" in text and "labels: ['slopstopper']" in text


def test_the_doc_updater_labels_its_prs_slopstopper():
    frontmatter = DOC_UPDATER.read_text().split("\n---\n", 1)[0]
    labels = re.search(r"^\s+labels: \[([^\]]*)\]", frontmatter, re.M)
    assert labels and "slopstopper" in [l.strip() for l in labels.group(1).split(",")]
    # The lock is what runs; it must have been recompiled from the .md.
    assert '"labels":["documentation","automation","slopstopper"]' in DOC_UPDATER_LOCK.read_text()
