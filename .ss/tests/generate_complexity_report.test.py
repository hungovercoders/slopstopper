"""Tests for the complexity report generation script."""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path


def setup_test_env():
    """Create a temporary directory for test files."""
    # Create temp dir
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)
    os.makedirs(".ss/reports/complexity", exist_ok=True)
    return tmpdir


def teardown_test_env(tmpdir):
    """Clean up temporary test directory."""
    os.chdir("/")
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_missing_csv_fails():
    """Test that script fails when CSV report is missing."""
    tmpdir = setup_test_env()
    try:
        # Create raw report but no CSV
        with open(".ss/reports/complexity/complexity-report-raw.txt", "w") as f:
            f.write("Total nloc  = 100\n")
        
        result = subprocess.run(
            ["python3", "/workspaces/slopstopper/.ss/scripts/generate-complexity-md.py"],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )
        
        assert result.returncode != 0, "Script should fail when CSV is missing"
        assert "CSV report not found" in result.stderr, "Should report missing CSV"
        assert not os.path.exists(".ss/reports/complexity/complexity-report.md"), \
            "Should not generate report on error"
        
        print("✅ test_missing_csv_fails passed")
    finally:
        teardown_test_env(tmpdir)


def test_missing_raw_report_fails():
    """Test that script fails when raw report is missing."""
    tmpdir = setup_test_env()
    try:
        # Create CSV but no raw report
        with open(".ss/reports/complexity/complexity-report.csv", "w") as f:
            f.write("NLOC,CCN,Tokens,Params,Length,Location\n")
            f.write("10,5,50,2,10,test.py:function_a\n")
        
        result = subprocess.run(
            ["python3", "/workspaces/slopstopper/.ss/scripts/generate-complexity-md.py"],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )
        
        assert result.returncode != 0, "Script should fail when raw report is missing"
        assert "Raw report not found" in result.stderr, "Should report missing raw report"
        
        print("✅ test_missing_raw_report_fails passed")
    finally:
        teardown_test_env(tmpdir)


def test_generates_report_with_valid_input():
    """Test that script generates markdown report with valid input."""
    tmpdir = setup_test_env()
    try:
        # Create valid input files
        with open(".ss/reports/complexity/complexity-report.csv", "w") as f:
            f.write("NLOC,CCN,Tokens,Params,Length,Location\n")
            f.write("10,5,50,2,10,test.py:function_a\n")
            f.write("15,8,75,3,15,test.py:function_b\n")
        
        with open(".ss/reports/complexity/complexity-report-raw.txt", "w") as f:
            f.write("Total nloc  = 100\n")
            f.write("Altogether 2 files are analyzed.\n")
            f.write("TOTAL     2 (avg: 1) \t2 (avg: 1) \tNo thresholds exceeded.\n")
        
        result = subprocess.run(
            ["python3", "/workspaces/slopstopper/.ss/scripts/generate-complexity-md.py"],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )
        
        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"
        assert os.path.exists(".ss/reports/complexity/complexity-report.md"), \
            "Should generate markdown report"
        
        with open(".ss/reports/complexity/complexity-report.md", "r") as f:
            content = f.read()
        
        assert "Code Complexity Analysis Report" in content, "Should have title"
        assert "✅ Complexity Status" in content, "Should show status when no high complexity"
        assert "No high-complexity items found" in content, "Should indicate clean status"
        
        print("✅ test_generates_report_with_valid_input passed")
    finally:
        teardown_test_env(tmpdir)


def test_identifies_high_complexity_items():
    """Test that script identifies high complexity items (CCN > 10)."""
    tmpdir = setup_test_env()
    try:
        # Create input with high complexity item
        with open(".ss/reports/complexity/complexity-report.csv", "w") as f:
            f.write("NLOC,CCN,Tokens,Params,Length,Location\n")
            f.write("10,5,50,2,10,code.py:simple_func\n")
            f.write("50,15,200,5,50,code.py:complex_func\n")
            f.write("20,8,100,3,20,code.py:medium_func\n")
        
        with open(".ss/reports/complexity/complexity-report-raw.txt", "w") as f:
            f.write("Total nloc  = 100\n")
            f.write("Altogether 3 files are analyzed.\n")
            f.write("TOTAL     3 (avg: 1) \t3 (avg: 1) \tNo thresholds exceeded.\n")
        
        result = subprocess.run(
            ["python3", "/workspaces/slopstopper/.ss/scripts/generate-complexity-md.py"],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )
        
        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"
        
        with open(".ss/reports/complexity/complexity-report.md", "r") as f:
            content = f.read()
        
        assert "High Complexity Items (CCN > 10)" in content, \
            "Should identify high complexity section"
        assert "code.py:complex_func" in content, "Should list high complexity function"
        assert "15" in content, "Should show CCN value"
        assert "simple_func" not in content, "Should not list low complexity functions"
        
        print("✅ test_identifies_high_complexity_items passed")
    finally:
        teardown_test_env(tmpdir)


def test_report_includes_guidelines():
    """Test that report includes guidelines."""
    tmpdir = setup_test_env()
    try:
        # Create valid minimal input
        with open(".ss/reports/complexity/complexity-report.csv", "w") as f:
            f.write("NLOC,CCN,Tokens,Params,Length,Location\n")
        
        with open(".ss/reports/complexity/complexity-report-raw.txt", "w") as f:
            f.write("Total nloc  = 0\n")
            f.write("Altogether 0 files are analyzed.\n")
        
        result = subprocess.run(
            ["python3", "/workspaces/slopstopper/.ss/scripts/generate-complexity-md.py"],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )
        
        assert result.returncode == 0, f"Script should succeed. stderr: {result.stderr}"
        
        with open(".ss/reports/complexity/complexity-report.md", "r") as f:
            content = f.read()
        
        assert "Guidelines" in content, "Should include guidelines"
        assert "Cyclomatic Complexity (CCN)" in content, "Should explain CCN"
        assert "Function Length (NLOC)" in content, "Should explain NLOC"
        assert "Generated by [Lizard]" in content, "Should credit Lizard"
        
        print("✅ test_report_includes_guidelines passed")
    finally:
        teardown_test_env(tmpdir)


if __name__ == "__main__":
    print("\n🧪 Running complexity script tests...\n")
    
    try:
        test_missing_csv_fails()
        test_missing_raw_report_fails()
        test_generates_report_with_valid_input()
        test_identifies_high_complexity_items()
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
