#!/usr/bin/env python
"""MCP E2E Test Runner — launches GUI, connects to MCP, runs scenarios, reports results.

Usage:
    python tools/mcp_e2e_runner.py --repo D:\\git\\video2pptx --video path.mp4 --subtitles path.srt --workspace D:\\temp\\e2e
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StepResult:
    name: str
    success: bool
    duration_sec: float = 0.0
    data: dict = field(default_factory=dict)
    error: str | None = None


class McpClient:
    def __init__(self, port: int) -> None:
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def call(self, method: str, params: dict | None = None) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }
        data = json.dumps(payload).encode("utf-8")
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request("POST", "/", body=data, headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")
            return json.loads(body)
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()

    def initialize(self) -> dict:
        return self.call("initialize")

    def tools_list(self) -> dict:
        return self.call("tools/list")

    def tool_call(self, name: str, arguments: dict | None = None) -> dict:
        return self.call("tools/call", {"name": name, "arguments": arguments or {}})

    def health(self) -> dict:
        try:
            with urllib.request.urlopen(f"{self.base_url}/", timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return self.tool_call("health")


def find_mcp_port(repo_dir: Path, timeout: float = 30.0) -> int | None:
    deadline = time.time() + timeout
    port_file = repo_dir / ".mcp_port"
    while time.time() < deadline:
        if port_file.is_file():
            try:
                port = int(port_file.read_text().strip())
                return port
            except ValueError:
                pass
        time.sleep(0.5)
    return None


def wait_for_mcp(port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    client = McpClient(port)
    while time.time() < deadline:
        try:
            result = client.initialize()
            if "result" in result:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def run_e2e(
    repo: Path,
    video: Path,
    subtitles: Path | None,
    workspace: Path,
    project_name: str = "e2e_test",
) -> list[StepResult]:
    """Run E2E test using direct Python API calls (no MCP HTTP layer).

    This tests the application service layer directly, which is what GUI/MCP/CLI
    all delegate to. The MCP HTTP networking issue (Qt main thread blocking
    ThreadingMixIn server) is documented in F-0039.
    """
    results: list[StepResult] = []
    workspace.mkdir(parents=True, exist_ok=True)

    import sys
    sys.path.insert(0, str(repo / "src"))

    from video2pptx.app_service import (
        run_detect, run_preview, run_auto_align,
        run_export_md, run_export_pptx, run_auto,
    )
    from video2pptx.config import load_config
    from video2pptx.project_manager import create_project, open_project
    from video2pptx.models import SlidesDocument

    # Step 1: Create project
    t0 = time.time()
    proj_dir = workspace / project_name
    if proj_dir.exists():
        import shutil
        shutil.rmtree(proj_dir)
    try:
        create_project(str(proj_dir), name=project_name)
        ok = (proj_dir / "project.json").is_file()
    except Exception as e:
        ok = False
        results.append(StepResult("project_create", False, time.time() - t0, error=str(e)))
        return results
    results.append(StepResult("project_create", ok, time.time() - t0))

    # Step 2: Load config
    cfg = load_config()
    cfg.video.sample_fps = 0.5

    # Step 3: Quick Preview (scores only, no slides)
    t0 = time.time()
    try:
        result = run_preview(video, proj_dir, cfg)
        ok = result.success
        data = result.data
    except Exception as e:
        ok = False
        data = {"error": str(e)}
    results.append(StepResult("quick_preview", ok, time.time() - t0, data=data))

    # Step 4: Detect
    t0 = time.time()
    try:
        result = run_detect(video, proj_dir, cfg)
        ok = result.success
        data = result.data
        if ok:
            slides_json = proj_dir / "slides.json"
            doc = SlidesDocument.model_validate_json(slides_json.read_text(encoding="utf-8"))
            data["slides_count"] = len(doc.slides)
            data["slides_json_exists"] = True
            # Check slide images
            slides_dir = proj_dir / "slides"
            imgs = list(slides_dir.glob("slide_*.png")) if slides_dir.is_dir() else []
            data["images_count"] = len(imgs)
            # Check no exports
            data["deck_md_exists"] = (proj_dir / "deck.md").exists()
            data["deck_pptx_exists"] = (proj_dir / "deck.pptx").exists()
    except Exception as e:
        ok = False
        data = {"error": str(e)}
    results.append(StepResult("detect", ok, time.time() - t0, data=data))

    if not results[-1].success:
        print_report(results)
        return results

    # Step 5: Auto Align (dry run first)
    slides_json = proj_dir / "slides.json"
    if subtitles and slides_json.is_file():
        t0 = time.time()
        try:
            result = run_auto_align(slides_json, subtitles, dry_run=True)
            ok = result.success
            data = result.data
        except Exception as e:
            ok = False
            data = {"error": str(e)}
        results.append(StepResult("auto_align_dry_run", ok, time.time() - t0, data=data))

        # Step 6: Auto Align (apply)
        t0 = time.time()
        try:
            result = run_auto_align(slides_json, subtitles, dry_run=False, max_shift_sec=3.0)
            ok = result.success
            data = result.data
        except Exception as e:
            ok = False
            data = {"error": str(e)}
        results.append(StepResult("auto_align_apply", ok, time.time() - t0, data=data))

    # Step 7: Export Markdown
    t0 = time.time()
    try:
        result = run_export_md(slides_json)
        ok = result.success
        deck_path = proj_dir / "deck.md"
        data = {"deck_md_exists": deck_path.exists(), **result.data}
        if deck_path.exists():
            content = deck_path.read_text(encoding="utf-8")
            data["has_marp"] = "marp: true" in content
            data["has_double_slides"] = "slides/slides/" in content
            data["slide_separators"] = content.count("\n---\n")
    except Exception as e:
        ok = False
        data = {"error": str(e)}
    results.append(StepResult("export_md", ok, time.time() - t0, data=data))

    # Step 8: Export PPTX
    t0 = time.time()
    try:
        result = run_export_pptx(slides_json)
        ok = result.success
        pptx_path = proj_dir / "deck.pptx"
        data = {"deck_pptx_exists": pptx_path.exists(), **result.data}
    except Exception as e:
        ok = False
        data = {"error": str(e)}
    results.append(StepResult("export_pptx", ok, time.time() - t0, data=data))

    # Step 9: Validate project
    t0 = time.time()
    validation_errors: list[str] = []
    if not (proj_dir / "slides.json").is_file():
        validation_errors.append("slides.json missing")
    if not (proj_dir / "deck.md").is_file():
        validation_errors.append("deck.md missing")
    doc = SlidesDocument.model_validate_json(slides_json.read_text(encoding="utf-8"))
    if len(doc.slides) == 0:
        validation_errors.append("no slides detected")
    for i, s in enumerate(doc.slides):
        if s.start >= s.end:
            validation_errors.append(f"slide[{i}] invalid interval")
        if s.image and not (proj_dir / s.image).is_file():
            validation_errors.append(f"slide[{i}] image not found: {s.image}")
    ok = len(validation_errors) == 0
    results.append(StepResult("validate_project", ok, time.time() - t0,
                              data={"errors": validation_errors, "slides": len(doc.slides)}))

    return results


def print_report(results: list[StepResult]) -> None:
    print("\n" + "=" * 60)
    print("E2E TEST REPORT")
    print("=" * 60)
    passed = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    for r in results:
        status = "PASS" if r.success else "FAIL"
        print(f"  [{status}] {r.name} ({r.duration_sec:.1f}s)")
        if r.error:
            print(f"         Error: {r.error}")
    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="MCP E2E Test Runner")
    parser.add_argument("--repo", required=True, type=Path, help="Path to video2pptx repo")
    parser.add_argument("--video", required=True, type=Path, help="Path to test video")
    parser.add_argument("--subtitles", type=Path, default=None, help="Path to SRT/VTT")
    parser.add_argument("--workspace", required=True, type=Path, help="Test workspace dir")
    parser.add_argument("--project-name", default="e2e_test", help="Project name")
    args = parser.parse_args()

    results = run_e2e(
        repo=args.repo,
        video=args.video,
        subtitles=args.subtitles,
        workspace=args.workspace,
        project_name=args.project_name,
    )
    print_report(results)

    report_path = args.workspace / "e2e_report.json"
    report_data = [
        {"name": r.name, "success": r.success, "duration_sec": r.duration_sec, "error": r.error}
        for r in results
    ]
    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"\nReport saved: {report_path}")

    sys.exit(0 if all(r.success for r in results) else 1)


if __name__ == "__main__":
    main()
