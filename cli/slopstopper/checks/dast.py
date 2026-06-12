"""Dynamic Application Security Testing (OWASP ZAP baseline scan).

Ports the bash security:dast flow:

  task dast:check-tool          (verifies Docker is on PATH)
  + docker run --rm
        -v $PWD/.ss/reports/dast:/zap/wrk/:rw
        [-v $PWD/.zap:/zap/wrk/.zap:ro]
        ghcr.io/zaproxy/zaproxy:stable
        zap-baseline.py -t <TARGET> -J dast-report.json -I
        [-c .zap/rules.tsv]
  + python3 .ss/scripts/generate-dast-md.py

into one self-contained check. The only check today that takes a CLI
arg (`--target URL`); plumbed through `slopstopper run security:dast
-- --target https://example.com`.

ZAP is Apache-2.0. Subprocess-invokes `docker` to run the official
ZAP image — slopstopper-cli wheel ships zero ZAP code.

Exit codes:
  0 — analysis completed (gating happens at the workflow level)
  1 — Docker is not installed, or nothing listening on a localhost target
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

REPORT_DIR = Path(".ss/reports/dast")
REPORT_JSON = REPORT_DIR / "dast-report.json"
REPORT_MD = REPORT_DIR / "dast-report.md"

DEFAULT_TARGET = "http://localhost:8080"

RISK_LABELS = {
    "3": "High",
    "2": "Medium",
    "1": "Low",
    "0": "Informational",
}


def _parse_args(args: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="slopstopper run security:dast", add_help=False)
    p.add_argument("--target", default=DEFAULT_TARGET)
    p.add_argument("--help", "-h", action="help")
    return p.parse_args(args or [])


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _target_is_localhost(target: str) -> bool:
    return "localhost" in target or target.startswith("http://127.0.0.1")


def _localhost_responding(url: str = "http://localhost:8080") -> bool:
    try:
        subprocess.run(
            ["curl", "-sf", url],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _start_local_server() -> subprocess.Popen | None:
    if not Path("server.js").exists():
        return None
    proc = subprocess.Popen(
        ["node", "server.js"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        if _localhost_responding():
            print("✅ Server is ready")
            return proc
        time.sleep(1)
    proc.terminate()
    print("❌ Server failed to start within 30 seconds")
    return None


def _docker_host_target(target: str) -> str:
    """Translate a localhost URL to one routable from inside the ZAP container.

    Linux Docker uses the bridge gateway 172.17.0.1; Docker Desktop on
    macOS (and Windows) routes via the magic host.docker.internal name.
    """
    if platform.system() == "Darwin":
        host = "host.docker.internal"
    else:
        host = "172.17.0.1"
    m = re.match(r"https?://[^:/]+:?(\d+)?", target)
    port = (m.group(1) if m else None) or "8080"
    return f"http://{host}:{port}"


def _run_zap(target: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(REPORT_DIR, 0o777)
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{Path.cwd() / REPORT_DIR}:/zap/wrk/:rw",
    ]
    rules_path = Path(".zap/rules.tsv")
    if rules_path.exists():
        cmd += ["-v", f"{Path.cwd() / '.zap'}:/zap/wrk/.zap:ro"]
    cmd += [
        "ghcr.io/zaproxy/zaproxy:stable",
        "zap-baseline.py",
        "-t", target,
        "-J", "dast-report.json",
        "-I",
    ]
    if rules_path.exists():
        cmd += ["-c", ".zap/rules.tsv"]
    subprocess.run(cmd, check=False)


def _read_data() -> dict:
    if not REPORT_JSON.exists():
        return {}
    try:
        return json.loads(REPORT_JSON.read_text())
    except json.JSONDecodeError:
        return {}


def _collect_alerts(data: dict) -> dict[str, list[dict]]:
    alerts_by_risk: dict[str, list[dict]] = {"3": [], "2": [], "1": [], "0": []}
    for site in data.get("site", []):
        for alert in site.get("alerts", []):
            riskcode = str(alert.get("riskcode", "0"))
            entry = {
                "name": alert.get("name", alert.get("alert", "unknown")),
                "riskcode": riskcode,
                "confidence": alert.get("confidence", "?"),
                "desc": alert.get("desc", "").replace("\n", " ").strip(),
                "instances": len(alert.get("instances", [])),
                "solution": alert.get("solution", "").replace("\n", " ").strip(),
            }
            bucket = alerts_by_risk.get(riskcode, alerts_by_risk["0"])
            bucket.append(entry)
    return alerts_by_risk


def _format_alert_row(alert: dict) -> str:
    name = alert["name"]
    risk = RISK_LABELS.get(alert["riskcode"], "Unknown")
    instances = alert["instances"]
    desc = (alert["desc"][:77] + "...") if len(alert["desc"]) > 80 else alert["desc"]
    return f"| {name} | {risk} | {instances} | {desc} |"


def _format_alert_section(alerts: list[dict], section_title: str, icon: str) -> str:
    if not alerts:
        return ""
    out = f"## {icon} {section_title}\n\n"
    out += "| Alert | Risk | Instances | Description |\n"
    out += "|-------|------|-----------|-------------|\n"
    for alert in alerts:
        out += _format_alert_row(alert) + "\n"
    out += "\n"
    return out


def _generated_at() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _build_md_report(data: dict) -> str:
    alerts = _collect_alerts(data)
    high, medium, low, info = alerts["3"], alerts["2"], alerts["1"], alerts["0"]
    total = sum(len(v) for v in alerts.values())

    md = "# DAST Analysis Report\n\n"
    md += f"**Generated**: {_generated_at()}\n\n"
    md += "## Summary\n\n"

    if total == 0:
        md += "## ✅ DAST Status\n\nNo alerts detected.\n\n"
    else:
        md += "| Risk Level | Count |\n"
        md += "|------------|-------|\n"
        md += f"| 🔴 High | {len(high)} |\n"
        md += f"| 🟡 Medium | {len(medium)} |\n"
        md += f"| 🔵 Low | {len(low)} |\n"
        md += f"| ℹ️ Informational | {len(info)} |\n"
        md += f"| **Total** | **{total}** |\n\n"
        md += _format_alert_section(high, "High Risk Alerts", "🔴")
        md += _format_alert_section(medium, "Medium Risk Alerts", "🟡")
        md += _format_alert_section(low, "Low Risk Alerts", "🔵")
        md += _format_alert_section(info, "Informational Alerts", "ℹ️")

    md += "## Guidelines\n\n"
    md += "- **High**: Must be addressed before merging\n"
    md += "- **Medium**: Should be reviewed and addressed\n"
    md += "- **Low**: Informational — review when time allows\n"
    md += "- Run `task dast -- <url>` locally to reproduce\n\n"
    md += "## More Information\n\n"
    md += "- Generated by [OWASP ZAP](https://www.zaproxy.org/)\n"
    md += "- Reports location: `.ss/reports/dast/`\n"
    md += "  - `dast-report.md` (this file)\n"
    md += "  - `dast-report.json` (machine-readable)\n"
    return md


def run(args: list[str] | None = None) -> int:
    if not _docker_available():
        print("❌ Docker is required to run OWASP ZAP")
        print("Please install Docker: https://docs.docker.com/get-docker/")
        return 1

    parsed = _parse_args(args)
    target = parsed.target

    print(f"🌐 Running DAST analysis against {target}…")

    server_proc: subprocess.Popen | None = None
    try:
        if _target_is_localhost(target):
            if not _localhost_responding():
                server_proc = _start_local_server()
                if server_proc is None and not _localhost_responding():
                    print(f"❌ Nothing listening on {target} and no server.js to start.")
                    print("   Start your app's server first, then re-run.")
                    return 1
            target = _docker_host_target(target)
            print(f"📍 Using Docker-compatible target: {target}")

        _run_zap(target)
        data = _read_data()
        REPORT_MD.write_text(_build_md_report(data))

        alerts = _collect_alerts(data)
        blocking = len(alerts["3"]) + len(alerts["2"])
        total = sum(len(v) for v in alerts.values())
        if blocking > 0:
            print(f"⚠️  Found {blocking} high/medium alert(s) (total {total})")
        elif total > 0:
            print(f"ℹ️  Found {total} alert(s) — none high/medium")
        else:
            print("✅ No alerts detected")
        print(f"📁 Reports saved to: {REPORT_DIR}/")
        return 0
    finally:
        if server_proc is not None:
            server_proc.terminate()
