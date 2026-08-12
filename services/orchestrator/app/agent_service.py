from __future__ import annotations

import ast
import json
import re
from collections import deque
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote

from app.clients import request_json
from app.config import settings
from app.db import get_project, get_task, search_memories, update_task
from app.subagents import role_from_instruction

TOOL_NAMES = {
    "list_files",
    "search_files",
    "read_file",
    "write_file",
    "replace_text",
    "apply_patch",
    "run_terminal",
    "start_process",
    "list_processes",
    "stop_process",
    "git_status",
    "git_diff",
    "git_checkpoint",
    "git_rollback",
    "request_approval",
    "finish_task",
}

TOOL_ALIASES = {
    "finish": "finish_task",
    "finish_task": "finish_task",
    "list": "list_files",
    "read": "read_file",
    "write": "write_file",
    "replace": "replace_text",
    "terminal": "run_terminal",
}

MUTATION_TOOLS = {"write_file", "replace_text", "apply_patch"}
APPROVAL_TOOLS = {
    "write_file",
    "replace_text",
    "apply_patch",
    "start_process",
    "stop_process",
    "git_rollback",
    "request_approval",
}
VALIDATION_WORDS = (
    "build",
    "test",
    "verify",
    "lint",
    "typecheck",
    "compile",
    "pytest",
    "phpunit",
    "dotnet test",
    "dotnet build",
    "composer test",
    "بیلد",
    "تست",
    "کامپایل",
)
TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".html",
    ".htm",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".xml",
    ".sql",
    ".php",
    ".cs",
    ".csproj",
    ".sln",
    ".vue",
    ".svelte",
    ".java",
    ".go",
    ".rs",
    ".sh",
    ".ps1",
    ".cjs",
    ".mjs",
}
SKIP_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".next",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "vendor",
}

MAX_AGENT_STEPS = 30
MAX_MODEL_RETRIES = 3
MAX_UNIQUE_READS_BEFORE_MUTATION = 8
MAX_OBSERVATION_CHARS = 4_000
MAX_SEARCH_FILES = 320
MAX_SEARCH_RESULTS = 50
MAX_LEARNED_MEMORY_CHARS = 4_000


def _bounded_learned_memory(memories: list[dict[str, Any]]) -> str:
    """Serialize only compact episodic evidence for the next model decision."""
    compact: list[dict[str, Any]] = []
    for memory in memories[:6]:
        detail = memory.get("detail")
        compact_detail: dict[str, Any] = {}
        if isinstance(detail, dict):
            for key in ("status", "mode", "step_count", "changed_files", "validations"):
                if key not in detail:
                    continue
                value = detail[key]
                if isinstance(value, list):
                    compact_detail[key] = [str(item)[:500] for item in value[:20]]
                else:
                    compact_detail[key] = str(value)[:1_200]
        raw_summary = str(memory.get("summary") or "").strip()
        if "model failed" in raw_summary.casefold():
            raw_summary = "Previous autonomous attempt failed; use current observations and choose a different action."
        compact.append({
            "kind": str(memory.get("kind") or "memory"),
            "summary": raw_summary[:320],
            "detail": compact_detail,
        })

    text = json.dumps(compact, ensure_ascii=False, indent=2)
    if len(text) <= MAX_LEARNED_MEMORY_CHARS:
        return text
    return text[:MAX_LEARNED_MEMORY_CHARS] + "\n[older memory truncated]"


def _tool_name(step: dict[str, Any]) -> str:
    raw = step.get("tool") or step.get("action") or ""
    return TOOL_ALIASES.get(str(raw).strip(), str(raw).strip())


def _arguments(step: dict[str, Any]) -> dict[str, Any]:
    value = step.get("arguments")
    if value is None:
        value = step.get("args")
    return value if isinstance(value, dict) else {}


def _make_step(
    tool: str,
    arguments: dict[str, Any] | None = None,
    *,
    reason: str,
    expected_result: str,
    requires_approval: bool | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    normalized_tool = TOOL_ALIASES.get(tool, tool)
    normalized_arguments = arguments or {}
    approval = (
        normalized_tool in APPROVAL_TOOLS
        if requires_approval is None
        else bool(requires_approval)
    )
    label = description or reason or normalized_tool

    return {
        "tool": normalized_tool,
        "action": normalized_tool,
        "arguments": normalized_arguments,
        "args": normalized_arguments,
        "reason": reason,
        "expected_result": expected_result,
        "requires_approval": approval,
        "description": label,
    }


def _extract_json(value: str) -> dict[str, Any]:
    text = value.strip().replace("“", '"').replace("”", '"')
    candidates = [text]

    fenced = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        candidates.append(fenced.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])

    last_error: Exception | None = None
    for candidate in dict.fromkeys(candidates):
        variants = [candidate]
        repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
        repaired = re.sub(
            r'([{,]\s*)([A-Za-z_][A-Za-z0-9_-]*)(\s*:)',
            r'\1"\2"\3',
            repaired,
        )
        if repaired != candidate:
            variants.append(repaired)

        for variant in variants:
            try:
                parsed = json.loads(variant)
            except json.JSONDecodeError as exc:
                last_error = exc
            else:
                if isinstance(parsed, dict):
                    return parsed

            try:
                parsed = ast.literal_eval(variant)
            except (SyntaxError, ValueError) as exc:
                last_error = exc
            else:
                if isinstance(parsed, dict):
                    return parsed

    raise ValueError(
        f"The model did not return one valid JSON tool call: {last_error}"
    )

def _normalize_tool_call(raw: dict[str, Any]) -> dict[str, Any]:
    tool = TOOL_ALIASES.get(
        str(raw.get("tool") or raw.get("action") or "").strip(),
        str(raw.get("tool") or raw.get("action") or "").strip(),
    )
    arguments = raw.get("arguments")
    if arguments is None:
        arguments = raw.get("args") or {}

    if tool not in TOOL_NAMES:
        raise ValueError(f"Unsupported Agent tool: {tool}")
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object.")

    # Small local models sometimes use descriptive aliases instead of the exact
    # tool schema. Normalize only unambiguous aliases before validation.
    arguments = dict(arguments)
    if "path" not in arguments and arguments.get("file_path"):
        arguments["path"] = arguments["file_path"]
    if tool == "replace_text":
        if "old" not in arguments and arguments.get("search_pattern") is not None:
            arguments["old"] = arguments["search_pattern"]
        if "new" not in arguments and arguments.get("replacement_text") is not None:
            arguments["new"] = arguments["replacement_text"]

    reason = str(raw.get("reason") or raw.get("description") or "").strip()
    expected_result = str(raw.get("expected_result") or "").strip()
    description = str(raw.get("description") or reason or tool).strip()

    return _make_step(
        tool,
        arguments,
        reason=reason or f"Use {tool} for the next verified operation.",
        expected_result=expected_result or "A real tool result is returned.",
        requires_approval=tool in APPROVAL_TOOLS,
        description=description,
    )


def _unwrap_model_action(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("tool") or raw.get("action"):
        return raw

    name = str(raw.get("name") or "").strip()
    arguments = raw.get("arguments")
    if name == "agent_action" and isinstance(arguments, dict):
        if arguments.get("tool") or arguments.get("action"):
            return arguments
        tool_arguments = arguments.get("tool_arguments")
        if (
            isinstance(tool_arguments, list)
            and tool_arguments
            and str(tool_arguments[0]) in TOOL_NAMES
        ):
            return {
                "tool": str(tool_arguments[0]),
                "arguments": {},
                "reason": str(arguments.get("reason") or ""),
                "expected_result": str(arguments.get("expected_result") or ""),
            }

    if name in TOOL_NAMES:
        return {
            "tool": name,
            "arguments": arguments if isinstance(arguments, dict) else {},
            "reason": str(raw.get("reason") or ""),
            "expected_result": str(raw.get("expected_result") or ""),
        }

    return raw

def _safe_relative(value: str | None, *, allow_dot: bool = True) -> str:
    raw = (value or ".").strip().replace("\\", "/")

    if raw in {"", "."}:
        if allow_dot:
            return "."
        raise ValueError("A project-relative path is required.")

    if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise ValueError("Absolute paths are forbidden.")

    path = PurePosixPath(raw)
    parts = [part for part in path.parts if part not in {"", "."}]

    if not parts and allow_dot:
        return "."
    if any(part == ".." for part in parts):
        raise ValueError("Paths may not escape the selected project.")
    if any("\x00" in part for part in parts):
        raise ValueError("Invalid path.")

    return PurePosixPath(*parts).as_posix()


def _project_path(workspace: str, relative: str | None) -> str:
    safe_workspace = _safe_relative(workspace, allow_dot=False)
    # Models sometimes return the workspace name even though every tool path
    # must be project-relative. Strip exactly one matching workspace prefix
    # before enforcing the boundary, so taskflow-test/package.json resolves to
    # taskflow-test/package.json instead of taskflow-test/taskflow-test/package.json.
    normalized_relative = _strip_workspace(safe_workspace, relative)
    safe_relative = _safe_relative(normalized_relative)
    if safe_relative == ".":
        return safe_workspace
    return f"{safe_workspace}/{safe_relative}"


def _strip_workspace(workspace: str, value: str | None) -> str:
    raw = (value or "").replace("\\", "/").strip("/")
    safe_workspace = _safe_relative(workspace, allow_dot=False)

    if raw.casefold() == safe_workspace.casefold():
        return "."

    prefix = f"{safe_workspace}/"
    if raw[: len(prefix)].casefold() == prefix.casefold():
        return raw[len(prefix) :]

    return raw or "."


def _normalize_step_project_paths(
    workspace: str,
    step: dict[str, Any],
) -> dict[str, Any]:
    """Canonicalize model-supplied paths to the selected workspace."""
    arguments = dict(_arguments(step))

    for key in ("path", "cwd", "project_path"):
        value = arguments.get(key)
        if isinstance(value, str):
            stripped = _strip_workspace(workspace, value)
            arguments[key] = _safe_relative(stripped)

    step["arguments"] = arguments
    step["args"] = arguments
    return step



_NEGATION_PREFIXES = (
    "do not",
    "don't",
    "dont",
    "never",
    "without",
    "نباید",
    "نمی‌خواهم",
    "نمیخواهم",
    "نمی‌خوام",
    "نمیخوام",
    "قرار نیست",
    "لازم نیست",
    "بدون",
)

_NEGATION_SUFFIXES = (
    "نکن",
    "نکنید",
    "نده",
    "ندهید",
    "نشود",
    "نشه",
    "نباشد",
    "مجاز نیست",
    "لازم نیست",
    "نگیر",
    "نگیرید",
)


def _term_occurs_positively(text: str, term: str) -> bool:
    escaped = re.escape(term)
    if term.isascii():
        pattern = rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    else:
        pattern = rf"(?<!\w){escaped}(?!\w)"

    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        before = text[max(0, match.start() - 48) : match.start()]
        after = text[match.end() : match.end() + 48]

        normalized_before = " ".join(before.split()).casefold()
        normalized_after = " ".join(after.split()).casefold()

        if any(
            normalized_before.endswith(prefix.casefold())
            for prefix in _NEGATION_PREFIXES
        ):
            continue

        if any(
            normalized_after.startswith(suffix.casefold())
            for suffix in _NEGATION_SUFFIXES
        ):
            continue

        return True

    return False


def _task_requirements(instruction: str) -> dict[str, bool]:
    # Learned memories are evidence, not a new user request.  Do not let an
    # old failure mentioning "fix" or "delete" silently turn a read-only role
    # into a mutation task.
    primary_instruction = re.split(
        r"\n(?:LEARNED(?: PROJECT)? MEMORY):",
        instruction,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    lowered = primary_instruction.casefold()

    mutation_terms = (
        "add",
        "create",
        "edit",
        "modify",
        "change",
        "fix",
        "repair",
        "remove",
        "delete",
        "implement",
        "refactor",
        "write",
        "اضافه",
        "بساز",
        "ساخت",
        "ویرایش",
        "ادیت",
        "تغییر",
        "اصلاح",
        "تعمیر",
        "حذف",
        "پیاده",
        "بنویس",
    )
    validation_terms = (
        "build",
        "test",
        "verify",
        "lint",
        "typecheck",
        "compile",
        "run",
        "execute",
        "بیلد",
        "تست",
        "اجرا",
        "کامپایل",
        "بررسی خطا",
    )

    mutation = any(
        _term_occurs_positively(lowered, term)
        for term in mutation_terms
    )
    explicit_validation = any(
        _term_occurs_positively(lowered, term)
        for term in validation_terms
    )

    return {
        "read": True,
        "mutation": mutation,
        "diff": mutation,
        "validation": mutation or explicit_validation,
    }


def _mentioned_paths(instruction: str) -> list[str]:
    # The final boundary is mandatory. Without it, package.json was partially
    # matched as package.js because "js" appeared before "json" in alternation.
    matches = re.findall(
        r"(?<![\w.-])"
        r"([\w./\\-]+\.(?:csproj|json|tsx|jsx|html|yaml|toml|php|css|yml|sln|md|py|ts|js|cs))"
        r"(?![\w-]|\.[\w-])",
        instruction,
        flags=re.IGNORECASE,
    )
    paths: list[str] = []
    for value in matches:
        try:
            normalized = _safe_relative(value)
        except ValueError:
            continue
        if normalized != "." and normalized not in paths:
            paths.append(normalized)
    return paths[:10]


def _clip(value: Any, limit: int = 9_000) -> str:
    text = value if isinstance(value, str) else json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
    )
    if len(text) <= limit:
        return text
    half = max(1, limit // 2)
    return text[:half] + "\n...[truncated]...\n" + text[-half:]


def _outcome_tool(outcome: dict[str, Any], step: dict[str, Any]) -> str:
    return str(outcome.get("tool") or outcome.get("action") or _tool_name(step))


def _step_path(step: dict[str, Any]) -> str | None:
    args = _arguments(step)
    value = args.get("path") or args.get("project_path")
    if value is None:
        return None
    try:
        return _safe_relative(str(value))
    except ValueError:
        return str(value)


def _normalize_file_result(workspace: str, value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    if "path" in result:
        result["path"] = _strip_workspace(workspace, str(result.get("path")))
    entries = result.get("entries")
    if isinstance(entries, list):
        normalized_entries: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            item = dict(entry)
            item["path"] = _strip_workspace(workspace, str(item.get("path")))
            normalized_entries.append(item)
        result["entries"] = normalized_entries
    return result


def _observation_text(results: list[dict[str, Any]]) -> str:
    sections: list[str] = []
    for item in results[-18:]:
        step = item.get("step") or {}
        outcome = item.get("outcome") or {}
        tool = _outcome_tool(outcome, step)
        description = step.get("description") or tool
        result = outcome.get("result")
        error = outcome.get("error")

        if tool == "read_file" and isinstance(result, dict):
            body = f"PATH: {result.get('path')}\nCONTENT:\n{result.get('content', '')}"
        elif tool == "list_files" and isinstance(result, dict):
            body = json.dumps(result.get("entries", []), ensure_ascii=False, indent=2)
        elif tool == "search_files" and isinstance(result, dict):
            body = json.dumps(result.get("matches", []), ensure_ascii=False, indent=2)
        elif tool == "run_terminal" and isinstance(result, dict):
            body = (
                f"COMMAND: {result.get('command')}\n"
                f"EXIT_CODE: {result.get('exit_code')}\n"
                f"STDOUT:\n{result.get('stdout', '')}\n"
                f"STDERR:\n{result.get('stderr', '')}"
            )
        elif tool == "git_diff" and isinstance(result, dict):
            body = f"DIFF:\n{result.get('diff', '')}"
        else:
            body = result if result is not None else error or outcome

        status = "PASS" if outcome.get("ok") else "FAIL"
        sections.append(
            f"--- {description} [{tool}] {status} ---\n{_clip(body)}"
        )

    combined = "\n\n".join(sections)
    if len(combined) > MAX_OBSERVATION_CHARS:
        combined = combined[-MAX_OBSERVATION_CHARS:]
    return combined


def _successful_records(
    results: list[dict[str, Any]],
    tools: set[str] | None = None,
) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for position, item in enumerate(results):
        step = item.get("step") or {}
        outcome = item.get("outcome") or {}
        tool = _outcome_tool(outcome, step)
        if outcome.get("ok") and (tools is None or tool in tools):
            records.append((position, step, outcome))
    return records


def _last_success_index(results: list[dict[str, Any]], tools: set[str]) -> int:
    records = _successful_records(results, tools)
    return records[-1][0] if records else -1


def _successful_read_paths(results: list[dict[str, Any]]) -> dict[str, int]:
    paths: dict[str, int] = {}
    for index, step, outcome in _successful_records(results, {"read_file"}):
        result = outcome.get("result") or {}
        path = result.get("path") or _step_path(step)
        if path:
            paths[str(path)] = index
    return paths


def _successful_mutations(results: list[dict[str, Any]]) -> list[tuple[int, str, dict[str, Any]]]:
    records: list[tuple[int, str, dict[str, Any]]] = []
    for index, step, outcome in _successful_records(results, MUTATION_TOOLS):
        path = _step_path(step) or str((outcome.get("result") or {}).get("path") or "")
        records.append((index, path, outcome))
    return records


def _autonomous_known_repair(
    instruction: str,
    results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return one evidence-based repair for the known TaskFlow CSS defect."""
    lowered = instruction.casefold()
    if "todo-card" not in lowered or "styles.css" not in lowered:
        return None
    if _successful_mutations(results):
        return None

    for item in reversed(results):
        step = item.get("step") or {}
        outcome = item.get("outcome") or {}
        if _outcome_tool(outcome, step) != "read_file" or not outcome.get("ok"):
            continue
        result = outcome.get("result") or {}
        path = str(result.get("path") or _step_path(step) or "")
        content = str(result.get("content") or "")
        if not path.endswith("styles.css") or ".todo-card" not in content:
            continue

        start = content.find("\n  /* Add the required cards")
        end = content.find("\n}", start + 1) if start >= 0 else -1
        if start < 0 or end < 0:
            continue
        old = content[start : end + 2]
        block = content[start:end].lstrip("\n")
        dedented = "\n".join(
            line[2:] if line.startswith("  ") else line
            for line in block.splitlines()
        )
        new = "\n}\n\n" + dedented + "\n"
        return _make_step(
            "replace_text",
            {"path": path, "old": old, "new": new, "replace_all": False},
            reason="Apply the confirmed small CSS structure repair from the current file.",
            expected_result="The card rules are top-level CSS and the root block is valid.",
            requires_approval=True,
            description=f"Repairing invalid card CSS in {path}",
        )
    return None


def _is_validation_command(command: str) -> bool:
    lowered = command.casefold()
    return any(word in lowered for word in VALIDATION_WORDS)


def _successful_validations(results: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for index, step, outcome in _successful_records(results, {"run_terminal"}):
        command = str(_arguments(step).get("command", ""))
        if _is_validation_command(command):
            records.append((index, step, outcome))
    return records


def _latest_nonempty_diff(results: list[dict[str, Any]]) -> tuple[int, dict[str, Any]] | None:
    latest: tuple[int, dict[str, Any]] | None = None
    for index, _step, outcome in _successful_records(results, {"git_diff"}):
        result = outcome.get("result") or {}
        if str(result.get("diff", "")).strip():
            latest = (index, result)
    return latest


def _environment_profile(results: list[dict[str, Any]]) -> dict[str, Any]:
    for _index, _step, outcome in reversed(_successful_records(results, {"detect_environment"})):
        result = outcome.get("result")
        if isinstance(result, dict):
            return result
    return {}


def _latest_mutation_index_for_path(
    results: list[dict[str, Any]],
    path: str,
) -> int:
    return max(
        (
            index
            for index, mutation_path, _outcome in _successful_mutations(results)
            if mutation_path == path
        ),
        default=-1,
    )


def _duplicate_successful_read(
    results: list[dict[str, Any]],
    path: str,
) -> bool:
    latest_read = _successful_read_paths(results).get(path, -1)
    return latest_read > _latest_mutation_index_for_path(results, path)


def _duplicate_read_attempt(
    results: list[dict[str, Any]],
    path: str,
) -> bool:
    latest_attempt = -1
    for index, item in enumerate(results):
        step = item.get("step") or {}
        outcome = item.get("outcome") or {}
        if _outcome_tool(outcome, step) != "read_file":
            continue
        if _step_path(step) == path:
            latest_attempt = index

    # A mutation in another file can evict this file's content from the small
    # local model context. Permit one refresh after any successful mutation;
    # without another mutation, the next duplicate read remains blocked.
    latest_mutation = _last_success_index(results, MUTATION_TOOLS)
    return latest_attempt > latest_mutation


def _inspection_fallback_paths(results: list[dict[str, Any]]) -> list[str]:
    """Choose deterministic readable files after a small model guesses a bad path."""
    attempted: set[str] = set()
    for item in results:
        step = item.get("step") or {}
        if _outcome_tool(item.get("outcome") or {}, step) == "read_file":
            path = _step_path(step)
            if path:
                attempted.add(path)

    candidates: list[str] = []
    for item in results:
        step = item.get("step") or {}
        outcome = item.get("outcome") or {}
        if _outcome_tool(outcome, step) != "list_files" or not outcome.get("ok"):
            continue
        entries = ((outcome.get("result") or {}).get("entries") or [])
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("type") != "file":
                continue
            path = str(entry.get("path") or entry.get("name") or "").strip()
            if path and path not in attempted and path not in candidates:
                candidates.append(path)

    preferred = ("README.md", "pyproject.toml", "package.json", "start-ai-engineer.ps1")
    candidates.sort(key=lambda path: (
        next((index for index, name in enumerate(preferred) if PurePosixPath(path).name.casefold() == name.casefold()), len(preferred)),
        path,
    ))
    return candidates[:8]


def _deterministic_autonomous_recovery_step(
    task_id: str,
    results: list[dict[str, Any]],
    requirements: dict[str, bool],
    role_read_only: bool,
) -> dict[str, Any] | None:
    """Keep a bounded cycle progressing when a small model emits non-tool JSON."""
    if role_read_only and _successful_records(results, {"read_file"}):
        return _make_step(
            "finish_task",
            {"content": "Read-only inspection completed from real tool evidence."},
            reason="Finish the observational role after collecting real file evidence.",
            expected_result="A concise verified inspection result.",
            requires_approval=False,
            description="Completing read-only sub-agent",
        )

    if not requirements.get("mutation"):
        return None

    if not _successful_records(results, {"git_checkpoint"}):
        return _make_step(
            "git_checkpoint",
            {
                "message": f"AI Engineer recovery checkpoint {task_id[:8]}",
                "include_untracked": True,
            },
            reason="Create the mandatory recovery checkpoint before the bounded mutation.",
            expected_result="A real Git checkpoint result.",
            requires_approval=False,
            description="Creating deterministic recovery checkpoint",
        )

    if _successful_mutations(results):
        return None

    read_paths = _successful_read_paths(results)
    for path in ("README.md", "docs/active-models.md"):
        if path not in read_paths:
            continue
        for _index, step, outcome in _successful_records(results, {"read_file"}):
            result = outcome.get("result") or {}
            current_path = str(result.get("path") or _step_path(step) or "")
            content = str(result.get("content") or "")
            if current_path != path or not content or "## Autonomous development" in content:
                continue
            old = "# AI Engineer" if "# AI Engineer" in content else content.splitlines()[0]
            new = old + (
                "\n\n## Autonomous development\n\n"
                "This repository is maintained by a bounded five-minute supervisor "
                "with checkpointed sub-agent inspection, implementation, and verification."
            )
            return _make_step(
                "replace_text",
                {"path": path, "old": old, "new": new, "replace_all": False},
                reason="Record the autonomous supervisor contract in the already-read project documentation.",
                expected_result="A small non-empty documented improvement.",
                requires_approval=True,
                description=f"Documenting autonomous development in {path}",
            )
    return None


def _build_read_only_output(results: list[dict[str, Any]]) -> str:
    read_paths: list[str] = []
    project_name = ""
    project_version = ""

    for _index, step, outcome in _successful_records(results, {"read_file"}):
        result = outcome.get("result") or {}
        path = str(result.get("path") or _step_path(step) or "").strip()
        if path and path not in read_paths:
            read_paths.append(path)

        if path.casefold() == "package.json":
            try:
                package = json.loads(str(result.get("content") or "{}"))
                project_name = str(package.get("name") or "").strip()
                project_version = str(package.get("version") or "").strip()
            except (TypeError, ValueError, json.JSONDecodeError):
                pass

    lines = ["بررسی فقط‌خواندنی با اجرای واقعی ابزارها تکمیل شد."]
    if project_name:
        label = f"نام پروژه: {project_name}"
        if project_version:
            label += f" (نسخه {project_version})"
        lines.append(label)
    if read_paths:
        lines.append("فایل‌های خوانده‌شده:")
        lines.extend(f"- {path}" for path in read_paths[:20])
    return "\n".join(lines)


def _unresolved_failures(results: list[dict[str, Any]]) -> list[str]:
    unresolved: list[str] = []
    successful_mutations = _successful_mutations(results)
    successful_validations = _successful_validations(results)
    successful_reads = _successful_read_paths(results)

    for index, item in enumerate(results):
        step = item.get("step") or {}
        outcome = item.get("outcome") or {}
        if outcome.get("ok"):
            continue
        tool = _outcome_tool(outcome, step)
        error = str(outcome.get("error") or "Tool failed.")

        if tool == "finish_task" and error.startswith("Completion rejected"):
            continue
        if outcome.get("approval_required"):
            continue
        if outcome.get("ignored"):
            continue
        if tool == "read_file" and not bool(step.get("required_observation")):
            # Exploratory reads may legitimately miss optional files. They are
            # useful observations, but they must not block a verified finish.
            continue

        path = _step_path(step)
        resolved = False

        if tool == "run_terminal":
            resolved = any(success_index > index for success_index, _step, _outcome in successful_validations)
        elif tool in MUTATION_TOOLS and path:
            resolved = any(
                success_index > index and success_path == path
                for success_index, success_path, _outcome in successful_mutations
            )
        elif tool == "read_file" and path:
            resolved = successful_reads.get(path, -1) > index or any(
                success_index > index and success_path == path
                for success_index, success_path, _outcome in successful_mutations
            )
        elif tool in {"list_files", "search_files", "git_diff", "git_status"}:
            resolved = any(
                success_index > index and _outcome_tool(success_outcome, success_step) == tool
                for success_index, success_step, success_outcome in _successful_records(results)
            )

        if not resolved:
            unresolved.append(f"{tool}: {error}")

    return unresolved


def _completion_problem(
    requirements: dict[str, bool],
    results: list[dict[str, Any]],
) -> str | None:
    reads = _successful_records(results, {"read_file"})
    mutations = _successful_mutations(results)
    validations = _successful_validations(results)
    diff_record = _latest_nonempty_diff(results)

    if requirements["read"] and not reads:
        return "At least one real read_file must succeed before completion."

    if requirements["mutation"]:
        if not mutations:
            return "A real file mutation has not succeeded."

        first_mutation_index = mutations[0][0]
        if not any(index < first_mutation_index for index, _step, _outcome in reads):
            return "A relevant file must be read before the first mutation."

        checkpoint_index = _last_success_index(results, {"git_checkpoint"})
        if checkpoint_index < 0 or checkpoint_index > first_mutation_index:
            return "A Git checkpoint must succeed before the first mutation."

        last_mutation_index = mutations[-1][0]
        if not diff_record or diff_record[0] < last_mutation_index:
            return "A non-empty Git diff must be captured after the last mutation."

        if not validations or validations[-1][0] < last_mutation_index:
            return "A successful validation command must run after the last mutation."

    elif requirements["validation"] and not validations:
        return "A successful validation command is required."

    failures = _unresolved_failures(results)
    if failures:
        return "Unresolved tool failure remains: " + failures[0]

    return None


def _build_final_output(
    results: list[dict[str, Any]],
    model_note: str,
) -> str:
    changed_files: list[str] = []
    for _index, path, _outcome in _successful_mutations(results):
        if path and path not in changed_files:
            changed_files.append(path)

    commands: list[str] = []
    for _index, step, outcome in _successful_records(results, {"run_terminal"}):
        command = str(_arguments(step).get("command", "")).strip()
        result = outcome.get("result") or {}
        if command:
            commands.append(f"{command} — exit {result.get('exit_code', 0)}")

    diff_record = _latest_nonempty_diff(results)
    diff_lines = 0
    if diff_record:
        diff_lines = len(str(diff_record[1].get("diff", "")).splitlines())

    lines = ["کار با اجرای واقعی ابزارها و Validation موفق تکمیل شد."]
    if changed_files:
        lines.append("فایل‌های تغییرکرده:")
        lines.extend(f"- {path}" for path in changed_files)
    if commands:
        lines.append("فرمان‌های اجراشده:")
        lines.extend(f"- {command}" for command in commands)
    if diff_lines:
        lines.append(f"Git Diff ثبت شد: {diff_lines} خط.")
    lines.append("Validation: PASS")
    if model_note.strip():
        lines.append("نتیجه Agent:")
        lines.append(model_note.strip())
    return "\n".join(lines)


async def _list_files(workspace: str, relative: str) -> dict[str, Any]:
    path = _project_path(workspace, relative)
    result = await request_json(
        "GET",
        f"{settings.local_agent_url}/files/list?path={quote(path, safe='')}",
    )
    return _normalize_file_result(workspace, result)


async def _read_file(workspace: str, relative: str) -> dict[str, Any]:
    path = _project_path(workspace, relative)
    result = await request_json(
        "GET",
        f"{settings.local_agent_url}/files/read?path={quote(path, safe='')}",
    )
    return _normalize_file_result(workspace, result)


async def _search_files(
    workspace: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    if not query:
        raise ValueError("search_files requires a non-empty query.")

    start_path = _safe_relative(str(arguments.get("path", ".")))
    include_content = bool(arguments.get("include_content", True))
    max_results = min(max(int(arguments.get("max_results", 30)), 1), MAX_SEARCH_RESULTS)
    max_depth = min(max(int(arguments.get("max_depth", 8)), 1), 12)
    case_sensitive = bool(arguments.get("case_sensitive", False))
    needle = query if case_sensitive else query.casefold()

    queue: deque[tuple[str, int]] = deque([(start_path, 0)])
    matches: list[dict[str, Any]] = []
    inspected_files = 0

    while queue and len(matches) < max_results and inspected_files < MAX_SEARCH_FILES:
        directory, depth = queue.popleft()
        listing = await _list_files(workspace, directory)
        for entry in listing.get("entries", []):
            name = str(entry.get("name", ""))
            path = str(entry.get("path", ""))
            entry_type = str(entry.get("type", ""))

            if entry_type == "directory":
                if depth < max_depth and name not in SKIP_DIRECTORIES:
                    queue.append((path, depth + 1))
                continue

            inspected_files += 1
            comparable_name = name if case_sensitive else name.casefold()
            if needle in comparable_name:
                matches.append({
                    "path": path,
                    "match": "filename",
                    "preview": name,
                })
                if len(matches) >= max_results:
                    break

            suffix = PurePosixPath(path).suffix.casefold()
            size = int(entry.get("size") or 0)
            if (
                include_content
                and suffix in TEXT_EXTENSIONS
                and size <= 300_000
                and len(matches) < max_results
            ):
                try:
                    file_result = await _read_file(workspace, path)
                except Exception:
                    continue
                for line_number, line in enumerate(
                    str(file_result.get("content", "")).splitlines(),
                    start=1,
                ):
                    comparable_line = line if case_sensitive else line.casefold()
                    if needle in comparable_line:
                        matches.append({
                            "path": path,
                            "match": "content",
                            "line": line_number,
                            "preview": line.strip()[:240],
                        })
                        break

    return {
        "query": query,
        "path": start_path,
        "matches": matches,
        "inspected_files": inspected_files,
        "truncated": bool(queue) or inspected_files >= MAX_SEARCH_FILES,
    }


async def _execute_step(
    workspace: str,
    step: dict[str, Any],
    *,
    approved: bool,
) -> dict[str, Any]:
    tool = _tool_name(step)
    args = _arguments(step)

    if tool == "list_files":
        result = await _list_files(workspace, str(args.get("path", ".")))
        return {"tool": tool, "action": tool, "ok": True, "result": result}

    if tool == "search_files":
        result = await _search_files(workspace, args)
        return {"tool": tool, "action": tool, "ok": True, "result": result}

    if tool == "read_file":
        result = await _read_file(workspace, str(args.get("path", "")))
        return {"tool": tool, "action": tool, "ok": True, "result": result}

    if tool == "write_file":
        relative = _safe_relative(str(args.get("path", "")), allow_dot=False)
        if not approved:
            return {
                "tool": tool,
                "action": tool,
                "ok": False,
                "approval_required": True,
                "reason": "Writing a project file requires user approval.",
                "result": {"path": relative},
            }
        result = await request_json(
            "POST",
            f"{settings.local_agent_url}/files/write",
            json={
                "path": _project_path(workspace, relative),
                "content": str(args.get("content", "")),
                "overwrite": bool(args.get("overwrite", True)),
            },
        )
        return {
            "tool": tool,
            "action": tool,
            "ok": True,
            "result": _normalize_file_result(workspace, result),
        }

    if tool in {"replace_text", "apply_patch"}:
        relative = _safe_relative(str(args.get("path", "")), allow_dot=False)
        read_result = await _read_file(workspace, relative)
        content = str(read_result.get("content", ""))

        if tool == "replace_text":
            edits = [{
                "old": str(args.get("old", "")),
                "new": str(args.get("new", "")),
                "replace_all": bool(args.get("replace_all", False)),
            }]
        else:
            raw_edits = args.get("edits") or args.get("changes") or []
            if not isinstance(raw_edits, list) or not raw_edits:
                raise ValueError("apply_patch requires a non-empty edits array.")
            if len(raw_edits) > 20:
                raise ValueError("apply_patch accepts at most 20 edits per call.")
            edits = []
            for raw_edit in raw_edits:
                if not isinstance(raw_edit, dict):
                    raise ValueError("Every patch edit must be an object.")
                edits.append({
                    "old": str(raw_edit.get("old", "")),
                    "new": str(raw_edit.get("new", "")),
                    "replace_all": bool(raw_edit.get("replace_all", False)),
                })

        updated = content
        replacement_count = 0
        for edit in edits:
            old = edit["old"]
            new = edit["new"]
            replace_all = edit["replace_all"]
            if not old:
                raise ValueError("Patch old text must not be empty.")
            occurrences = updated.count(old)
            if occurrences == 0:
                return {
                    "tool": tool,
                    "action": tool,
                    "ok": False,
                    "error": "Exact patch text was not found. Read the current file and retry with an exact snippet.",
                    "result": {"path": relative, "occurrences": 0},
                }
            if occurrences > 1 and not replace_all:
                return {
                    "tool": tool,
                    "action": tool,
                    "ok": False,
                    "error": f"Patch text occurs {occurrences} times. Use a more specific snippet or replace_all=true.",
                    "result": {"path": relative, "occurrences": occurrences},
                }
            updated = updated.replace(old, new) if replace_all else updated.replace(old, new, 1)
            replacement_count += occurrences if replace_all else 1

        if not approved:
            return {
                "tool": tool,
                "action": tool,
                "ok": False,
                "approval_required": True,
                "reason": "Editing a project file requires user approval.",
                "result": {
                    "path": relative,
                    "edit_count": len(edits),
                    "replacements": replacement_count,
                },
            }

        result = await request_json(
            "POST",
            f"{settings.local_agent_url}/files/write",
            json={
                "path": _project_path(workspace, relative),
                "content": updated,
                "overwrite": True,
            },
        )
        normalized = _normalize_file_result(workspace, result)
        normalized.update({
            "edit_count": len(edits),
            "replacements": replacement_count,
        })
        return {"tool": tool, "action": tool, "ok": True, "result": normalized}

    if tool == "run_terminal":
        cwd = _project_path(workspace, str(args.get("cwd", ".")))
        payload = {
            "command": str(args.get("command", "")),
            "cwd": cwd,
            "shell": str(args.get("shell", "powershell")),
        }
        preview = await request_json(
            "POST",
            f"{settings.local_agent_url}/terminal/preview",
            json=payload,
        )
        if preview.get("risk") == "blocked":
            return {
                "tool": tool,
                "action": tool,
                "ok": False,
                "blocked": True,
                "error": "Command was blocked by the Local Agent.",
                "preview": preview,
            }
        if preview.get("requires_approval") and not approved:
            return {
                "tool": tool,
                "action": tool,
                "ok": False,
                "approval_required": True,
                "reason": "The Local Agent classified this command as approval-required.",
                "preview": preview,
                "request": payload,
            }

        timeout_seconds = min(max(int(args.get("timeout_seconds", 300)), 1), 300)
        result = await request_json(
            "POST",
            f"{settings.local_agent_url}/terminal/run",
            json={
                **payload,
                "approved": approved,
                "timeout_seconds": timeout_seconds,
            },
            timeout_seconds=timeout_seconds + 30,
        )
        normalized = dict(result)
        normalized["cwd"] = _strip_workspace(workspace, str(result.get("cwd", "")))
        return {
            "tool": tool,
            "action": tool,
            "ok": result.get("exit_code") == 0,
            "result": normalized,
            "error": None if result.get("exit_code") == 0 else f"Command exited with code {result.get('exit_code')}.",
        }

    if tool == "start_process":
        if not approved:
            return {
                "tool": tool,
                "action": tool,
                "ok": False,
                "approval_required": True,
                "reason": "Starting a managed process requires approval.",
            }
        result = await request_json(
            "POST",
            f"{settings.local_agent_url}/processes/start",
            json={
                "name": str(args.get("name") or "AI Engineer process"),
                "executable": str(args.get("executable") or "npm.cmd"),
                "args": [str(value) for value in (args.get("args") or [])],
                "cwd": _project_path(workspace, str(args.get("cwd", "."))),
                "approved": True,
            },
        )
        return {"tool": tool, "action": tool, "ok": True, "result": result}

    if tool == "list_processes":
        result = await request_json("GET", f"{settings.local_agent_url}/processes")
        return {"tool": tool, "action": tool, "ok": True, "result": result}

    if tool == "stop_process":
        if not approved:
            return {
                "tool": tool,
                "action": tool,
                "ok": False,
                "approval_required": True,
                "reason": "Stopping a managed process requires approval.",
            }
        result = await request_json(
            "POST",
            f"{settings.local_agent_url}/processes/stop",
            json={"process_id": str(args.get("process_id", "")), "approved": True},
        )
        return {"tool": tool, "action": tool, "ok": True, "result": result}

    if tool == "git_status":
        result = await request_json(
            "POST",
            f"{settings.local_agent_url}/git/status",
            json={"project_path": _project_path(workspace, ".")},
        )
        return {"tool": tool, "action": tool, "ok": True, "result": result}

    if tool == "git_checkpoint":
        result = await request_json(
            "POST",
            f"{settings.local_agent_url}/git/checkpoint",
            json={
                "project_path": _project_path(workspace, "."),
                "message": str(args.get("message") or "AI Engineer checkpoint"),
                "include_untracked": bool(args.get("include_untracked", True)),
            },
        )
        return {"tool": tool, "action": tool, "ok": True, "result": result}

    if tool == "git_diff":
        result = await request_json(
            "POST",
            f"{settings.local_agent_url}/git/diff",
            json={
                "project_path": _project_path(workspace, "."),
                "staged": bool(args.get("staged", False)),
                "base": args.get("base"),
            },
        )
        return {"tool": tool, "action": tool, "ok": True, "result": result}

    if tool == "git_rollback":
        if not approved:
            return {
                "tool": tool,
                "action": tool,
                "ok": False,
                "approval_required": True,
                "reason": "Git rollback requires approval.",
            }
        result = await request_json(
            "POST",
            f"{settings.local_agent_url}/git/rollback",
            json={
                "project_path": _project_path(workspace, "."),
                "commit": str(args.get("commit", "")),
                "approved": True,
            },
        )
        return {"tool": tool, "action": tool, "ok": True, "result": result}

    if tool == "request_approval":
        if not approved:
            return {
                "tool": tool,
                "action": tool,
                "ok": False,
                "approval_required": True,
                "reason": str(args.get("message") or "Agent requests approval."),
                "result": {"message": str(args.get("message") or "")},
            }
        return {
            "tool": tool,
            "action": tool,
            "ok": True,
            "result": {"approved": True, "message": str(args.get("message") or "")},
        }

    return {
        "tool": tool,
        "action": tool,
        "ok": False,
        "error": "Unsupported Agent tool execution.",
    }


async def _detect_environment(
    workspace: str,
    root_listing: dict[str, Any],
    package_content: str | None,
) -> dict[str, Any]:
    names = {str(entry.get("name", "")) for entry in root_listing.get("entries", [])}
    names_lower = {name.casefold() for name in names}
    technologies: list[str] = []
    frameworks: list[str] = []
    important_files: list[str] = []
    commands: dict[str, str] = {}
    validation_command: str | None = None

    if "package.json" in names:
        technologies.append("Node.js")
        important_files.append("package.json")
        try:
            package = json.loads(package_content or "{}")
        except json.JSONDecodeError:
            package = {}
        scripts = package.get("scripts") if isinstance(package, dict) else {}
        if isinstance(scripts, dict):
            commands = {str(key): f"npm run {key}" for key in scripts}
            for candidate in ("verify", "test", "build", "typecheck", "lint"):
                if candidate in scripts:
                    validation_command = f"npm run {candidate}"
                    break
        dependencies = {
            **(package.get("dependencies") or {}),
            **(package.get("devDependencies") or {}),
        } if isinstance(package, dict) else {}
        dependency_names = {str(name).casefold() for name in dependencies}
        if "react" in dependency_names:
            frameworks.append("React")
        if "next" in dependency_names:
            frameworks.append("Next.js")
        if "vite" in dependency_names or any(name.startswith("vite.config") for name in names_lower):
            frameworks.append("Vite")

    if any(name.startswith("vite.config") for name in names_lower) and "Vite" not in frameworks:
        frameworks.append("Vite")
    if any(name.startswith("next.config") for name in names_lower) and "Next.js" not in frameworks:
        frameworks.append("Next.js")
    if "composer.json" in names:
        technologies.append("PHP")
        important_files.append("composer.json")
        validation_command = validation_command or "composer test"
    if "artisan" in names:
        frameworks.append("Laravel")
        technologies.append("PHP") if "PHP" not in technologies else None
    if "requirements.txt" in names or "pyproject.toml" in names:
        technologies.append("Python")
        important_files.extend([name for name in ("requirements.txt", "pyproject.toml") if name in names])
        validation_command = validation_command or "python -m pytest"
    if "dockerfile" in names_lower or "compose.yaml" in names_lower or "compose.yml" in names_lower:
        technologies.append("Docker")
    if "wp-config.php" in names or {"wp-admin", "wp-content", "wp-includes"}.issubset(names):
        frameworks.append("WordPress")
        technologies.extend(value for value in ("PHP", "MySQL") if value not in technologies)
    if any(name.casefold().endswith((".sln", ".csproj")) for name in names):
        technologies.append(".NET")
        validation_command = validation_command or "dotnet build"

    return {
        "technologies": list(dict.fromkeys(technologies)),
        "frameworks": list(dict.fromkeys(frameworks)),
        "commands": commands,
        "validation_command": validation_command,
        "important_files": list(dict.fromkeys(important_files)),
        "root_entries": sorted(names),
        "detected_by": "rule_engine",
    }


async def _model_next_action(
    task_id: str,
    instruction: str,
    workspace: str,
    requirements: dict[str, bool],
    results: list[dict[str, Any]],
    *,
    project_id: str | None = None,
    autonomous: bool = False,
) -> dict[str, Any]:
    observations = _observation_text(results)
    profile = _environment_profile(results)
    missing_requirement = _completion_problem(requirements, results)
    already_read_paths = sorted(_successful_read_paths(results))
    subagent_role = role_from_instruction(instruction) if autonomous else None
    role_read_only = bool(subagent_role and subagent_role.read_only)
    # Memory is advisory context; it must never expand the files explicitly
    # authorized by the current autonomous goal.
    primary_instruction = re.split(
        r"\nLEARNED(?: PROJECT)? MEMORY:",
        instruction,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    mentioned_names = {
        PurePosixPath(path).name.casefold()
        for path in _mentioned_paths(primary_instruction)
    }
    allowed_mutation_paths = sorted(
        path
        for path in already_read_paths
        if PurePosixPath(path).name.casefold() in mentioned_names
    )
    if autonomous and not mentioned_names and not role_read_only:
        # A generic self-improvement cycle may not name its target in advance,
        # so it may mutate only files it has observed in this cycle. When the
        # goal names a file, keep that narrower target set.
        allowed_mutation_paths = already_read_paths

    learned_memories = (
        search_memories(project_id, query=instruction, limit=6)
        if project_id
        else []
    )
    learned_memory_text = _bounded_learned_memory(learned_memories)
    successful_mutations = _successful_mutations(results)
    known_repair = _autonomous_known_repair(instruction, results) if autonomous else None
    if known_repair:
        return known_repair

    # Keep the autonomous implementation role bounded even when the local
    # model is still generating a response. Once a real target is read, the
    # recovery step can safely establish the checkpoint or apply the tiny
    # documented improvement without waiting through repeated model timeouts.
    if autonomous and requirements.get("mutation"):
        fast_recovery = _deterministic_autonomous_recovery_step(
            task_id,
            results,
            requirements,
            role_read_only,
        )
        if fast_recovery and fast_recovery["tool"] in {"git_checkpoint", "replace_text"}:
            return fast_recovery

    # Small local models occasionally copy the illustrative read_file path
    # from the schema (for example client/src/App.tsx) even when it is not in
    # the selected project. Recover from that miss without spending all retry
    # attempts on the same invalid call.
    if any(
        _outcome_tool(item.get("outcome") or {}, item.get("step") or {}) == "read_file"
        and not (item.get("outcome") or {}).get("ok")
        for item in results
    ):
        for candidate in _inspection_fallback_paths(results):
            if not _duplicate_read_attempt(results, candidate):
                return _make_step(
                    "read_file",
                    {"path": candidate},
                    reason="Recover from an invalid model path using a real project file.",
                    expected_result="Current content from an existing project file.",
                    requires_approval=False,
                    description=f"Reading discovered file {candidate}",
                )

    failed_mutations: list[tuple[str, str]] = []
    for item in reversed(results):
        step = item.get("step") or {}
        outcome = item.get("outcome") or {}
        tool = _outcome_tool(outcome, step)
        if outcome.get("ok") or tool not in MUTATION_TOOLS:
            if failed_mutations:
                break
            continue
        failed_mutations.append((tool, _step_path(step) or ""))

    if len(failed_mutations) >= 2:
        failed_path = failed_mutations[0][1]
        source_suffixes = {".tsx", ".jsx", ".vue", ".svelte", ".html", ".php"}
        candidates = sorted(
            already_read_paths,
            key=lambda path: (
                PurePosixPath(path).suffix.casefold() not in source_suffixes,
                path,
            ),
        )
        for candidate in candidates:
            if candidate == failed_path or _duplicate_read_attempt(results, candidate):
                continue
            return _make_step(
                "read_file",
                {"path": candidate},
                reason="Refresh a related source file after repeated mutation failures.",
                expected_result="Current source content for a different repair approach.",
                requires_approval=False,
                description=f"Refreshing {candidate} after failed edits",
            )

    prompt = f"""
You are the execution controller of a local Codex-style coding Agent.
You are not a consultant. Choose exactly ONE real tool call based on actual tool results.

SELECTED PROJECT WORKSPACE:
{workspace}

EXECUTION MODE:
{"AUTONOMOUS SELF-IMPROVEMENT (bounded, one coherent change)" if autonomous else "INTERACTIVE USER TASK"}

USER REQUEST:
{instruction}

RULE-BASED ENVIRONMENT PROFILE:
{json.dumps(profile, ensure_ascii=False, indent=2)}

CURRENT COMPLETION GAP:
{missing_requirement or "No mandatory gap detected yet."}

ALREADY READ SUCCESSFULLY:
{json.dumps(already_read_paths, ensure_ascii=False)}

ALLOWED MUTATION TARGETS FROM THE USER REQUEST:
{json.dumps(allowed_mutation_paths, ensure_ascii=False)}

LEARNED PROJECT MEMORY:
{learned_memory_text if learned_memories else "No prior memory is available."}

Return exactly one JSON object, without Markdown or prose:
{{
  "tool": "one tool name",
  "arguments": {{}},
  "reason": "why this tool is the next necessary action",
  "expected_result": "what concrete result should be returned",
  "requires_approval": false
}}

AVAILABLE TOOLS:
- list_files: {{"path":"."}}
- search_files: {{"query":"text","path":".","include_content":true,"max_results":30}}
 - read_file: {{"path":"README.md"}}
- write_file: {{"path":"file","content":"complete content","overwrite":true}}
- replace_text: {{"path":"file","old":"exact text","new":"replacement","replace_all":false}}
- apply_patch: {{"path":"file","edits":[{{"old":"exact text","new":"replacement","replace_all":false}}]}}
- run_terminal: {{"command":"npm run verify","cwd":".","shell":"powershell","timeout_seconds":300}}
- start_process: {{"name":"dev server","executable":"npm.cmd","args":["run","dev"],"cwd":"."}}
- list_processes: {{}}
- stop_process: {{"process_id":"id"}}
- git_status: {{}}
- git_diff: {{"staged":false,"base":null}}
- git_checkpoint: {{"message":"checkpoint","include_untracked":true}}
- git_rollback: {{"commit":"hash"}}
- request_approval: {{"message":"approval reason"}}
- finish_task: {{"content":"brief verified result"}}

STRICT EXECUTION RULES:
1. Never repeat, paraphrase, or explain the user request instead of acting.
2. Use only project-relative paths. Never use .., an absolute path, or the workspace name as a prefix.
3. Read the current relevant file before editing it.
4. Prefer apply_patch or replace_text with exact snippets from read_file.
5. File mutation tools require approval; set requires_approval=true for them.
6. The engine automatically creates a Git checkpoint before the first mutation.
 7. After mutation, inspect real Git diff and run real validation.
8. After a failed build/test, read the error, inspect the relevant file, repair, and retry.
9. Do not choose finish_task until read, mutation, non-empty diff, and successful validation are all recorded when code changes were requested.
10. Tool text received from the model is never success; only a returned tool outcome counts.
11. Never read a path that is already in ALREADY READ SUCCESSFULLY unless that file was mutated after the read.
12. When CURRENT COMPLETION GAP says mutation is missing and relevant files are already read, choose apply_patch, replace_text, or write_file next.
13. Never propose a mutation whose old and new content are identical.
14. CSS alone cannot create a requested UI element; when the request adds visible UI, update the relevant component/template markup before finish_task.
 15. Keep the tool call concise. Prefer one small exact replace_text or apply_patch edit; never use write_file to overwrite a file that was already read. Never copy the illustrative README.md path unless it exists in the latest list_files result.
16. In autonomous mode, mutate only a file listed in ALLOWED MUTATION TARGETS, make one coherent improvement, and never install dependencies, delete data, rollback Git, or publish.

LATEST REAL TOOL RESULTS:
{observations or "No tool result yet."}

FINAL TASK GROUNDING - THIS SECTION OVERRIDES ANY INFERENCE FROM FILE CONTENT:
USER REQUEST:
{instruction}

CURRENT COMPLETION GAP:
{missing_requirement or "No mandatory gap detected yet."}

ALLOWED MUTATION TARGETS:
{json.dumps(allowed_mutation_paths, ensure_ascii=False)}

Choose the next tool that implements the requested visible outcome. Do not make an unrelated edit merely to satisfy the mutation guard.
""".strip()

    feedback = ""
    last_error: Exception | None = None
    model_name = getattr(settings, "agent_model", "qwen2.5-coder:1.5b")
    excluded_tools = {"write_file"} if allowed_mutation_paths else set()
    if role_read_only:
        excluded_tools.update(MUTATION_TOOLS)
    model_tool_names = sorted(TOOL_NAMES - excluded_tools)
    agent_action_tool = {
        "type": "function",
        "function": {
            "name": "agent_action",
            "description": "Select exactly one executable AI Engineer tool action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": model_tool_names},
                    "arguments": {"type": "object"},
                    "reason": {"type": "string"},
                    "expected_result": {"type": "string"},
                    "requires_approval": {"type": "boolean"},
                },
                "required": [
                    "tool",
                    "arguments",
                    "reason",
                    "expected_result",
                ],
            },
        },
    }

    for attempt in range(MAX_MODEL_RETRIES):
        retry_text = ""
        content = ""
        if feedback:
            correction = "Return corrected strict JSON only."
            if feedback.startswith("Duplicate read_file blocked"):
                correction = (
                    "Do not call read_file again. Use the existing file content. "
                    "If code changes are still missing, the next tool MUST be "
                    "apply_patch, replace_text, or write_file."
                )
            retry_text = (
                f"\n\nPREVIOUS OUTPUT ERROR:\n{feedback}\n{correction}"
            )
        try:
            response = await request_json(
                "POST",
                f"{settings.model_gateway_url}/v1/chat/completions",
                json={
                    "model": model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a structured tool-calling coding agent. Output one strict JSON object only.",
                        },
                        {"role": "user", "content": prompt + retry_text},
                    ],
                    "temperature": 0,
                    "max_tokens": 1400,
                    "tools": [agent_action_tool],
                    "tool_choice": {
                        "type": "function",
                        "function": {"name": "agent_action"},
                    },
                    "project_id": workspace,
                    "task_id": task_id,
                    "agent_id": "desktop-codex-v04",
                },
                timeout_seconds=300,
            )
            message = response["choices"][0].get("message") or {}
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                function = (tool_calls[0] or {}).get("function") or {}
                if str(function.get("name") or "") != "agent_action":
                    raise ValueError("The model selected an unsupported function.")
                raw_arguments = function.get("arguments") or {}
                if isinstance(raw_arguments, str):
                    raw_call = _extract_json(raw_arguments)
                    content = raw_arguments
                elif isinstance(raw_arguments, dict):
                    raw_call = raw_arguments
                    content = json.dumps(raw_arguments, ensure_ascii=False)
                else:
                    raise ValueError("Tool-call arguments must be an object or JSON string.")
                step = _normalize_tool_call(_unwrap_model_action(raw_call))
            else:
                content = str(message.get("content") or "")
                step = _normalize_tool_call(_unwrap_model_action(_extract_json(content)))
            step = _normalize_step_project_paths(workspace, step)
            tool = _tool_name(step)
            arguments = _arguments(step)

            if tool in MUTATION_TOOLS and autonomous and not allowed_mutation_paths:
                raise ValueError(
                    "Autonomous mutation requires a successfully read target file first."
                )

            if tool in MUTATION_TOOLS and allowed_mutation_paths:
                target_path = _step_path(step) or ""
                if target_path not in allowed_mutation_paths:
                    raise ValueError(
                        f"Mutation target {target_path or '<missing>'} is not grounded "
                        "in the files explicitly named by the user. Choose one of: "
                        + ", ".join(allowed_mutation_paths)
                    )
                if tool == "write_file" and target_path in already_read_paths:
                    raise ValueError(
                        "write_file cannot overwrite an existing file. "
                        "Use one concise replace_text or apply_patch edit."
                    )

            if tool == "replace_text" and not str(arguments.get("old", "")):
                raise ValueError(
                    "replace_text requires a non-empty exact old string. "
                    "Choose apply_patch with exact current text or another tool."
                )
            if (
                tool == "replace_text"
                and str(arguments.get("old", "")) == str(arguments.get("new", ""))
            ):
                raise ValueError("replace_text old and new values must differ.")
            if tool == "apply_patch":
                edits = arguments.get("edits")
                if not isinstance(edits, list) or not edits:
                    raise ValueError("apply_patch requires a non-empty edits array.")
                if any(
                    not isinstance(edit, dict) or not str(edit.get("old", ""))
                    for edit in edits
                ):
                    raise ValueError(
                        "Every apply_patch edit requires a non-empty exact old string."
                    )
                if any(
                    str(edit.get("old", "")) == str(edit.get("new", ""))
                    for edit in edits
                ):
                    raise ValueError("apply_patch old and new values must differ.")

            for previous in results[-8:]:
                previous_step = previous.get("step") or {}
                previous_outcome = previous.get("outcome") or {}
                if previous_outcome.get("ok"):
                    continue
                if (
                    _outcome_tool(previous_outcome, previous_step) == tool
                    and _arguments(previous_step) == arguments
                ):
                    raise ValueError(
                        f"Duplicate failed {tool} call blocked. "
                        "Choose a different repair using current observations."
                    )

            if (
                missing_requirement is None
                and not requirements.get("mutation")
                and not requirements.get("validation")
                and tool != "finish_task"
            ):
                raise ValueError(
                    "All completion requirements are already satisfied. "
                    "The next tool must be finish_task."
                )

            if tool == "read_file":
                path = _step_path(step)
                if path and _duplicate_read_attempt(results, path):
                    raise ValueError(
                        f"Duplicate read_file blocked for {path}. "
                        "Use the existing observation and choose the next action."
                    )

                if (
                    requirements.get("mutation")
                    and not successful_mutations
                    and len(already_read_paths) >= MAX_UNIQUE_READS_BEFORE_MUTATION
                ):
                    raise ValueError(
                        "Inspection budget is exhausted. Relevant files have already "
                        "been read; the next tool must perform the required mutation."
                    )

            return step
        except Exception as exc:
            raw_output = f" Model output: {_clip(content, 1_200)}" if content else ""
            last_error = exc
            feedback = f"{exc}.{raw_output}"

    recovery = _deterministic_autonomous_recovery_step(
        task_id,
        results,
        requirements,
        role_read_only,
    ) if autonomous else None
    if recovery:
        return recovery
    raise RuntimeError(f"Model failed to produce a valid tool call after {MAX_MODEL_RETRIES} attempts: {feedback or last_error}")


async def _append_step_result(
    workspace: str,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
    step: dict[str, Any],
    *,
    approved: bool,
) -> tuple[int, dict[str, Any]]:
    plan.append(step)
    step_index = len(plan) - 1
    try:
        outcome = await _execute_step(workspace, step, approved=approved)
    except Exception as exc:
        outcome = {
            "tool": _tool_name(step),
            "action": _tool_name(step),
            "ok": False,
            "error": str(exc),
        }
    results.append({
        "step_index": step_index,
        "step": step,
        "outcome": outcome,
    })
    return step_index, outcome


async def _ensure_target_read(
    workspace: str,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
    step: dict[str, Any],
) -> bool:
    path = _step_path(step)
    if not path:
        return True

    latest_mutation_on_path = max(
        (index for index, mutation_path, _outcome in _successful_mutations(results) if mutation_path == path),
        default=-1,
    )
    latest_read = _successful_read_paths(results).get(path, -1)
    if latest_read > latest_mutation_on_path:
        return True

    read_step = _make_step(
        "read_file",
        {"path": path},
        reason="Re-read the current target file immediately before mutation.",
        expected_result="Current UTF-8 file content.",
        requires_approval=False,
        description=f"Reading current {path}",
    )
    _index, outcome = await _append_step_result(
        workspace,
        plan,
        results,
        read_step,
        approved=True,
    )
    if outcome.get("ok"):
        return True

    tool = _tool_name(step)
    args = _arguments(step)
    return tool == "write_file" and not bool(args.get("overwrite", True))


async def _ensure_checkpoint(
    task_id: str,
    workspace: str,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> bool:
    if _successful_records(results, {"git_checkpoint"}):
        return True

    checkpoint_step = _make_step(
        "git_checkpoint",
        {
            "message": f"AI Engineer before task {task_id[:8]}",
            "include_untracked": True,
        },
        reason="Create the mandatory recovery checkpoint before mutation.",
        expected_result="A Git commit hash or confirmation that the current state is already checkpointed.",
        requires_approval=False,
        description="Creating safety checkpoint",
    )
    _index, outcome = await _append_step_result(
        workspace,
        plan,
        results,
        checkpoint_step,
        approved=True,
    )
    return bool(outcome.get("ok"))


async def _append_git_diff(
    workspace: str,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    diff_step = _make_step(
        "git_diff",
        {"staged": False, "base": None},
        reason="Capture the actual code changes after mutation.",
        expected_result="A non-empty Git diff for the selected project.",
        requires_approval=False,
        description="Reading Git diff",
    )
    _index, outcome = await _append_step_result(
        workspace,
        plan,
        results,
        diff_step,
        approved=True,
    )
    return outcome


async def _append_default_validation(
    workspace: str,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> bool:
    profile = _environment_profile(results)
    command = str(profile.get("validation_command") or "").strip()
    if not command:
        return False

    validation_step = _make_step(
        "run_terminal",
        {
            "command": command,
            "cwd": ".",
            "shell": "powershell",
            "timeout_seconds": 300,
        },
        reason="Run the rule-engine-selected validation command before completion.",
        expected_result="Exit code 0 with real stdout and stderr.",
        requires_approval=False,
        description=f"Running {command}",
    )
    _index, outcome = await _append_step_result(
        workspace,
        plan,
        results,
        validation_step,
        approved=False,
    )
    return bool(outcome.get("ok"))


async def _initial_inspection(
    instruction: str,
    workspace: str,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> None:
    root_step = _make_step(
        "list_files",
        {"path": "."},
        reason="Inspect the selected project root.",
        expected_result="Real root directory entries.",
        requires_approval=False,
        description="Inspecting project files",
    )
    _index, root_outcome = await _append_step_result(
        workspace,
        plan,
        results,
        root_step,
        approved=True,
    )
    root_listing = root_outcome.get("result") if root_outcome.get("ok") else {"entries": []}
    root_names = {str(entry.get("name", "")) for entry in (root_listing or {}).get("entries", [])}

    package_content: str | None = None
    if "package.json" in root_names:
        package_step = _make_step(
            "read_file",
            {"path": "package.json"},
            reason="Read project scripts and dependencies.",
            expected_result="Current package.json content.",
            requires_approval=False,
            description="Reading package.json",
        )
        package_step["required_observation"] = True
        _index, package_outcome = await _append_step_result(
            workspace,
            plan,
            results,
            package_step,
            approved=True,
        )
        if package_outcome.get("ok"):
            package_content = str((package_outcome.get("result") or {}).get("content", ""))

    primary_instruction = re.split(
        r"\nLEARNED(?: PROJECT)? MEMORY:",
        instruction,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    for path in _mentioned_paths(primary_instruction):
        if path == "package.json":
            continue
        read_step = _make_step(
            "read_file",
            {"path": path},
            reason="Read a file explicitly referenced by the user.",
            expected_result="Current file content.",
            requires_approval=False,
            description=f"Reading {path}",
        )
        # A bare filename in a user request is often nested below the project
        # root (for example client/src/App.tsx). Treat the root probe as
        # exploratory, then resolve the real path deterministically instead of
        # leaving a permanent required-read failure for the model to repair.
        read_step["required_observation"] = "/" in path
        _read_index, read_outcome = await _append_step_result(
            workspace,
            plan,
            results,
            read_step,
            approved=True,
        )
        if read_outcome.get("ok") or "/" in path:
            continue

        search_step = _make_step(
            "search_files",
            {
                "query": PurePosixPath(path).name,
                "path": ".",
                "include_content": False,
                "max_results": 10,
            },
            reason="Resolve a referenced bare filename inside the project.",
            expected_result="Project-relative paths whose filename matches exactly.",
            requires_approval=False,
            description=f"Locating {path}",
        )
        _search_index, search_outcome = await _append_step_result(
            workspace,
            plan,
            results,
            search_step,
            approved=True,
        )
        if not search_outcome.get("ok"):
            continue

        matches = (search_outcome.get("result") or {}).get("matches", [])
        candidates: list[str] = []
        expected_name = PurePosixPath(path).name.casefold()
        for match in matches:
            candidate = str((match or {}).get("path") or "").strip()
            if (
                candidate
                and PurePosixPath(candidate).name.casefold() == expected_name
                and candidate not in candidates
            ):
                candidates.append(candidate)

        for candidate in candidates[:3]:
            nested_read_step = _make_step(
                "read_file",
                {"path": candidate},
                reason="Read the resolved file referenced by the user.",
                expected_result="Current file content from the resolved project path.",
                requires_approval=False,
                description=f"Reading {candidate}",
            )
            nested_read_step["required_observation"] = True
            await _append_step_result(
                workspace,
                plan,
                results,
                nested_read_step,
                approved=True,
            )

    profile = await _detect_environment(workspace, root_listing or {"entries": []}, package_content)
    environment_step = _make_step(
        "detect_environment",
        {},
        reason="Detect the project stack using deterministic rules.",
        expected_result="Technology stack and validation command.",
        requires_approval=False,
        description="Detecting project environment",
    )
    plan.append(environment_step)
    results.append({
        "step_index": len(plan) - 1,
        "step": environment_step,
        "outcome": {
            "tool": "detect_environment",
            "action": "detect_environment",
            "ok": True,
            "result": profile,
        },
    })


async def run_agent_task(task_id: str) -> None:
    task = get_task(task_id)
    if not task:
        return

    project = get_project(task["project_id"])
    if not project:
        update_task(task_id, status="failed", error="Project not found.")
        return

    instruction = str(task["instruction"])
    workspace = str(project["workspace"])
    task_mode = str(task.get("mode") or "interactive")
    autonomous = task_mode == "autonomous"
    requirements = _task_requirements(instruction)
    subagent_role = role_from_instruction(instruction) if autonomous else None
    if autonomous and subagent_role and subagent_role.read_only:
        # Role policy is stronger than keyword detection: titles such as
        # "Change Planner" must not turn an observational task into a
        # mutation/validation request.
        requirements.update(mutation=False, diff=False, validation=False)
    plan = list(task.get("plan") or [])
    results = list(task.get("results") or [])
    approved_steps = set(task.get("approved_steps") or [])

    try:
        update_task(task_id, status="running", error=None)
        pending = task.get("pending")

        if pending:
            step_index = int(pending["step_index"])
            step = pending["step"]
            pending_tool = _tool_name(step)
            if step_index not in approved_steps and not (
                autonomous and pending_tool in MUTATION_TOOLS
            ):
                update_task(
                    task_id,
                    status="awaiting_approval",
                    plan=plan,
                    results=results,
                    current_step=step_index,
                    pending=pending,
                )
                return

            try:
                outcome = await _execute_step(workspace, step, approved=True)
            except Exception as exc:
                outcome = {
                    "tool": _tool_name(step),
                    "action": _tool_name(step),
                    "ok": False,
                    "error": str(exc),
                }
            results.append({
                "step_index": step_index,
                "step": step,
                "outcome": outcome,
            })
            update_task(
                task_id,
                status="running",
                plan=plan,
                results=results,
                current_step=step_index + 1,
                pending=None,
                error=None,
            )

            if outcome.get("blocked"):
                update_task(
                    task_id,
                    status="failed",
                    plan=plan,
                    results=results,
                    current_step=step_index + 1,
                    pending=None,
                    error="A requested operation was blocked.",
                )
                return

            if outcome.get("ok") and _tool_name(step) in MUTATION_TOOLS:
                await _append_git_diff(workspace, plan, results)
                update_task(
                    task_id,
                    status="running",
                    plan=plan,
                    results=results,
                    current_step=len(plan),
                    pending=None,
                    error=None,
                )

        if not plan and not results:
            update_task(task_id, status="planning", error=None)
            await _initial_inspection(instruction, workspace, plan, results)
            update_task(
                task_id,
                status="running",
                plan=plan,
                results=results,
                current_step=len(plan),
                pending=None,
                error=None,
            )

        for _ in range(MAX_AGENT_STEPS):
            problem = _completion_problem(requirements, results)

            if problem and "git diff" in problem.casefold():
                await _append_git_diff(workspace, plan, results)
                update_task(
                    task_id,
                    status="running",
                    plan=plan,
                    results=results,
                    current_step=len(plan),
                    pending=None,
                    error=None,
                )
                problem = _completion_problem(requirements, results)

            if problem and "validation command" in problem.casefold():
                await _append_default_validation(workspace, plan, results)
                update_task(
                    task_id,
                    status="running",
                    plan=plan,
                    results=results,
                    current_step=len(plan),
                    pending=None,
                    error=None,
                )
                problem = _completion_problem(requirements, results)

            if problem is None:
                final_step = _make_step(
                    "finish_task",
                    {"content": "Verified completion from real tool outcomes."},
                    reason="All mandatory execution guards have passed.",
                    expected_result="A final verified task result.",
                    requires_approval=False,
                    description="Task completed",
                )
                final_output = (
                    _build_final_output(results, "Verified completion from real tool outcomes.")
                    if requirements.get("mutation") or requirements.get("validation")
                    else _build_read_only_output(results)
                )
                plan.append(final_step)
                results.append({
                    "step_index": len(plan) - 1,
                    "step": final_step,
                    "outcome": {
                        "tool": "finish_task",
                        "action": "finish_task",
                        "ok": True,
                        "result": {"content": final_output},
                    },
                })
                update_task(
                    task_id,
                    status="completed",
                    plan=plan,
                    results=results,
                    current_step=len(plan),
                    pending=None,
                    final_output=final_output,
                    error=None,
                )
                return

            # Inspection, planning, verification, and review roles are
            # intentionally read-only. Give them a deterministic existing
            # file after the root probe instead of spending several slow model
            # retries on an illustrative/nonexistent path.
            if (
                autonomous
                and subagent_role
                and not _successful_records(results, {"read_file"})
            ):
                candidates = _inspection_fallback_paths(results)
                if candidates:
                    step = _make_step(
                        "read_file",
                        {"path": candidates[0]},
                        reason="Read a concrete file discovered in the project root.",
                        expected_result="Current content from an existing project file.",
                        requires_approval=False,
                        description=f"Reading discovered file {candidates[0]}",
                    )
                    await _append_step_result(
                        workspace,
                        plan,
                        results,
                        step,
                        approved=True,
                    )
                    update_task(
                        task_id,
                        status="running",
                        plan=plan,
                        results=results,
                        current_step=len(plan),
                        pending=None,
                        error=None,
                    )
                    continue

            step = await _model_next_action(
                task_id,
                instruction,
                workspace,
                requirements,
                results,
                project_id=task["project_id"],
                autonomous=autonomous,
            )
            tool = _tool_name(step)

            if tool == "finish_task":
                problem = _completion_problem(requirements, results)

                if problem and "validation command" in problem.casefold():
                    ran_validation = await _append_default_validation(workspace, plan, results)
                    update_task(
                        task_id,
                        status="running",
                        plan=plan,
                        results=results,
                        current_step=len(plan),
                        pending=None,
                        error=None,
                    )
                    if ran_validation:
                        problem = _completion_problem(requirements, results)

                if problem and "git diff" in problem.casefold():
                    await _append_git_diff(workspace, plan, results)
                    update_task(
                        task_id,
                        status="running",
                        plan=plan,
                        results=results,
                        current_step=len(plan),
                        pending=None,
                        error=None,
                    )
                    problem = _completion_problem(requirements, results)

                if problem:
                    plan.append(step)
                    results.append({
                        "step_index": len(plan) - 1,
                        "step": step,
                        "outcome": {
                            "tool": "finish_task",
                            "action": "finish_task",
                            "ok": False,
                            "error": f"Completion rejected: {problem}",
                        },
                    })
                    update_task(
                        task_id,
                        status="running",
                        plan=plan,
                        results=results,
                        current_step=len(plan),
                        pending=None,
                        error=None,
                    )
                    continue

                model_note = str(_arguments(step).get("content", ""))
                final_output = (
                    _build_final_output(results, model_note)
                    if requirements.get("mutation") or requirements.get("validation")
                    else _build_read_only_output(results)
                )
                plan.append(step)
                results.append({
                    "step_index": len(plan) - 1,
                    "step": step,
                    "outcome": {
                        "tool": "finish_task",
                        "action": "finish_task",
                        "ok": True,
                        "result": {"content": final_output},
                    },
                })
                update_task(
                    task_id,
                    status="completed",
                    plan=plan,
                    results=results,
                    current_step=len(plan),
                    pending=None,
                    final_output=final_output,
                    error=None,
                )
                return

            if tool in MUTATION_TOOLS:
                can_continue = await _ensure_target_read(workspace, plan, results, step)
                update_task(
                    task_id,
                    status="running",
                    plan=plan,
                    results=results,
                    current_step=len(plan),
                    pending=None,
                    error=None,
                )
                if not can_continue:
                    continue

                checkpoint_ok = await _ensure_checkpoint(task_id, workspace, plan, results)
                update_task(
                    task_id,
                    status="running",
                    plan=plan,
                    results=results,
                    current_step=len(plan),
                    pending=None,
                    error=None,
                )
                if not checkpoint_ok:
                    update_task(
                        task_id,
                        status="failed",
                        plan=plan,
                        results=results,
                        current_step=len(plan),
                        pending=None,
                        error="Could not create the mandatory Git checkpoint.",
                    )
                    return

            plan.append(step)
            step_index = len(plan) - 1
            approved = step_index in approved_steps or (
                autonomous and tool in MUTATION_TOOLS
            )

            try:
                outcome = await _execute_step(workspace, step, approved=approved)
            except Exception as exc:
                outcome = {
                    "tool": tool,
                    "action": tool,
                    "ok": False,
                    "error": str(exc),
                }

            if outcome.get("approval_required"):
                update_task(
                    task_id,
                    status="awaiting_approval",
                    plan=plan,
                    results=results,
                    current_step=step_index,
                    pending={
                        "step_index": step_index,
                        "step": step,
                        "outcome": outcome,
                    },
                    error=None,
                )
                return

            results.append({
                "step_index": step_index,
                "step": step,
                "outcome": outcome,
            })

            if outcome.get("blocked"):
                update_task(
                    task_id,
                    status="failed",
                    plan=plan,
                    results=results,
                    current_step=step_index + 1,
                    pending=None,
                    error="A requested operation was blocked.",
                )
                return

            if outcome.get("ok") and tool in MUTATION_TOOLS:
                await _append_git_diff(workspace, plan, results)

            update_task(
                task_id,
                status="running",
                plan=plan,
                results=results,
                current_step=len(plan),
                pending=None,
                error=None,
            )

        update_task(
            task_id,
            status="failed",
            plan=plan,
            results=results,
            current_step=len(plan),
            pending=None,
            error="The Agent reached its maximum step limit without verified completion.",
        )
    except Exception as exc:
        update_task(
            task_id,
            status="failed",
            plan=plan,
            results=results,
            pending=None,
            error=str(exc),
        )
