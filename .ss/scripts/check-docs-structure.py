#!/usr/bin/env python3

"""
Documentation Structure Validator

Validates that the docs directory structure matches the governance
defined in docs/index.md. Generates a JSON report of violations.
"""

import json
import re
import sys
from pathlib import Path


def extract_categories_from_index():
    """Parse docs/index.md to extract expected categories."""
    index_path = Path("docs/index.md")
    if not index_path.exists():
        print("❌ docs/index.md not found")
        sys.exit(1)

    content = index_path.read_text()
    
    # Find the table with categories
    # Pattern: | [category/](category/) | ... |
    pattern = r'\|\s*\[([a-z_]+)/\]\(([a-z_]+)/\)\s*\|'
    matches = re.findall(pattern, content)
    
    categories = [match[0] for match in matches]
    
    return sorted(set(categories))


def _check_expected_categories(docs_path, expected_categories):
    """Check that all expected categories exist with README.md files."""
    violations = []
    for category in expected_categories:
        category_path = docs_path / category
        if not category_path.exists():
            violations.append({
                "type": "missing_directory",
                "path": f"docs/{category}/",
                "message": f"Missing directory: docs/{category}/"
            })
        elif not (category_path / "README.md").exists():
            violations.append({
                "type": "missing_readme",
                "path": f"docs/{category}/README.md",
                "message": f"Missing README.md: docs/{category}/README.md"
            })
    return violations


def _check_unexpected_items(docs_path, expected_categories):
    """Check for unexpected files and directories in docs/."""
    violations = []

    expected_files = {"index.md", "README.md", "AGENTS.md", "CONTRIBUTING.md"}
    actual_files = {f.name for f in docs_path.iterdir() if f.is_file()}
    for filename in sorted(actual_files - expected_files):
        violations.append({
            "type": "unexpected_file",
            "path": f"docs/{filename}",
            "message": f"Unexpected file (not in index): docs/{filename}"
        })

    expected_dirs = set(expected_categories)
    actual_dirs = sorted([d.name for d in docs_path.iterdir() if d.is_dir()])
    for dirname in sorted(set(actual_dirs) - expected_dirs):
        violations.append({
            "type": "unexpected_directory",
            "path": f"docs/{dirname}/",
            "message": f"Unexpected directory (not in index): docs/{dirname}/"
        })

    return violations


def check_docs_structure():
    """Validate docs structure against index.md governance."""
    docs_path = Path("docs")

    if not docs_path.exists():
        print("❌ docs/ directory not found")
        sys.exit(1)

    expected_categories = extract_categories_from_index()
    violations = _check_expected_categories(docs_path, expected_categories)
    violations += _check_unexpected_items(docs_path, expected_categories)
    return violations


def main():
    print("🔍 Validating documentation structure...")
    
    violations = check_docs_structure()
    
    # Create report directory
    Path(".docs-reports").mkdir(exist_ok=True)
    
    # Write JSON report
    report = {
        "violations": violations,
        "valid": len(violations) == 0,
        "violation_count": len(violations)
    }
    
    with open(".docs-reports/docs-structure-report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    if violations:
        print(f"❌ Found {len(violations)} structure violation(s)")
        sys.exit(1)
    else:
        print("✅ Documentation structure is valid")


if __name__ == "__main__":
    main()
