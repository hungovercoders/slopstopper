"""Documentation size monitor.

Ports .ss/scripts/check-docs-size.sh + generate-docs-size-report.py into
one self-contained check. Writes .ss/reports/docs/docs-size-report.md
and prints a coloured summary to stdout. Exits 0 always — alerts are
reported, not enforced.

Configuration (.slopstopper.yml — all keys optional):

    hygiene:
      docs_size:
        max_total_size_kb: 150   # total .md under docs/ (excl. docs/archive/**)
        max_file_size_kb: 20     # largest single doc
        max_files: 25            # total doc count

See .slopstopper.yml.example for the canonical schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from slopstopper import config

DOCS_DIR = Path("docs")
ARCHIVE_PREFIX = Path("docs/archive")
REPORT_DIR = Path(".ss/reports/docs")
REPORT_FILE = REPORT_DIR / "docs-size-report.md"

# Consumed by `slopstopper emit hygiene:docs-size --target {pr-comment,issue}`.
# Strings are byte-for-byte identical to the discriminator / title / labels
# the legacy actions/github-script@v7 block in
# .github/workflows/ss-hygiene-docs-size-check.yml used, so the same bot
# comments/issues are matched after the workflow flip.
META = {
    "report_path": str(REPORT_FILE),
    "comment_discriminator": "📚 Documentation Size Report",
    "issue_title": "📚 Documentation Size Exceeds Thresholds",
    "issue_labels": ["documentation-size", "maintenance"],
    "issue_followup": "🔔 Documentation size thresholds exceeded again in commit",
}

DEFAULT_MAX_TOTAL_SIZE_KB = 150
DEFAULT_MAX_FILE_SIZE_KB = 20
DEFAULT_MAX_FILES = 25

RED = "\033[0;31m"
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
NC = "\033[0m"


def _iter_doc_files(docs_dir: Path = DOCS_DIR) -> list[Path]:
    if not docs_dir.exists():
        return []
    archive = docs_dir / "archive"
    return [p for p in sorted(docs_dir.rglob("*.md")) if archive not in p.parents]


def _config_int(path: str, default: int) -> int:
    raw = config.get(path, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _load_thresholds() -> dict[str, int]:
    return {
        "max_total_size_kb": _config_int("hygiene.docs_size.max_total_size_kb", DEFAULT_MAX_TOTAL_SIZE_KB),
        "max_file_size_kb": _config_int("hygiene.docs_size.max_file_size_kb", DEFAULT_MAX_FILE_SIZE_KB),
        "max_files": _config_int("hygiene.docs_size.max_files", DEFAULT_MAX_FILES),
    }


def _compute_stats(files_with_size: list[tuple[Path, int]]) -> dict[str, int]:
    file_count = len(files_with_size)
    total_size = sum(size for _, size in files_with_size)
    return {
        "file_count": file_count,
        "total_size_bytes": total_size,
        "total_size_kb": total_size // 1024,
        "estimated_tokens": total_size // 4,
        "avg_size_kb": (total_size // file_count // 1024) if file_count else 0,
    }


def _format_largest(files_with_size: list[tuple[Path, int]]) -> str:
    top5 = sorted(files_with_size, key=lambda fs: fs[1], reverse=True)[:5]
    return "\n".join(f"{p} ({size // 1024} KB)" for p, size in top5)


def _compute_alerts(
    stats: dict[str, int],
    files_with_size: list[tuple[Path, int]],
    thresholds: dict[str, int],
) -> list[str]:
    parts: list[str] = []
    if stats["total_size_kb"] > thresholds["max_total_size_kb"]:
        parts.append(
            f"⚠️  Total documentation size ({stats['total_size_kb']} KB) "
            f"exceeds threshold ({thresholds['max_total_size_kb']} KB)"
        )
    if stats["file_count"] > thresholds["max_files"]:
        parts.append(
            f"⚠️  Number of documentation files ({stats['file_count']}) "
            f"exceeds threshold ({thresholds['max_files']})"
        )
    oversized = [p for p, size in files_with_size if size > thresholds["max_file_size_kb"] * 1024]
    if oversized:
        oversized_lines = "\n".join(f"     - {p.name}" for p in oversized)
        parts.append(f"⚠️  Files exceeding {thresholds['max_file_size_kb']} KB:\n{oversized_lines}")
    return parts


def _generated_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _build_report_md(
    *,
    stats: dict[str, int],
    largest_files: str,
    alerts: list[str],
    thresholds: dict[str, int],
    generated_at: str | None = None,
) -> str:
    has_alerts = bool(alerts)
    alerts_str = ("\n".join(alerts) + "\n") if has_alerts else ""
    status_line = (
        "❌ Documentation size exceeds thresholds!"
        if has_alerts
        else "✅ Documentation size within acceptable limits"
    )
    generated = generated_at or _generated_at()

    report = (
        f"# 📚 Documentation Size Report\n"
        f"\n"
        f"**Generated:** {generated}\n"
        f"\n"
        f"## Summary\n"
        f"\n"
        f"- **Total Files:** {stats['file_count']}\n"
        f"- **Total Size:** {stats['total_size_kb']} KB\n"
        f"- **Estimated Tokens:** ~{stats['estimated_tokens']}\n"
        f"- **Average File Size:** {stats['avg_size_kb']} KB\n"
        f"\n"
        f"## Largest Files\n"
        f"\n"
        f"```\n"
        f"{largest_files}\n"
        f"```\n"
        f"\n"
        f"## Status\n"
        f"\n"
        f"{status_line}\n"
        f"\n"
    )
    if has_alerts:
        report += f"### Alerts\n\n{alerts_str}\n"
    report += (
        f"## Thresholds\n"
        f"\n"
        f"- **Max Total Size:** {thresholds['max_total_size_kb']} KB\n"
        f"- **Max File Size:** {thresholds['max_file_size_kb']} KB\n"
        f"- **Max File Count:** {thresholds['max_files']}\n"
        f"\n"
        f"## Recommendations\n"
        f"\n"
        f"If thresholds are exceeded:\n"
        f"- Consider consolidating related documentation\n"
        f"- Move historical/completed content to archive\n"
        f"- Split large files into focused topics\n"
        f"- Remove redundant information\n"
        f"\n"
        f"---\n"
        f"\n"
        f"*This report was generated by the Documentation Size Monitor.*\n"
    )
    return report


def _print_terminal_summary(
    stats: dict[str, int],
    largest_files: str,
    alerts: list[str],
    thresholds: dict[str, int],
) -> None:
    print()
    print("📚 Documentation Size Monitor")
    print("━" * 56)
    print()
    print("📊 Documentation Statistics:")
    print("━" * 56)
    print(f"  Total Files:        {BLUE}{stats['file_count']}{NC}")
    print(f"  Total Size:         {BLUE}{stats['total_size_kb']} KB{NC}")
    print(f"  Estimated Tokens:   {BLUE}~{stats['estimated_tokens']}{NC}")
    print(f"  Average File Size:  {BLUE}{stats['avg_size_kb']} KB{NC}")
    print()
    print("📈 Largest Files:")
    print("━" * 56)
    print(largest_files)
    print()
    print("📋 Threshold Limits:")
    print("━" * 56)
    print(f"  Max Total Size:     {BLUE}{thresholds['max_total_size_kb']} KB{NC}")
    print(f"  Max File Size:      {BLUE}{thresholds['max_file_size_kb']} KB{NC}")
    print(f"  Max File Count:     {BLUE}{thresholds['max_files']}{NC}")
    print()
    if alerts:
        print(f"{RED}❌ Status: THRESHOLDS EXCEEDED{NC}")
        print()
        print("⚠️  Alerts:")
        print("━" * 56)
        print("\n".join(alerts))
    else:
        print(f"{GREEN}✅ Status: Within acceptable limits{NC}")
    print()


def run(_args: list[str] | None = None) -> int:
    thresholds = _load_thresholds()
    files_with_size = [(p, p.stat().st_size) for p in _iter_doc_files()]
    stats = _compute_stats(files_with_size)
    largest_files = _format_largest(files_with_size)
    alerts = _compute_alerts(stats, files_with_size, thresholds)

    _print_terminal_summary(stats, largest_files, alerts, thresholds)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(_build_report_md(
        stats=stats,
        largest_files=largest_files,
        alerts=alerts,
        thresholds=thresholds,
    ))

    print(f"📁 Reports saved to: {REPORT_DIR}/")
    print(f"   • {REPORT_FILE.name} (human-readable)")
    print()
    return 0
