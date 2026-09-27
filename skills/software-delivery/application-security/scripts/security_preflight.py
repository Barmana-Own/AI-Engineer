#!/usr/bin/env python3
"""Create a non-secret repository inventory for Stage 08 AppSec preflight.

This script intentionally reads filenames and selected package metadata only. It does
not print environment-file contents or credential values.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "vendor", ".next", "dist", "build", "coverage",
    ".cache", ".turbo", ".venv", "venv", "__pycache__", "target", "out",
}

MANIFEST_NAMES = {
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "requirements.txt", "pyproject.toml", "poetry.lock", "Pipfile", "Pipfile.lock",
    "go.mod", "go.sum", "Cargo.toml", "Cargo.lock", "composer.json", "composer.lock",
    "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile", "Gemfile.lock",
}

DEPLOYMENT_NAMES = {
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
    "nginx.conf", "Caddyfile", "Procfile", "vercel.json", "netlify.toml",
}

ENV_NAMES = {".env", ".env.local", ".env.production", ".env.development", ".env.test"}

FRAMEWORK_PACKAGES = {
    "next": "Next.js",
    "react": "React",
    "vite": "Vite",
    "express": "Express",
    "fastify": "Fastify",
    "@nestjs/core": "NestJS",
    "koa": "Koa",
    "mysql2": "MySQL client (mysql2)",
    "mysql": "MySQL client",
    "sequelize": "Sequelize",
    "typeorm": "TypeORM",
    "prisma": "Prisma",
    "@prisma/client": "Prisma Client",
    "redis": "Redis client",
    "ioredis": "ioredis",
    "amqplib": "RabbitMQ/amqplib",
    "bullmq": "BullMQ",
    "@aws-sdk/client-s3": "AWS S3 SDK",
    "minio": "MinIO SDK",
    "passport": "Passport",
    "jsonwebtoken": "jsonwebtoken",
    "jose": "jose",
    "express-session": "express-session",
    "helmet": "Helmet",
    "cors": "cors",
    "multer": "Multer",
    "graphql": "GraphQL",
    "@apollo/server": "Apollo Server",
    "socket.io": "Socket.IO",
    "ws": "WebSocket (ws)",
    "openai": "OpenAI SDK",
    "@anthropic-ai/sdk": "Anthropic SDK",
    "langchain": "LangChain",
    "@langchain/core": "LangChain",
    "ollama": "Ollama",
}


def run_git(root: Path, args: list[str]) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def walk_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        cpath = Path(current)
        for name in files:
            yield cpath / name


def parse_package_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # metadata error only
        return {"path": str(path), "error": type(exc).__name__}
    deps = {}
    for field in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        value = data.get(field)
        if isinstance(value, dict):
            deps.update(value)
    frameworks = sorted({label for pkg, label in FRAMEWORK_PACKAGES.items() if pkg in deps})
    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
    return {
        "path": str(path),
        "name": data.get("name"),
        "private": data.get("private"),
        "package_manager": data.get("packageManager"),
        "framework_hints": frameworks,
        "scripts": {k: v for k, v in scripts.items() if k in {
            "test", "test:unit", "test:integration", "test:e2e", "lint", "typecheck",
            "build", "start", "dev", "audit", "security"
        }},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 08 repository preflight inventory")
    parser.add_argument("root", nargs="?", default=".", help="Project root")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: project root is not a directory: {root}", file=sys.stderr)
        return 2

    manifests: list[str] = []
    deployments: list[str] = []
    env_like: list[str] = []
    ci_files: list[str] = []
    package_files: list[dict] = []
    file_count = 0

    for path in walk_files(root):
        file_count += 1
        name = path.name
        r = rel(root, path)
        if name in MANIFEST_NAMES:
            manifests.append(r)
        if name in DEPLOYMENT_NAMES or name.startswith("Dockerfile"):
            deployments.append(r)
        if name in ENV_NAMES or name.startswith(".env."):
            env_like.append(r)
        if ".github/workflows/" in r.replace("\\", "/") or r in {".gitlab-ci.yml", "azure-pipelines.yml"}:
            ci_files.append(r)
        if name == "package.json" and path.stat().st_size <= 2_000_000:
            meta = parse_package_json(path)
            meta["path"] = r
            package_files.append(meta)

    git_head = run_git(root, ["rev-parse", "HEAD"])
    git_branch = run_git(root, ["branch", "--show-current"])
    git_status_raw = run_git(root, ["status", "--short"])
    status_lines = git_status_raw.splitlines() if git_status_raw else []

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "note": "Inventory only; not a vulnerability verdict. No environment-file contents were read for output.",
        "git": {
            "detected": git_head is not None,
            "branch": git_branch,
            "head": git_head,
            "worktree_change_count": len(status_lines),
            "worktree_paths": [line[3:] if len(line) > 3 else line for line in status_lines],
        },
        "file_count_excluding_common_generated_dirs": file_count,
        "manifests_and_lockfiles": sorted(set(manifests)),
        "deployment_files": sorted(set(deployments)),
        "environment_like_files": sorted(set(env_like)),
        "ci_files": sorted(set(ci_files)),
        "package_json": package_files,
        "framework_hints": sorted({
            fw for pkg in package_files for fw in pkg.get("framework_hints", [])
        }),
    }

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        out = Path(args.output).expanduser()
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
