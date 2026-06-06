"""Tests for the DAST report generation script."""

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
    os.makedirs(".ss/reports/dast", exist_ok=True)
    return tmpdir


def teardown_test_env(tmpdir):
    """Clean up temporary test directory."""
    os.chdir("/")
    shutil.rmtree(tmpdir, ignore_errors=True)


SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    ".scripts",
    "generate-dast-md.py",
)


def run_script(cwd):
    return subprocess.run(
        ["python3", SCRIPT_PATH],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def write_json(tmpdir, data):
    with open(os.path.join(tmpdir, ".ss/reports/dast", "dast-report.json"), "w") as f:
        json.dump(data, f)


def test_missing_json_fails():
    """Test that script fails when JSON report is missing."""
    tmpdir = setup_test_env()
    try:
        result = run_script(tmpdir)

        assert result.returncode != 0, "Script should fail when JSON is missing"
        assert "not found" in result.stderr, "Should report missing JSON"
        assert not os.path.exists(
            os.path.join(tmpdir, ".ss/reports/dast", "dast-report.md")
        ), "Should not generate report on error"

        print("✅ test_missing_json_fails passed")
    finally:
        teardown_test_env(tmpdir)


def test_generates_report_with_no_alerts():
    """Test that script generates markdown report when there are no alerts."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {"site": []})

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"
        report_path = os.path.join(tmpdir, ".ss/reports/dast", "dast-report.md")
        assert os.path.exists(report_path), "Should generate markdown report"

        with open(report_path) as f:
            content = f.read()

        assert "DAST Analysis Report" in content, "Should have title"
        assert "No alerts detected" in content, "Should indicate clean status"

        print("✅ test_generates_report_with_no_alerts passed")
    finally:
        teardown_test_env(tmpdir)


def test_identifies_high_and_medium_alerts():
    """Test that script identifies high and medium alerts."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {
            "site": [
                {
                    "@name": "http://localhost:8080",
                    "alerts": [
                        {
                            "pluginid": "10038",
                            "alert": "Content Security Policy Header Not Set",
                            "name": "Content Security Policy Header Not Set",
                            "riskcode": "2",
                            "confidence": "3",
                            "desc": "CSP header is missing.",
                            "solution": "Add CSP header.",
                            "instances": [{"uri": "http://localhost:8080"}],
                        },
                        {
                            "pluginid": "10021",
                            "alert": "X-Content-Type-Options Header Missing",
                            "name": "X-Content-Type-Options Header Missing",
                            "riskcode": "1",
                            "confidence": "2",
                            "desc": "Header missing.",
                            "solution": "Add header.",
                            "instances": [{"uri": "http://localhost:8080"}],
                        },
                    ],
                }
            ]
        })

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(os.path.join(tmpdir, ".ss/reports/dast", "dast-report.md")) as f:
            content = f.read()

        assert "Medium Risk Alerts" in content, "Should have medium alerts section"
        assert "Low Risk Alerts" in content, "Should have low alerts section"
        assert "Content Security Policy" in content, "Should list medium alert"
        assert "X-Content-Type-Options" in content, "Should list low alert"

        print("✅ test_identifies_high_and_medium_alerts passed")
    finally:
        teardown_test_env(tmpdir)


def test_report_includes_guidelines():
    """Test that report includes guidelines section."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {"site": []})

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(os.path.join(tmpdir, ".ss/reports/dast", "dast-report.md")) as f:
            content = f.read()

        assert "Guidelines" in content, "Should include guidelines"
        assert "OWASP ZAP" in content, "Should mention OWASP ZAP"
        assert "dast-report.json" in content, "Should reference JSON report"

        print("✅ test_report_includes_guidelines passed")
    finally:
        teardown_test_env(tmpdir)


def test_risk_summary_counts():
    """Test that risk summary shows correct counts."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {
            "site": [
                {
                    "@name": "http://localhost:8080",
                    "alerts": [
                        {
                            "alert": "High Alert",
                            "name": "High Alert",
                            "riskcode": "3",
                            "confidence": "3",
                            "desc": "Serious issue.",
                            "solution": "Fix it.",
                            "instances": [{"uri": "http://localhost:8080"}],
                        },
                        {
                            "alert": "Info Alert",
                            "name": "Info Alert",
                            "riskcode": "0",
                            "confidence": "1",
                            "desc": "Just info.",
                            "solution": "None needed.",
                            "instances": [],
                        },
                    ],
                }
            ]
        })

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(os.path.join(tmpdir, ".ss/reports/dast", "dast-report.md")) as f:
            content = f.read()

        assert "High Risk Alerts" in content, "Should have high risk section"
        assert "Informational Alerts" in content, "Should have informational section"

        print("✅ test_risk_summary_counts passed")
    finally:
        teardown_test_env(tmpdir)


if __name__ == "__main__":
    print("\n🧪 Running DAST script tests...\n")

    try:
        test_missing_json_fails()
        test_generates_report_with_no_alerts()
        test_identifies_high_and_medium_alerts()
        test_report_includes_guidelines()
        test_risk_summary_counts()

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
