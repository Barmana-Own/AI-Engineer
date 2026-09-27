#!/usr/bin/env python3
"""Discover a project's executable topology without modifying it."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

EXCLUDED_DIRS = {
    ".git", ".final-review", "node_modules", "vendor", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", ".cache", "coverage", "target",
    "__pycache__", ".idea", ".vscode"
}
LOCKFILES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock",
    "poetry.lock", "Pipfile.lock", "uv.lock", "composer.lock", "Cargo.lock", "go.sum"
}
MANIFESTS = {
    "package.json", "pyproject.toml", "requirements.txt", "Pipfile", "composer.json",
    "go.mod", "Cargo.toml", "Gemfile", "pom.xml", "build.gradle", "build.gradle.kts"
}
ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template", ".env.defaults"}
TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "specs", "e2e", "cypress", "playwright"}
MIGRATION_DIR_NAMES = {"migration", "migrations", "alembic", "prisma", "drizzle"}


def run_quiet(args: list[str], cwd: Path) -> str | None:
    try:
        p = subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           text=True, timeout=8, check=False)
        if p.returncode == 0:
            return p.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def walk_project(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        cpath = Path(current)
        for filename in files:
            yield cpath / filename


def runtime_version(exe: str, version_args: list[str]) -> dict[str, Any]:
    path = shutil.which(exe)
    if not path:
        return {"available": False}
    try:
        p = subprocess.run([path, *version_args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=8, check=False)
        first = (p.stdout or "").strip().splitlines()
        return {"available": True, "path": path, "version": first[0] if first else None,
                "exit_code": p.returncode}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": True, "path": path, "version": None, "error": str(exc)}


def detect_frameworks(deps: set[str]) -> list[str]:
    known = {
        "next": "Next.js", "react": "React", "vue": "Vue", "nuxt": "Nuxt",
        "@angular/core": "Angular", "svelte": "Svelte", "@sveltejs/kit": "SvelteKit",
        "express": "Express", "fastify": "Fastify", "@nestjs/core": "NestJS",
        "koa": "Koa", "hono": "Hono", "prisma": "Prisma", "@prisma/client": "Prisma",
        "drizzle-orm": "Drizzle ORM", "typeorm": "TypeORM", "sequelize": "Sequelize",
        "mongoose": "Mongoose", "vitest": "Vitest", "jest": "Jest",
        "playwright": "Playwright", "@playwright/test": "Playwright", "cypress": "Cypress"
    }
    return sorted({label for dep, label in known.items() if dep in deps})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--output")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    files = list(walk_project(root))
    file_set = {p.name for p in files}

    package_manifests: list[dict[str, Any]] = []
    frameworks: set[str] = set()
    command_candidates: dict[str, list[dict[str, str]]] = {
        "install": [], "build": [], "test": [], "lint": [], "typecheck": [],
        "format": [], "migrate": [], "seed": [], "start": [], "e2e": [], "security": []
    }
    name = None
    version = None

    for path in files:
        if path.name != "package.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            package_manifests.append({"path": rel(path, root), "parse_error": True})
            continue
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        deps = set()
        for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            val = data.get(key)
            if isinstance(val, dict):
                deps.update(val.keys())
        frameworks.update(detect_frameworks(deps))
        package_manifests.append({
            "path": rel(path, root),
            "name": data.get("name"),
            "version": data.get("version"),
            "private": data.get("private"),
            "scripts": scripts,
            "frameworks": detect_frameworks(deps),
        })
        if path.parent == root:
            name = data.get("name") or name
            version = data.get("version") or version
        for script_name, body in scripts.items():
            low = script_name.lower()
            item = {"manifest": rel(path, root), "script": script_name, "body": str(body)}
            if low in {"build", "compile"} or low.startswith("build:"):
                command_candidates["build"].append(item)
            if low == "test" or low.startswith("test:"):
                command_candidates["test"].append(item)
            if "lint" in low:
                command_candidates["lint"].append(item)
            if "typecheck" in low or "type-check" in low or low in {"types", "check:types"}:
                command_candidates["typecheck"].append(item)
            if "format" in low:
                command_candidates["format"].append(item)
            if "migrat" in low or low in {"db:push", "db:setup"}:
                command_candidates["migrate"].append(item)
            if "seed" in low:
                command_candidates["seed"].append(item)
            if low in {"start", "serve", "start:prod", "start:production"}:
                command_candidates["start"].append(item)
            if "e2e" in low or "playwright" in low or "cypress" in low:
                command_candidates["e2e"].append(item)
            if "audit" in low or "security" in low or "sast" in low:
                command_candidates["security"].append(item)

    lockfiles = sorted(rel(p, root) for p in files if p.name in LOCKFILES)
    manifests = sorted(rel(p, root) for p in files if p.name in MANIFESTS)
    env_templates = sorted(rel(p, root) for p in files if p.name in ENV_TEMPLATES)
    docker_files = sorted(rel(p, root) for p in files if p.name == "Dockerfile" or p.name.startswith("Dockerfile."))
    compose_files = sorted(rel(p, root) for p in files if p.name in {
        "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"
    } or p.name.startswith("docker-compose."))
    ci_files = sorted(rel(p, root) for p in files if ".github/workflows/" in p.as_posix()
                      or p.name in {".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml"})
    task_files = sorted(rel(p, root) for p in files if p.name in {"Makefile", "Taskfile.yml", "Taskfile.yaml", "justfile"})
    api_specs = sorted(rel(p, root) for p in files if p.name.lower() in {
        "openapi.json", "openapi.yaml", "openapi.yml", "swagger.json", "swagger.yaml", "swagger.yml"
    } or p.suffix.lower() == ".graphql")
    docs = sorted(rel(p, root) for p in files if p.suffix.lower() in {".md", ".mdx"})
    test_dirs = sorted({rel(p.parent, root) for p in files if any(part.lower() in TEST_DIR_NAMES for part in p.relative_to(root).parts[:-1])})
    migration_dirs = sorted({rel(p.parent, root) for p in files if any(part.lower() in MIGRATION_DIR_NAMES for part in p.relative_to(root).parts[:-1])})

    git_inside = run_quiet(["git", "rev-parse", "--is-inside-work-tree"], root) == "true"
    git_info: dict[str, Any] = {"is_repo": git_inside}
    if git_inside:
        git_info.update({
            "revision": run_quiet(["git", "rev-parse", "HEAD"], root),
            "branch": run_quiet(["git", "rev-parse", "--abbrev-ref", "HEAD"], root),
            "status_short": (run_quiet(["git", "status", "--short"], root) or "").splitlines(),
        })

    runtimes = {
        "node": runtime_version("node", ["--version"]),
        "npm": runtime_version("npm", ["--version"]),
        "pnpm": runtime_version("pnpm", ["--version"]),
        "yarn": runtime_version("yarn", ["--version"]),
        "bun": runtime_version("bun", ["--version"]),
        "python3": runtime_version("python3", ["--version"]),
        "php": runtime_version("php", ["--version"]),
        "composer": runtime_version("composer", ["--version"]),
        "go": runtime_version("go", ["version"]),
        "rustc": runtime_version("rustc", ["--version"]),
        "cargo": runtime_version("cargo", ["--version"]),
        "docker": runtime_version("docker", ["--version"]),
    }

    profile = {
        "schema_version": 1,
        "project_root": str(root),
        "project": {"name": name or root.name, "version": version},
        "git": git_info,
        "file_count_scanned": len(files),
        "manifests": manifests,
        "package_manifests": package_manifests,
        "lockfiles": lockfiles,
        "frameworks": sorted(frameworks),
        "dockerfiles": docker_files,
        "compose_files": compose_files,
        "ci_files": ci_files,
        "task_files": task_files,
        "api_specs": api_specs,
        "env_templates": env_templates,
        "test_dirs": test_dirs,
        "migration_dirs": migration_dirs,
        "documentation": docs,
        "command_candidates": command_candidates,
        "runtimes": runtimes,
        "signals": {
            "has_persistence_signals": bool(migration_dirs) or any("prisma" in x.lower() or "alembic" in x.lower() for x in manifests),
            "has_container_signals": bool(docker_files or compose_files),
            "has_ci": bool(ci_files),
            "has_tests": bool(test_dirs) or bool(command_candidates["test"]),
        },
    }

    out = Path(args.output).resolve() if args.output else root / ".final-review" / "project-profile.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Project profile written: {out}")
    print(f"Scanned files: {len(files)} | manifests: {len(manifests)} | frameworks: {', '.join(sorted(frameworks)) or 'none detected'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
