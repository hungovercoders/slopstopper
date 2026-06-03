"""Tests for the dependency vulnerability report generation script."""

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
    os.makedirs(".ss/reports/dependencies", exist_ok=True)
    return tmpdir


def teardown_test_env(tmpdir):
    """Clean up temporary test directory."""
    os.chdir("/")
    shutil.rmtree(tmpdir, ignore_errors=True)


SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    ".scripts",
    "generate-dependencies-md.py",
)


def run_script(cwd):
    return subprocess.run(
        ["python3", SCRIPT_PATH],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def write_json(tmpdir, data):
    with open(
        os.path.join(tmpdir, ".ss/reports/dependencies", "dependencies-report.json"), "w"
    ) as f:
        json.dump(data, f)


def test_missing_json_fails():
    """Test that script fails when JSON report is missing."""
    tmpdir = setup_test_env()
    try:
        result = run_script(tmpdir)

        assert result.returncode != 0, "Script should fail when JSON is missing"
        assert "not found" in result.stderr, "Should report missing JSON"
        assert not os.path.exists(
            os.path.join(tmpdir, ".ss/reports/dependencies", "dependencies-report.md")
        ), "Should not generate report on error"

        print("✅ test_missing_json_fails passed")
    finally:
        teardown_test_env(tmpdir)


def test_generates_report_with_no_vulnerabilities():
    """Test that script generates markdown report when there are no vulnerabilities."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {"Results": []})

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"
        report_path = os.path.join(
            tmpdir, ".ss/reports/dependencies", "dependencies-report.md"
        )
        assert os.path.exists(report_path), "Should generate markdown report"

        with open(report_path) as f:
            content = f.read()

        assert "Dependency Vulnerability Report" in content, "Should have title"
        assert "No vulnerabilities detected" in content, "Should indicate clean status"

        print("✅ test_generates_report_with_no_vulnerabilities passed")
    finally:
        teardown_test_env(tmpdir)


def test_identifies_critical_and_high_vulns():
    """Test that script identifies CRITICAL and HIGH vulnerabilities."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {
            "Results": [
                {
                    "Target": "package-lock.json",
                    "Type": "npm",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2021-1234",
                            "PkgName": "lodash",
                            "InstalledVersion": "4.17.20",
                            "FixedVersion": "4.17.21",
                            "Severity": "CRITICAL",
                            "Title": "Prototype Pollution in lodash",
                        },
                        {
                            "VulnerabilityID": "CVE-2021-5678",
                            "PkgName": "express",
                            "InstalledVersion": "4.17.0",
                            "FixedVersion": "4.17.3",
                            "Severity": "HIGH",
                            "Title": "Open Redirect in express",
                        },
                        {
                            "VulnerabilityID": "CVE-2021-9999",
                            "PkgName": "debug",
                            "InstalledVersion": "2.6.8",
                            "FixedVersion": "2.6.9",
                            "Severity": "LOW",
                            "Title": "ReDoS in debug",
                        },
                    ],
                }
            ]
        })

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(
            os.path.join(tmpdir, ".ss/reports/dependencies", "dependencies-report.md")
        ) as f:
            content = f.read()

        assert "Critical Vulnerabilities" in content, "Should have critical section"
        assert "High Vulnerabilities" in content, "Should have high section"
        assert "CVE-2021-1234" in content, "Should list critical CVE"
        assert "lodash" in content, "Should show vulnerable package"
        assert "CVE-2021-5678" in content, "Should list high CVE"

        print("✅ test_identifies_critical_and_high_vulns passed")
    finally:
        teardown_test_env(tmpdir)


def test_report_includes_guidelines():
    """Test that report includes guidelines section."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {"Results": []})

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(
            os.path.join(tmpdir, ".ss/reports/dependencies", "dependencies-report.md")
        ) as f:
            content = f.read()

        assert "Guidelines" in content, "Should include guidelines"
        assert "Trivy" in content, "Should mention Trivy"
        assert "dependencies-report.json" in content, "Should reference JSON report"

        print("✅ test_report_includes_guidelines passed")
    finally:
        teardown_test_env(tmpdir)


def test_severity_counts_in_summary():
    """Test that summary table shows correct severity counts."""
    tmpdir = setup_test_env()
    try:
        write_json(tmpdir, {
            "Results": [
                {
                    "Target": "package-lock.json",
                    "Type": "npm",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-A",
                            "PkgName": "pkg-a",
                            "InstalledVersion": "1.0.0",
                            "FixedVersion": "1.0.1",
                            "Severity": "CRITICAL",
                            "Title": "Critical issue",
                        },
                        {
                            "VulnerabilityID": "CVE-B",
                            "PkgName": "pkg-b",
                            "InstalledVersion": "2.0.0",
                            "FixedVersion": "2.0.1",
                            "Severity": "MEDIUM",
                            "Title": "Medium issue",
                        },
                    ],
                }
            ]
        })

        result = run_script(tmpdir)

        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"

        with open(
            os.path.join(tmpdir, ".ss/reports/dependencies", "dependencies-report.md")
        ) as f:
            content = f.read()

        assert "Critical" in content, "Should show Critical in summary"
        assert "Medium" in content, "Should show Medium in summary"

        print("✅ test_severity_counts_in_summary passed")
    finally:
        teardown_test_env(tmpdir)


if __name__ == "__main__":
    print("\n🧪 Running dependency vulnerability script tests...\n")

    try:
        test_missing_json_fails()
        test_generates_report_with_no_vulnerabilities()
        test_identifies_critical_and_high_vulns()
        test_report_includes_guidelines()
        test_severity_counts_in_summary()

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
