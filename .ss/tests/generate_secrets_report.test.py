"""Tests for the secrets detection report generation script."""

import json
import os
import shutil
import subprocess
import sys
import tempfile


def setup_test_env():
    """Create a temporary directory for test files."""
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)
    os.makedirs(".ss/reports/secrets", exist_ok=True)
    return tmpdir


def teardown_test_env(tmpdir):
    """Clean up temporary test directory."""
    os.chdir("/")
    shutil.rmtree(tmpdir, ignore_errors=True)


SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    ".scripts",
    "generate-secrets-md.py",
)


def run_script(cwd):
    return subprocess.run(
        ["python3", SCRIPT_PATH],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def write_json(tmpdir, data):
    path = os.path.join(tmpdir, ".ss/reports/secrets", "secrets-report.json")
    with open(path, "w") as f:
        if data is None:
            f.write("null")
        else:
            json.dump(data, f)


def test_missing_json_fails():
    """Test that script fails when JSON report is missing."""
    tmpdir = setup_test_env()
    try:
        result = run_script(tmpdir)

        assert result.returncode != 0, "Script should fail when JSON is missing"
        assert "not found" in result.stderr, "Should report missing JSON"
        assert not os.path.exists(
            os.path.join(tmpdir, ".ss/reports/secrets", "secrets-report.md")
        ), "Should not generate report on error"

        print("✅ test_missing_json_fails passed")
    finally:
        teardown_test_env(tmpdir)


def test_generates_report_with_null_output():
    """Test that script handles Gitleaks 'null' output (no findings)."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, None)  # Gitleaks writes null when clean

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"
        report_path = os.path.join(tmpdir, ".ss/reports/secrets", "secrets-report.md")
        assert os.path.exists(report_path), "Should generate markdown report"

        with open(report_path) as f:
            content = f.read()

        assert "Secrets Detection Report" in content, "Should have title"
        assert "No secrets detected" in content, "Should indicate clean status"

        print("✅ test_generates_report_with_null_output passed")
    finally:
        teardown_test_env(tmpdir)


def test_generates_report_with_empty_list():
    """Test that script handles empty findings list."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, [])

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(os.path.join(tmpdir, ".ss/reports/secrets", "secrets-report.md")) as f:
            content = f.read()

        assert "No secrets detected" in content, "Should indicate clean status"

        print("✅ test_generates_report_with_empty_list passed")
    finally:
        teardown_test_env(tmpdir)


def test_identifies_secrets():
    """Test that script identifies detected secrets."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, [
            {
                "RuleID": "aws-access-token",
                "Description": "AWS Access Token",
                "File": "config.py",
                "StartLine": 12,
                "Commit": "abc123def456",
                "Secret": "AKIAIOSFODNN7EXAMPLE",
            },
            {
                "RuleID": "github-pat",
                "Description": "GitHub Personal Access Token",
                "File": ".env",
                "StartLine": 3,
                "Commit": "",
                "Secret": "ghp_xxxxxxxxxxxxxxxxxxxx",
            },
        ])

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(os.path.join(tmpdir, ".ss/reports/secrets", "secrets-report.md")) as f:
            content = f.read()

        assert "aws-access-token" in content, "Should list AWS token rule"
        assert "github-pat" in content, "Should list GitHub PAT rule"
        assert "config.py" in content, "Should show file location"
        assert "2 secret(s) detected" in content, "Should show count"

        print("✅ test_identifies_secrets passed")
    finally:
        teardown_test_env(tmpdir)


def test_report_includes_guidelines():
    """Test that report includes guidelines section."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, [])

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(os.path.join(tmpdir, ".ss/reports/secrets", "secrets-report.md")) as f:
            content = f.read()

        assert "Guidelines" in content, "Should include guidelines"
        assert "Gitleaks" in content, "Should mention Gitleaks"
        assert "secrets-report.json" in content, "Should reference JSON report"

        print("✅ test_report_includes_guidelines passed")
    finally:
        teardown_test_env(tmpdir)


if __name__ == "__main__":
    print("\n🧪 Running secrets detection script tests...\n")

    try:
        test_missing_json_fails()
        test_generates_report_with_null_output()
        test_generates_report_with_empty_list()
        test_identifies_secrets()
        test_report_includes_guidelines()

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
