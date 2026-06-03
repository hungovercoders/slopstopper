"""Tests for the SAST report generation script."""

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
    os.makedirs(".ss/reports/sast", exist_ok=True)
    return tmpdir


def teardown_test_env(tmpdir):
    """Clean up temporary test directory."""
    os.chdir("/")
    shutil.rmtree(tmpdir, ignore_errors=True)


SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    ".scripts",
    "generate-sast-md.py",
)


def run_script(cwd):
    return subprocess.run(
        ["python3", SCRIPT_PATH],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def write_json(tmpdir, data):
    with open(os.path.join(tmpdir, ".ss/reports/sast", "sast-report.json"), "w") as f:
        json.dump(data, f)


def test_missing_json_fails():
    """Test that script fails when JSON report is missing."""
    tmpdir = setup_test_env()
    try:
        result = run_script(tmpdir)

        assert result.returncode != 0, "Script should fail when JSON is missing"
        assert "not found" in result.stderr, "Should report missing JSON"
        assert not os.path.exists(
            os.path.join(tmpdir, ".ss/reports/sast", "sast-report.md")
        ), "Should not generate report on error"

        print("✅ test_missing_json_fails passed")
    finally:
        teardown_test_env(tmpdir)


def test_generates_report_with_no_findings():
    """Test that script generates markdown report when there are no findings."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {"results": [], "errors": []})

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"
        report_path = os.path.join(tmpdir, ".ss/reports/sast", "sast-report.md")
        assert os.path.exists(report_path), "Should generate markdown report"

        with open(report_path) as f:
            content = f.read()

        assert "SAST Analysis Report" in content, "Should have title"
        assert "No findings detected" in content, "Should indicate clean status"

        print("✅ test_generates_report_with_no_findings passed")
    finally:
        teardown_test_env(tmpdir)


def test_identifies_error_findings():
    """Test that script identifies ERROR-severity findings."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {
            "results": [
                {
                    "check_id": "python.lang.security.dangerous-exec",
                    "path": "app.py",
                    "start": {"line": 10},
                    "end": {"line": 10},
                    "extra": {
                        "message": "Dangerous use of exec()",
                        "severity": "ERROR",
                    },
                },
                {
                    "check_id": "python.lang.best-practice.useless-eqeq",
                    "path": "app.py",
                    "start": {"line": 20},
                    "end": {"line": 20},
                    "extra": {
                        "message": "Useless equality check",
                        "severity": "WARNING",
                    },
                },
            ],
            "errors": [],
        })

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(os.path.join(tmpdir, ".ss/reports/sast", "sast-report.md")) as f:
            content = f.read()

        assert "Error Findings" in content, "Should have error findings section"
        assert "Warning Findings" in content, "Should have warning findings section"
        assert "python.lang.security.dangerous-exec" in content, "Should list error rule"
        assert "python.lang.best-practice.useless-eqeq" in content, "Should list warning rule"
        assert "Total findings" in content, "Should show summary counts"

        print("✅ test_identifies_error_findings passed")
    finally:
        teardown_test_env(tmpdir)


def test_report_includes_guidelines():
    """Test that report includes guidelines section."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {"results": [], "errors": []})

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(os.path.join(tmpdir, ".ss/reports/sast", "sast-report.md")) as f:
            content = f.read()

        assert "Guidelines" in content, "Should include guidelines"
        assert "Semgrep" in content, "Should mention Semgrep"
        assert "sast-report.json" in content, "Should reference JSON report"

        print("✅ test_report_includes_guidelines passed")
    finally:
        teardown_test_env(tmpdir)


def test_scan_errors_shown_in_report():
    """Test that Semgrep scan errors are surfaced in the report."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {
            "results": [],
            "errors": [{"message": "Parse error in file.py", "type": "ParseError"}],
        })

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(os.path.join(tmpdir, ".ss/reports/sast", "sast-report.md")) as f:
            content = f.read()

        assert "scan error(s)" in content, "Should mention scan errors"

        print("✅ test_scan_errors_shown_in_report passed")
    finally:
        teardown_test_env(tmpdir)


if __name__ == "__main__":
    print("\n🧪 Running SAST script tests...\n")

    try:
        test_missing_json_fails()
        test_generates_report_with_no_findings()
        test_identifies_error_findings()
        test_report_includes_guidelines()
        test_scan_errors_shown_in_report()

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
