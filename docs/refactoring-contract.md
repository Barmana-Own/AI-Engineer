# Agent Service Refactoring Contract

## Scope

This contract defines the bounded extraction from `services/orchestrator/app/agent_service.py`. The objective is to reduce coupling in the model-action parsing path without redesigning the agent loop or changing public APIs.

## Before state

- `agent_service.py` contained the model tool vocabulary, aliases, approval classification, action coercion, JSON extraction, nested tool-call unwrapping, and step construction alongside orchestration, recovery, path policy, observations, and execution logic.
- Tests and existing modules imported parser helpers directly from `app.agent_service`.
- The agent loop, tool executor, persistence calls, and HTTP contracts were not in scope for this extraction.

## Target modules

| Module | Responsibility |
| --- | --- |
| `app/agent/parser.py` | Tool vocabulary, aliases, approval policy, model-action coercion, JSON parsing, nested-call unwrapping, and normalized step construction |
| `app/agent/__init__.py` | Package marker and stable package boundary |
| `app/agent_service.py` | Agent loop, recovery, path policy, observations, persistence, and execution; compatibility imports re-export parser symbols |

## Compatibility contract

The following names remain importable from `app.agent_service`: `TOOL_NAMES`, `TOOL_ALIASES`, `MUTATION_TOOLS`, `APPROVAL_TOOLS`, `MODEL_ACTION_ALIASES`, `VALIDATION_ACTION_ALIASES`, `_tool_name`, `_arguments`, `_make_step`, `_extract_json`, `_model_reported_verified_noop`, `_canonical_tool_name`, `_action_arguments`, `_normalise_model_edit_arguments`, `_coerce_model_action`, `_normalize_tool_call`, and `_unwrap_model_action`. Existing tests therefore require no import changes.

## Constraints

- Preserve behavior and error messages for accepted and rejected model payloads.
- Do not move the agent loop, persistence transactions, or tool execution into the parser module.
- Keep parser dependencies limited to the Python standard library and typing.
- Keep the extraction bounded to the parser module and package marker; avoid a broad rewrite.
- Verify syntax and the existing subagent/autonomous backlog tests after the move.

## After state

The parser concerns are isolated in `app/agent/parser.py`; `agent_service.py` imports and re-exports those symbols while retaining the existing execution flow. This creates a seam for future policy/loop extraction without changing the Control Center or Desktop API surface.

## Verification evidence

- `python -m py_compile app/agent/parser.py app/agent_service.py`
- `python -m unittest tests.test_subagents tests.test_autonomous_backlog`
