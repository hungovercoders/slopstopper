"""Tests for check-seo-metatags.py — focused on SEO_OG_IMAGE_BASE rewrite path.

End-to-end fetching is exercised by `task ss:reliability:seo` in CI against
slopstopper.dev / preview URLs. This test pins the URL-rewrite logic
that lets adopters validate pre-deploy previews against production-baked
og:image URLs.
"""

import importlib.util
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = THIS_DIR.parent / "scripts" / "check-seo-metatags.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_seo_metatags", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT_PATH.parent))
    spec.loader.exec_module(module)
    return module


def test_rewrite_origin_swaps_scheme_and_netloc():
    mod = _load_module()
    result = mod.rewrite_origin(
        "https://hungovercoders.com/assets/foo/link.png",
        "http://localhost:8080",
    )
    assert result == "http://localhost:8080/assets/foo/link.png", \
        f"unexpected rewrite: {result}"
    print("✅ test_rewrite_origin_swaps_scheme_and_netloc passed")


def test_rewrite_origin_preserves_query_and_fragment():
    mod = _load_module()
    result = mod.rewrite_origin(
        "https://hungovercoders.com/assets/foo/link.png?v=2#x",
        "http://localhost:8080",
    )
    assert result == "http://localhost:8080/assets/foo/link.png?v=2#x", \
        f"unexpected rewrite: {result}"
    print("✅ test_rewrite_origin_preserves_query_and_fragment passed")


def test_rewrite_origin_handles_port_in_target():
    mod = _load_module()
    result = mod.rewrite_origin(
        "https://hungovercoders.com/og.png",
        "http://127.0.0.1:4321",
    )
    assert result == "http://127.0.0.1:4321/og.png", f"unexpected rewrite: {result}"
    print("✅ test_rewrite_origin_handles_port_in_target passed")


if __name__ == "__main__":
    print("\n🧪 Running check-seo-metatags tests...\n")
    try:
        test_rewrite_origin_swaps_scheme_and_netloc()
        test_rewrite_origin_preserves_query_and_fragment()
        test_rewrite_origin_handles_port_in_target()
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
