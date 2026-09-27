#!/usr/bin/env python3
"""Regression tests for Stage 11 helper scripts using only stdlib."""
from __future__ import annotations

import http.server
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )


def assert_ok(proc: subprocess.CompletedProcess[str], label: str) -> None:
    if proc.returncode != 0:
        raise AssertionError(
            f"{label} failed with exit {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            payload = b'{"status":"ok"}'
            self.send_response(200)
        elif self.path == "/ready":
            payload = b'{"status":"ready"}'
            self.send_response(200)
        else:
            payload = b'not found'
            self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):  # noqa: A002
        return


def init_git(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "stage11@test.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Stage11 Test"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True)


def evidence_fixture() -> dict:
    gate_ids = [
        "G00_PRECONDITIONS",
        "G01_RELEASE_BASELINE",
        "G02_DETERMINISTIC_BUILD",
        "G03_RUNTIME_PACKAGING",
        "G04_CONFIG_AND_SECRETS",
        "G05_DATABASE_AND_DATA",
        "G06_EDGE_AND_NETWORK",
        "G07_CI_CD_AND_PROMOTION",
        "G08_SUPPLY_CHAIN_SECURITY",
        "G09_OBSERVABILITY",
        "G10_BACKUP_RESTORE",
        "G11_RELEASE_STRATEGY",
        "G12_PRODUCTION_LIKE_VALIDATION",
        "G13_DEPLOYMENT_TRUTH",
        "G14_EVIDENCE_AND_HANDOFF",
    ]
    return {
        "stage": "11-deployment-production",
        "generated_at": "2026-01-01T00:00:00Z",
        "source": {"commit": "test", "ref": "main", "dirty": False},
        "release_candidate": {"version": "1.0.0", "artifact_ids": ["artifact.txt"]},
        "deployment": {"status": "NOT_PERFORMED", "target": None, "url": None},
        "gates": [
            {
                "id": gid,
                "status": "PASS",
                "summary": f"{gid} passed in fixture",
                "evidence": ["fixture:evidence"],
                "findings": [],
                "rationale": None,
            }
            for gid in gate_ids
        ],
        "residual_risks": [],
        "blockers": [],
        "stage12_handoff": {"review_focus": [], "known_warnings": [], "external_assumptions": []},
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="stage11-selftest-") as tmp:
        root = Path(tmp)
        (root / "package.json").write_text('{"name":"fixture","version":"1.0.0"}\n', encoding="utf-8")
        (root / "package-lock.json").write_text('{"name":"fixture","lockfileVersion":3}\n', encoding="utf-8")
        (root / ".env.example").write_text("PORT=8080\n", encoding="utf-8")
        (root / "artifact.txt").write_text("release artifact\n", encoding="utf-8")
        (root / "project-state.json").write_text(
            json.dumps({
                "completed_stages": [
                    {"id": "10-quality-security", "status": "PASS", "artifacts": ["stage10-report.json"]}
                ]
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        init_git(root)

        preflight_out = root / "artifacts/stage-11/preflight.json"
        proc = run(str(HERE / "stage11_preflight.py"), "--root", str(root), "--json-out", str(preflight_out))
        assert_ok(proc, "preflight")
        preflight = json.loads(preflight_out.read_text(encoding="utf-8"))
        assert preflight["source"]["commit"], "preflight must capture git commit"
        stage10 = next(c for c in preflight["checks"] if c["id"] == "stage10_state")
        assert stage10["status"] == "PASS", stage10

        manifest_out = root / "artifacts/stage-11/release-manifest.json"
        proc = run(
            str(HERE / "release_manifest.py"),
            "--root", str(root),
            "--output", str(manifest_out),
            "--version", "1.0.0",
            "--environment", "production-like",
            "--artifact", "artifact.txt",
            "--deployment-status", "NOT_PERFORMED",
        )
        assert_ok(proc, "release manifest")
        manifest = json.loads(manifest_out.read_text(encoding="utf-8"))
        assert len(manifest["artifacts"]) == 1
        assert len(manifest["artifacts"][0]["sha256"]) == 64

        evidence_path = root / "artifacts/stage-11/evidence.json"
        evidence_path.write_text(json.dumps(evidence_fixture(), indent=2) + "\n", encoding="utf-8")
        proc = run(str(HERE / "validate_evidence.py"), str(evidence_path), "--require-pass")
        assert_ok(proc, "evidence validation")

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            smoke_config = root / "smoke.json"
            smoke_config.write_text(
                json.dumps({
                    "base_url": f"http://127.0.0.1:{port}",
                    "retries": 2,
                    "retry_delay_seconds": 0.05,
                    "checks": [
                        {"name": "health", "path": "/health", "expected_status": [200], "expected_body_contains": "ok"},
                        {"name": "ready", "path": "/ready", "expected_status": [200], "expected_body_contains": "ready"},
                    ],
                }, indent=2) + "\n",
                encoding="utf-8",
            )
            smoke_out = root / "artifacts/stage-11/smoke.json"
            proc = run(str(HERE / "smoke_http.py"), "--config", str(smoke_config), "--output", str(smoke_out))
            assert_ok(proc, "HTTP smoke")
            smoke = json.loads(smoke_out.read_text(encoding="utf-8"))
            assert smoke["passed"] is True
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        # Negative evidence test: a failed gate must block --require-pass.
        bad = evidence_fixture()
        bad["gates"][2]["status"] = "FAIL"
        bad_path = root / "bad-evidence.json"
        bad_path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
        proc = run(str(HERE / "validate_evidence.py"), str(bad_path), "--require-pass")
        if proc.returncode == 0:
            raise AssertionError("failed gate incorrectly accepted as PASS-eligible")

    print("SELF_TEST_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
