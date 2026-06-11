"""Tests for check-csp-exceptions.py — focused on parser invariants.

The end-to-end drift comparison is exercised by `task ss:hygiene:csp-exceptions`
against slopstopper's own CSP_EXCEPTIONS.md in CI.
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = THIS_DIR.parent / "scripts" / "check-csp-exceptions.py"


def _load_module():
    """Import check-csp-exceptions.py by file path (hyphen in name blocks normal import)."""
    spec = importlib.util.spec_from_file_location("check_csp_exceptions", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT_PATH.parent))
    spec.loader.exec_module(module)
    return module


def _write_doc(text: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
    tmp.write(text)
    tmp.close()
    return Path(tmp.name)


def test_skips_glob_baseline_under_exceptions():
    """`### /*` under `## Exceptions` is the site-wide baseline, not a per-path exception."""
    mod = _load_module()
    doc = _write_doc("""# CSP Exceptions

## Baseline relaxations (site-wide CSP)

Baseline notes here.

## Exceptions

### /*

- **Origin allowed:** none — site-wide baseline only
- **Why:** site-wide CSP baseline; documented for reference, not an exception

### /feedback.html

- **Origin allowed:** https://giscus.app
- **Directives added:** script-src https://giscus.app
- **Loader SRI:** abc123
- **Why:** Giscus comments
- **Approved by:** maintainer
- **Data leaving site:** username, comment
- **Refresh policy:** quarterly
""")
    try:
        entries = mod.parse_exceptions_doc(doc)
        assert "/*" not in entries, "Glob baseline must not be parsed as an exception entry"
        assert "/feedback.html" in entries, "Per-path heading should still be picked up"
        assert "https://giscus.app" in entries["/feedback.html"]["origins"], \
            "Origin should be extracted for valid entries"
        print("✅ test_skips_glob_baseline_under_exceptions passed")
    finally:
        os.unlink(doc)


def test_following_heading_starts_clean_after_skipped_glob():
    """Field lines after a skipped `### /*` must not bleed into the next entry."""
    mod = _load_module()
    doc = _write_doc("""# CSP Exceptions

## Exceptions

### /*

- **Origin allowed:** baseline only
- **Directives added:** script-src https://baseline.example
- **Loader SRI:** TODO

### /real-exception

- **Origin allowed:** https://real.example
- **Directives added:** script-src https://real.example
- **Loader SRI:** sha256-real
- **Why:** real third party
- **Approved by:** maintainer
- **Data leaving site:** nothing
- **Refresh policy:** quarterly
""")
    try:
        entries = mod.parse_exceptions_doc(doc)
        assert "/*" not in entries
        assert entries["/real-exception"]["origins"] == {"https://real.example"}, \
            "Origins from skipped /* block must not leak into next entry"
        assert entries["/real-exception"]["sri"] == "sha256-real", \
            "SRI from skipped /* block must not leak into next entry"
        print("✅ test_following_heading_starts_clean_after_skipped_glob passed")
    finally:
        os.unlink(doc)


def test_glob_outside_exceptions_section_is_irrelevant():
    """`### /*` outside `## Exceptions` (e.g. under a baseline section) is always ignored."""
    mod = _load_module()
    doc = _write_doc("""# CSP Exceptions

## Baseline relaxations (site-wide CSP)

### /*

- **Origin allowed:** site-wide baseline only

## Exceptions

### /feedback.html

- **Origin allowed:** https://giscus.app
""")
    try:
        entries = mod.parse_exceptions_doc(doc)
        assert "/*" not in entries
        assert "/feedback.html" in entries
        print("✅ test_glob_outside_exceptions_section_is_irrelevant passed")
    finally:
        os.unlink(doc)


if __name__ == "__main__":
    print("\n🧪 Running check-csp-exceptions parser tests...\n")
    try:
        test_skips_glob_baseline_under_exceptions()
        test_following_heading_starts_clean_after_skipped_glob()
        test_glob_outside_exceptions_section_is_irrelevant()
        print("\n✅ All tests passed!\n")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
