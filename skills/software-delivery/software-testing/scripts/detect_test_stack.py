#!/usr/bin/env python3
"""Conservative repository test-stack detector for Stage 09.

The script only reads files and writes a JSON inventory. It does not install
packages or execute project test commands.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage", ".cache", "target",
    "bin", "obj", ".idea", ".vscode", ".terraform",
}

CONFIG_NAMES = {
    "vitest.config.js", "vitest.config.ts", "vitest.config.mjs", "vitest.config.mts",
    "jest.config.js", "jest.config.ts", "jest.config.cjs", "jest.config.mjs",
    "playwright.config.js", "playwright.config.ts", "playwright.config.mjs",
    "cypress.config.js", "cypress.config.ts", "pytest.ini", "tox.ini", "noxfile.py",
    "phpunit.xml", "phpunit.xml.dist", "pest.php", "go.mod", "Cargo.toml",
    "pom.xml", "build.gradle", "build.gradle.kts", "composer.json", "pyproject.toml",
}

MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "requirements.txt", "requirements-dev.txt",
    "Pipfile", "composer.json", "pom.xml", "build.gradle", "build.gradle.kts",
    "go.mod", "Cargo.toml", "global.json",
}

LOCKFILE_NAMES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb",
    "poetry.lock", "uv.lock", "Pipfile.lock", "composer.lock", "Cargo.lock",
}

MIGRATION_MARKERS = {
    "migrations", "migration", "alembic", "prisma", "drizzle", "flyway", "liquibase",
}


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def walk(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        cpath = Path(current)
        for name in files:
            yield cpath / name


def safe_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def add_unique(items: list[Any], value: Any) -> None:
    if value not in items:
        items.append(value)


def detect_package_json(path: Path, root: Path, out: dict[str, Any]) -> None:
    data = safe_json(path)
    if not isinstance(data, dict):
        out["warnings"].append(f"Could not parse {rel(path, root)} as JSON")
        return

    scripts = data.get("scripts") or {}
    deps = {}
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        value = data.get(key)
        if isinstance(value, dict):
            deps.update(value)

    known = {
        "vitest": "vitest",
        "jest": "jest",
        "@playwright/test": "playwright",
        "playwright": "playwright",
        "cypress": "cypress",
        "@testing-library/react": "testing-library-react",
        "@testing-library/vue": "testing-library-vue",
        "@testing-library/angular": "testing-library-angular",
        "supertest": "supertest",
        "msw": "msw",
        "@vitest/coverage-v8": "vitest-coverage-v8",
        "@vitest/coverage-istanbul": "vitest-coverage-istanbul",
        "nyc": "nyc",
    }
    for dep, label in known.items():
        if dep in deps:
            add_unique(out["frameworks"], label)

    test_scripts = {}
    if isinstance(scripts, dict):
        for name, command in scripts.items():
            lname = name.lower()
            if any(token in lname for token in ("test", "e2e", "spec", "coverage", "check")):
                test_scripts[name] = command
                add_unique(out["candidate_commands"], {
                    "source": rel(path, root),
                    "kind": "package-script",
                    "name": name,
                    "command": command,
                })

    out["package_json"].append({
        "path": rel(path, root),
        "package_manager_hint": data.get("packageManager"),
        "engines": data.get("engines"),
        "test_scripts": test_scripts,
    })
    add_unique(out["ecosystems"], "node")


def detect_pyproject(path: Path, root: Path, out: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    add_unique(out["ecosystems"], "python")
    if "pytest" in text:
        add_unique(out["frameworks"], "pytest")
    if "coverage" in text:
        add_unique(out["frameworks"], "coverage.py")
    if "tox" in text:
        add_unique(out["frameworks"], "tox")
    if "nox" in text:
        add_unique(out["frameworks"], "nox")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root not found: {root}")

    out: dict[str, Any] = {
        "schema_version": 1,
        "root": str(root),
        "ecosystems": [],
        "manifests": [],
        "lockfiles": [],
        "configs": [],
        "frameworks": [],
        "candidate_commands": [],
        "package_json": [],
        "ci_files": [],
        "migration_paths": [],
        "test_files_sample": [],
        "warnings": [],
        "notes": [
            "Inventory only; verify against repository configuration before executing commands.",
            "Candidate commands are not automatically safe to run.",
        ],
    }

    files = list(walk(root))
    for path in files:
        name = path.name
        r = rel(path, root)
        lower_r = r.lower()

        if name in MANIFEST_NAMES:
            add_unique(out["manifests"], r)
        if name in LOCKFILE_NAMES:
            add_unique(out["lockfiles"], r)
        if name in CONFIG_NAMES:
            add_unique(out["configs"], r)

        if name == "package.json":
            detect_package_json(path, root, out)
        elif name == "pyproject.toml":
            detect_pyproject(path, root, out)
        elif name == "pytest.ini":
            add_unique(out["ecosystems"], "python")
            add_unique(out["frameworks"], "pytest")
        elif name in {"phpunit.xml", "phpunit.xml.dist"}:
            add_unique(out["ecosystems"], "php")
            add_unique(out["frameworks"], "phpunit")
        elif name == "pest.php":
            add_unique(out["ecosystems"], "php")
            add_unique(out["frameworks"], "pest")
        elif name == "go.mod":
            add_unique(out["ecosystems"], "go")
            add_unique(out["frameworks"], "go-test")
        elif name == "Cargo.toml":
            add_unique(out["ecosystems"], "rust")
            add_unique(out["frameworks"], "cargo-test")
        elif name in {"pom.xml", "build.gradle", "build.gradle.kts"}:
            add_unique(out["ecosystems"], "jvm")
        elif name.endswith(".csproj") or name.endswith(".sln"):
            add_unique(out["ecosystems"], "dotnet")

        if name.startswith("playwright.config"):
            add_unique(out["frameworks"], "playwright")
        if name.startswith("cypress.config"):
            add_unique(out["frameworks"], "cypress")
        if name.startswith("vitest.config"):
            add_unique(out["frameworks"], "vitest")
        if name.startswith("jest.config"):
            add_unique(out["frameworks"], "jest")

        if lower_r.startswith(".github/workflows/") or any(
            token in lower_r for token in (".gitlab-ci", "azure-pipelines", "circleci/config", "jenkinsfile")
        ):
            add_unique(out["ci_files"], r)

        parts_lower = {part.lower() for part in path.parts}
        if parts_lower & MIGRATION_MARKERS:
            parent = path.parent
            try:
                add_unique(out["migration_paths"], rel(parent, root))
            except ValueError:
                pass

        if len(out["test_files_sample"]) < 100:
            lname = name.lower()
            if (
                lname.endswith((".test.js", ".test.ts", ".spec.js", ".spec.ts", ".test.tsx", ".spec.tsx", "_test.go"))
                or lname.startswith("test_") and lname.endswith(".py")
                or lname.endswith("_test.py")
                or "/tests/" in f"/{lower_r}/"
                or "/test/" in f"/{lower_r}/"
            ):
                add_unique(out["test_files_sample"], r)

    # Infer package manager from lockfiles conservatively.
    lock_names = {Path(p).name for p in out["lockfiles"]}
    package_managers = []
    if "pnpm-lock.yaml" in lock_names:
        package_managers.append("pnpm")
    if "yarn.lock" in lock_names:
        package_managers.append("yarn")
    if "package-lock.json" in lock_names:
        package_managers.append("npm")
    if "bun.lock" in lock_names or "bun.lockb" in lock_names:
        package_managers.append("bun")
    out["package_managers"] = package_managers

    payload = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        print(output)
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
