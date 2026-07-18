"""Stage 2 cleanup test runner (Req 6).

Runs three bounded pytest commands and saves RAW stdout+stderr along with
structured JSON metadata.

Targeted: the six checks that justified entries moved to "passed" in Stage 2.
Wave:     the prior bounded Stage 2 wave command.
Phase:    the prior bounded phase command.

Each run produces:
- test-runs/<scope>-tests.txt  (full raw output + envelope metadata)
- test-runs/<scope>-tests.json (parsed counts + envelope metadata)

No output is summarized or replaced. Failures are NOT fixed here.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = DOCS = ROOT / "docs" / "grace-reports" / "stage2-verification-20260718"
RUN_DIR = REPORT_DIR / "test-runs"

PYTHON_VERSION = sys.version.replace("\n", " ")
try:
    PYTEST_VERSION = (
        subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        .stdout.splitlines()[0]
        .strip()
    )
except Exception:
    PYTEST_VERSION = "unknown"


def git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except Exception:
        return ""


HEAD = git_head()


SCOPES: list[dict] = [
    {
        "scope": "targeted",
        "command": "python -m pytest tests/test_bootstrap.py tests/application/test_common.py tests/gui/test_pipeline_controller.py tests/gui/test_timeline_controller.py tests/test_benchmark_provenance.py tests/test_github_release_provider.py -q",
        "argv": [
            sys.executable, "-m", "pytest",
            "--override-ini=addopts=",
            "tests/test_bootstrap.py",
            "tests/application/test_common.py",
            "tests/gui/test_pipeline_controller.py",
            "tests/gui/test_timeline_controller.py",
            "tests/test_benchmark_provenance.py",
            "tests/test_github_release_provider.py",
            "-q",
        ],
        "rationale": (
            "Six targeted checks that justified Stage 2 'passed' transitions "
            "(V-M-APP-BOOTSTRAP, V-M-APP-COMMON, V-M-GUI-PIPELINE-CTRL, "
            "V-M-GUI-TIMELINE-CTRL, V-M-DETECT-BENCHMARK, V-M-GITHUB-PROVIDER)."
        ),
    },
    {
        "scope": "wave",
        "command": "python -m pytest tests/infra tests/domain tests/application tests/gui -q",
        "argv": [
            sys.executable, "-m", "pytest",
            "--override-ini=addopts=",
            "tests/infra", "tests/domain", "tests/application", "tests/gui",
            "-q",
        ],
        "rationale": (
            "Prior bounded Stage 2 wave command (controller-managed layer sweep)."
        ),
    },
    {
        "scope": "phase",
        "command": "python -m pytest tests --ignore=tests/e2e --ignore=tests/tools -q",
        "argv": [
            sys.executable, "-m", "pytest",
            "--override-ini=addopts=",
            "tests",
            "--ignore=tests/e2e",
            "--ignore=tests/tools",
            "-q",
        ],
        "rationale": (
            "Prior bounded phase command excluding E2E and tools (no "
            "benchmarks, no media-heavy runs, no new performance benchmark)."
        ),
    },
]


def parse_pytest_counts(output: str) -> dict:
    """Extract passed/failed/skipped/xfailed/xpassed from pytest -q summary line."""
    counts = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}
    # Find last "X passed, Y failed, ..." style line
    summary_re = re.compile(
        r"==\s+summary\s+==|"
        r"(?P<n>\d+)\s+(?P<k>passed|failed|skipped|xfailed|xpassed|errors|error)s?(?:,|\s)",
        re.IGNORECASE,
    )
    for line in output.splitlines():
        for m in summary_re.finditer(line):
            n = m.group("n")
            k = m.group("k")
            if n is None or k is None:
                continue
            k = k.lower()
            if k == "error":
                k = "failed"
            if k in counts:
                counts[k] += int(n)
    return counts


def run_scope(cfg: dict) -> dict:
    started_at = dt.datetime.now(dt.timezone.utc)
    proc = subprocess.run(
        cfg["argv"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60 * 60,  # generous
    )
    finished_at = dt.datetime.now(dt.timezone.utc)
    raw = proc.stdout + ("\n--- STDERR ---\n" + proc.stderr if proc.stderr else "")
    counts = parse_pytest_counts(proc.stdout + proc.stderr)

    txt_lines = [
        f"Repository HEAD: {HEAD}",
        f"Command: {cfg['command']}",
        f"Working directory: {ROOT}",
        f"Python version: {PYTHON_VERSION}",
        f"Pytest version: {PYTEST_VERSION}",
        f"Platform: {platform.platform()}",
        f"Started at: {started_at.isoformat()}",
        f"Finished at: {finished_at.isoformat()}",
        f"Exit code: {proc.returncode}",
        f"Rationale: {cfg['rationale']}",
        "",
        "RAW OUTPUT:",
        raw,
    ]
    txt_path = RUN_DIR / f"{cfg['scope']}-tests.txt"
    txt_path.write_text("\n".join(txt_lines), encoding="utf-8")

    json_block = {
        "head": HEAD,
        "scope": cfg["scope"],
        "command": cfg["command"],
        "working_directory": str(ROOT),
        "python_version": PYTHON_VERSION,
        "pytest_version": PYTEST_VERSION,
        "platform": platform.platform(),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "exit_code": proc.returncode,
        "passed": counts["passed"],
        "failed": counts["failed"],
        "skipped": counts["skipped"],
        "xfailed": counts["xfailed"],
        "xpassed": counts["xpassed"],
        "rationale": cfg["rationale"],
        "output_file": f"test-runs/{cfg['scope']}-tests.txt",
    }
    json_path = RUN_DIR / f"{cfg['scope']}-tests.json"
    json_path.write_text(json.dumps(json_block, indent=2) + "\n", encoding="utf-8")
    return json_block


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for cfg in SCOPES:
        print(f"Running {cfg['scope']}: {cfg['command']}")
        res = run_scope(cfg)
        print(
            f"  exit={res['exit_code']} "
            f"passed={res['passed']} failed={res['failed']} "
            f"skipped={res['skipped']} xfailed={res['xfailed']} "
            f"xpassed={res['xpassed']}"
        )
        results.append(res)

    index_path = RUN_DIR / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "head": HEAD,
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "scopes": results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {RUN_DIR}")


if __name__ == "__main__":
    main()
