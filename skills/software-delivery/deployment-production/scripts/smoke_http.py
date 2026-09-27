#!/usr/bin/env python3
"""Run repeatable Stage 11 HTTP smoke checks.

Configuration example:
{
  "base_url": "http://127.0.0.1:8080",
  "retries": 3,
  "retry_delay_seconds": 1,
  "checks": [
    {"name": "health", "path": "/health", "expected_status": [200]},
    {"name": "ready", "path": "/ready", "expected_status": [200],
     "expected_body_contains": "ready"}
  ]
}

Secret header values can be provided indirectly:
  "headers_env": {"Authorization": "SMOKE_AUTHORIZATION"}
The environment variable value is used but never emitted in the report.
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_BODY = 64 * 1024


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def is_loopback(host: str | None) -> bool:
    if not host:
        return False
    h = host.lower().strip("[]")
    return h in {"localhost", "127.0.0.1", "::1"} or h.startswith("127.")


def ensure_safe_url(url: str, allow_insecure_http: bool) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise ValueError("URL has no hostname")
    if parsed.scheme == "http" and not is_loopback(parsed.hostname) and not allow_insecure_http:
        raise ValueError(
            "plain HTTP is allowed only for localhost by default; use --allow-insecure-http only for an intentional non-production test target"
        )


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


def build_url(base_url: str | None, check: dict[str, Any]) -> str:
    if check.get("url"):
        return str(check["url"])
    if not base_url:
        raise ValueError(f"check {check.get('name', '<unnamed>')} needs url or config base_url")
    path = str(check.get("path", "/"))
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def expected_statuses(check: dict[str, Any]) -> set[int]:
    raw = check.get("expected_status", [200])
    if isinstance(raw, int):
        return {raw}
    if isinstance(raw, list) and all(isinstance(x, int) for x in raw):
        return set(raw)
    raise ValueError("expected_status must be an integer or list of integers")


def build_headers(check: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    headers: dict[str, str] = {}
    public = check.get("headers", {})
    if public:
        if not isinstance(public, dict):
            raise ValueError("headers must be an object")
        headers.update({str(k): str(v) for k, v in public.items()})

    used_secret_header_names: list[str] = []
    secret_map = check.get("headers_env", {})
    if secret_map:
        if not isinstance(secret_map, dict):
            raise ValueError("headers_env must be an object")
        for header, env_name in secret_map.items():
            env_name = str(env_name)
            value = os.environ.get(env_name)
            if value is None:
                raise ValueError(f"required header environment variable is missing: {env_name}")
            headers[str(header)] = value
            used_secret_header_names.append(str(header))
    return headers, sorted(used_secret_header_names)


def run_once(check: dict[str, Any], base_url: str | None, timeout: float, allow_insecure_http: bool) -> dict[str, Any]:
    url = build_url(base_url, check)
    ensure_safe_url(url, allow_insecure_http)
    method = str(check.get("method", "GET")).upper()
    if method not in {"GET", "HEAD"}:
        raise ValueError("smoke_http supports only GET and HEAD to avoid accidental mutations")
    expected = expected_statuses(check)
    headers, secret_header_names = build_headers(check)
    body_contains = check.get("expected_body_contains")
    if body_contains is not None:
        body_contains = str(body_contains)

    follow_redirects = bool(check.get("follow_redirects", True))
    handlers: list[Any] = []
    if not follow_redirects:
        handlers.append(NoRedirect())
    # Default SSL context validates certificates and hostnames.
    handlers.append(urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    opener = urllib.request.build_opener(*handlers)

    request = urllib.request.Request(url=url, method=method, headers=headers)
    start = time.monotonic()
    status = None
    body = b""
    response_url = None
    error = None
    try:
        with opener.open(request, timeout=timeout) as response:
            status = int(response.status)
            response_url = response.geturl()
            if method != "HEAD":
                body = response.read(MAX_BODY)
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        response_url = exc.geturl()
        try:
            body = exc.read(MAX_BODY)
        except Exception:  # noqa: BLE001
            body = b""
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        error = f"{type(exc).__name__}: {exc}"

    duration_ms = round((time.monotonic() - start) * 1000, 2)
    status_ok = status in expected if status is not None else False
    body_ok = True
    if body_contains is not None:
        text = body.decode("utf-8", errors="replace")
        body_ok = body_contains in text

    return {
        "name": str(check.get("name") or url),
        "method": method,
        "url": url,
        "response_url": response_url,
        "status": status,
        "expected_status": sorted(expected),
        "status_ok": status_ok,
        "body_contains_checked": body_contains is not None,
        "body_match": body_ok if body_contains is not None else None,
        "duration_ms": duration_ms,
        "secret_headers_used": secret_header_names,
        "error": error,
        "passed": bool(status_ok and body_ok and error is None),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Run Stage 11 HTTP smoke checks")
    p.add_argument("--config", required=True, help="JSON smoke configuration")
    p.add_argument("--output", help="Write JSON result to this path")
    p.add_argument("--allow-insecure-http", action="store_true", help="Allow plain HTTP to non-loopback hosts for intentional test targets")
    args = p.parse_args()

    config_path = Path(args.config)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: cannot read config: {exc}", file=sys.stderr)
        return 2

    checks = config.get("checks")
    if not isinstance(checks, list) or not checks:
        print("ERROR: config.checks must be a non-empty list", file=sys.stderr)
        return 2

    base_url = config.get("base_url")
    retries = max(1, int(config.get("retries", 1)))
    delay = max(0.0, float(config.get("retry_delay_seconds", 1.0)))
    default_timeout = max(0.1, float(config.get("timeout_seconds", 5.0)))

    results = []
    for check in checks:
        if not isinstance(check, dict):
            print("ERROR: every check must be an object", file=sys.stderr)
            return 2
        attempts = []
        last = None
        try:
            timeout = max(0.1, float(check.get("timeout_seconds", default_timeout)))
            for attempt in range(1, retries + 1):
                result = run_once(check, base_url, timeout, args.allow_insecure_http)
                result["attempt"] = attempt
                attempts.append(result)
                last = result
                if result["passed"]:
                    break
                if attempt < retries:
                    time.sleep(delay)
        except (ValueError, TypeError) as exc:
            last = {
                "name": str(check.get("name", "<unnamed>")),
                "passed": False,
                "error": f"configuration error: {exc}",
            }
            attempts.append(last)
        results.append({
            "name": last.get("name") if last else str(check.get("name", "<unnamed>")),
            "passed": bool(last and last.get("passed")),
            "attempts": attempts,
        })

    report = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "config": str(config_path),
        "passed": all(r["passed"] for r in results),
        "results": results,
    }
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
