from __future__ import annotations

import ast
import json
import re
from typing import Any
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
    text = value.strip().replace("â€œ", '"').replace("â€", '"')
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

def _model_reported_verified_noop(value: str) -> bool:
    """Recognize a bounded no-op summary emitted instead of a tool call."""
    try:
        payload = _extract_json(str(value or ""))
    except ValueError:
        return False
    detail = payload.get("detail") if isinstance(payload.get("detail"), dict) else {}
    status = str(detail.get("status") or payload.get("status") or payload.get("kind") or "").casefold()
    changed_files = detail.get("changed_files") or payload.get("changed_files") or []
    failures = detail.get("failures") or payload.get("failures") or detail.get("blockers") or payload.get("blockers") or []
    validations = detail.get("validations") or payload.get("validations") or []
    successful_validation = any(
        isinstance(item, dict)
        and (
            item.get("ok") is True
            or item.get("exit_code") == 0
            or str(item.get("status") or "").casefold() in {"pass", "passed", "success", "completed"}
        )
        for item in validations
    )
    if not successful_validation and validations and all(not isinstance(item, dict) for item in validations):
        successful_validation = True
    summary = " ".join(
        str(value)
        for value in (payload.get("summary"), detail.get("summary"))
        if value
    ).casefold()
    structured_noop = (
        str(payload.get("mode") or detail.get("mode") or "").casefold() == "autonomous"
        and payload.get("step_count") is not None
        and "changed_files" in payload
        and "validations" in payload
        and "failures" in payload
    )
    return (
        status in {"completed", "success"}
        and not changed_files
        and not failures
        and successful_validation
        and (
            structured_noop
            or any(
                marker in summary
                for marker in (
                    "no additional safe bounded change",
                    "already satisfies",
                    "no safe bounded change",
                    "verified completion from real tool outcomes",
                )
            )
        )
    )
MODEL_ACTION_ALIASES = {
    "code_change": "apply_patch",
    "code_editor": "apply_patch",
    "edit": "apply_patch",
    "edit_file": "apply_patch",
    "file_editor": "apply_patch",
}
VALIDATION_ACTION_ALIASES = {"run_validation"}


def _canonical_tool_name(value: object) -> str:
    name = str(value or "").strip().casefold()
    return TOOL_ALIASES.get(name, name)


def _action_arguments(raw: dict[str, Any]) -> dict[str, Any]:
    value = raw.get("arguments")
    if value is None:
        value = raw.get("args")
    direct_keys = (
        "command",
        "validation_command",
        "cwd",
        "path",
        "file_path",
        "file",
        "target",
        "edits",
        "changes",
        "change",
        "old",
        "old_content",
        "search_pattern",
        "new",
        "new_content",
        "replacement_text",
        "content",
    )
    direct = {key: raw[key] for key in direct_keys if key in raw}
    if isinstance(value, dict):
        return {**direct, **value}
    return direct


def _normalise_model_edit_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    source = dict(arguments)
    path = (
        source.get("path")
        or source.get("file_path")
        or source.get("file")
        or source.get("target")
    )
    raw_edits = source.get("edits")
    if raw_edits is None:
        raw_edits = source.get("changes")
    if raw_edits is None and isinstance(source.get("change"), dict):
        raw_edits = [source["change"]]
    if not isinstance(raw_edits, list) or not raw_edits:
        old = source.get("old")
        if old is None:
            old = source.get("old_content")
        if old is None:
            old = source.get("search_pattern")
        new = source.get("new")
        if new is None:
            new = source.get("new_content")
        if new is None:
            new = source.get("replacement_text")
        if old is not None and new is not None:
            raw_edits = [source]
    if not isinstance(raw_edits, list) or not raw_edits:
        raise ValueError(
            "Unsupported editor payload. Use apply_patch with exact old and new text "
            "edits; line ranges or full-content replacements are not accepted."
        )

    edits: list[dict[str, Any]] = []
    discovered_paths: set[str] = set()
    for item in raw_edits:
        if not isinstance(item, dict):
            raise ValueError("Every editor change must be an object.")
        item_path = (
            item.get("path")
            or item.get("file_path")
            or item.get("file")
            or item.get("target")
        )
        if item_path:
            discovered_paths.add(str(item_path))
        old = item.get("old")
        if old is None:
            old = item.get("old_content")
        if old is None:
            old = item.get("search_pattern")
        new = item.get("new")
        if new is None:
            new = item.get("new_content")
        if new is None:
            new = item.get("replacement_text")
        if old is None or new is None:
            raise ValueError(
                "Editor changes must include exact old and new text. "
                "Read the file first, then use apply_patch."
            )
        edit: dict[str, Any] = {"old": str(old), "new": str(new)}
        if "replace_all" in item:
            edit["replace_all"] = bool(item.get("replace_all"))
        edits.append(edit)

    if not path and len(discovered_paths) == 1:
        path = next(iter(discovered_paths))
    if not path:
        raise ValueError("Editor payload requires a project-relative file path.")
    return {"path": str(path), "edits": edits}


def _coerce_model_action(raw: dict[str, Any]) -> dict[str, Any]:
    name = raw.get("tool") or raw.get("action") or raw.get("name") or ""
    key = str(name).strip().casefold()
    canonical = _canonical_tool_name(name)
    if canonical in TOOL_NAMES:
        result = dict(raw)
        result["tool"] = canonical
        result["action"] = canonical
        return result

    arguments = _action_arguments(raw)
    if key in VALIDATION_ACTION_ALIASES:
        command = arguments.get("command") or arguments.get("validation_command")
        if not isinstance(command, str) or not command.strip():
            raise ValueError(
                "run_validation requires a command; use run_terminal with "
                "a bounded validation command."
            )
        mapped = dict(arguments)
        mapped["command"] = command.strip()
        mapped.setdefault("cwd", ".")
        result = dict(raw)
        result["tool"] = "run_terminal"
        result["action"] = "run_terminal"
        result["arguments"] = mapped
        result["args"] = mapped
        return result

    if key in MODEL_ACTION_ALIASES:
        mapped = _normalise_model_edit_arguments(arguments)
        result = dict(raw)
        result["tool"] = "apply_patch"
        result["action"] = "apply_patch"
        result["arguments"] = mapped
        result["args"] = mapped
        return result

    return raw


def _normalize_tool_call(raw: dict[str, Any]) -> dict[str, Any]:
    raw = _unwrap_model_action(raw)
    if not isinstance(raw, dict):
        raise ValueError("Tool call must be a JSON object.")
    raw_name = raw.get("tool") or raw.get("action") or ""
    tool = _canonical_tool_name(raw_name)
    arguments = raw.get("arguments")
    if arguments is None:
        arguments = raw.get("args") or {}

    if tool not in TOOL_NAMES:
        raise ValueError(f"Unsupported Agent tool: {str(raw_name).strip()}")
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
    if not isinstance(raw, dict):
        return raw

    if raw.get("tool") or raw.get("action"):
        return _coerce_model_action(raw)

    # Qwen-compatible gateways occasionally wrap the selected function in a
    # tool_call object instead of returning the public agent_action envelope.
    nested_call = raw.get("tool_call")
    if isinstance(nested_call, dict):
        nested_name = str(
            nested_call.get("name")
            or nested_call.get("tool")
            or nested_call.get("action")
            or ""
        ).strip()
        nested_arguments = nested_call.get("arguments")
        if nested_arguments is None:
            nested_arguments = nested_call.get("args")
        if nested_name.casefold() == "agent_action" and isinstance(
            nested_arguments, dict
        ):
            return _coerce_model_action(nested_arguments)
        if nested_name:
            return _coerce_model_action(
                {
                    "tool": nested_name,
                    "arguments": (
                        nested_arguments if isinstance(nested_arguments, dict) else {}
                    ),
                    "reason": str(raw.get("reason") or nested_call.get("reason") or ""),
                    "expected_result": str(raw.get("expected_result") or ""),
                }
            )
        for candidate_name, candidate_arguments in nested_call.items():
            candidate_key = str(candidate_name).strip().casefold()
            if (
                candidate_key in TOOL_NAMES
                or candidate_key in TOOL_ALIASES
                or candidate_key in MODEL_ACTION_ALIASES
                or candidate_key in VALIDATION_ACTION_ALIASES
            ):
                return _coerce_model_action(
                    {
                        "tool": str(candidate_name),
                        "arguments": (
                            candidate_arguments
                            if isinstance(candidate_arguments, dict)
                            else {}
                        ),
                        "reason": str(raw.get("reason") or ""),
                        "expected_result": str(raw.get("expected_result") or ""),
                    }
                )

    name = str(raw.get("name") or "").strip()
    arguments = raw.get("arguments")
    if name.casefold() == "agent_action" and isinstance(arguments, dict):
        if arguments.get("tool") or arguments.get("action"):
            return _coerce_model_action(arguments)
        tool_arguments = arguments.get("tool_arguments")
        if isinstance(tool_arguments, list) and tool_arguments:
            tool_name = str(tool_arguments[0])
            tool_args = (
                tool_arguments[1] if len(tool_arguments) > 1 else {}
            )
            return _coerce_model_action(
                {
                    "tool": tool_name,
                    "arguments": tool_args if isinstance(tool_args, dict) else {},
                    "reason": str(arguments.get("reason") or ""),
                    "expected_result": str(arguments.get("expected_result") or ""),
                }
            )

    if name:
        return _coerce_model_action(
            {
                "tool": name,
                "arguments": arguments if isinstance(arguments, dict) else {},
                "reason": str(raw.get("reason") or ""),
                "expected_result": str(raw.get("expected_result") or ""),
            }
        )

    return raw


