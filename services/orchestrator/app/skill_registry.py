"""Filesystem registry for imported engineering playbooks.

The registry is intentionally read-only.  It discovers the imported skill
materials and exposes metadata to future routing code, but it does not invoke
skills, create tasks, or treat ``project-state.json`` as workflow state.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SKILL_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DEFAULT_SKILLS_RELATIVE_PATH = Path("skills") / "software-delivery"
OUTER_PACKAGE_ALIASES = {
    "12-ullstack-final-review": "12-fullstack-final-review",
}


class SkillRegistryError(ValueError):
    """Raised when the installed skill registry is invalid."""


class UnknownSkillError(SkillRegistryError):
    """Raised when a caller requests a skill that is not installed."""


@dataclass(frozen=True)
class SkillScript:
    name: str
    classification: tuple[str, ...]
    execution: str


@dataclass(frozen=True)
class SkillDescriptor:
    skill_id: str
    display_name: str
    version: str | None
    purpose: str
    recommended_roles: tuple[str, ...]
    task_categories: tuple[str, ...]
    required_context: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    risk_class: str
    scripts: tuple[SkillScript, ...]
    references: tuple[str, ...]
    activation_policy: str
    stage_dependencies: tuple[str, ...]
    outputs: tuple[str, ...]
    root: Path
    source_outer_package: str
    normalized_outer_package: str | None
    external_allow_implicit_invocation: bool

    @property
    def skill_file(self) -> Path:
        return self.root / "SKILL.md"

    @property
    def openai_metadata_file(self) -> Path:
        return self.root / "agents" / "openai.yaml"


def normalize_outer_package_name(name: str) -> str:
    """Return the normalized package directory name without changing IDs."""

    return OUTER_PACKAGE_ALIASES.get(name, name)


def _repository_root() -> Path:
    configured = os.getenv("AI_ENGINE_PROJECT_ROOT") or os.getenv("PROJECT_ROOT")
    if configured:
        candidate = Path(configured).expanduser().resolve()
        if (candidate / DEFAULT_SKILLS_RELATIVE_PATH / "manifest.json").is_file():
            return candidate

    current = Path(__file__).resolve()
    for parent in (current.parent, *current.parents):
        if (parent / DEFAULT_SKILLS_RELATIVE_PATH / "manifest.json").is_file():
            return parent
    # The fallback is deterministic for the existing repository layout.  The
    # manifest check in SkillRegistry still reports a useful error if missing.
    return current.parents[3]


def _as_tuple(value: Any, *, field: str, skill_id: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SkillRegistryError(f"{skill_id}.{field} must be a list of strings")
    return tuple(value)


class SkillRegistry:
    """Load and validate the imported playbook manifest without executing it."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.repository_root = (
            Path(root).expanduser().resolve() if root is not None else _repository_root()
        )
        self.root = self.repository_root / DEFAULT_SKILLS_RELATIVE_PATH
        self.manifest_path = self.root / "manifest.json"
        self._skills = self._load_manifest()

    @property
    def state_authority(self) -> str:
        return "orchestrator_database"

    @property
    def skills(self) -> tuple[SkillDescriptor, ...]:
        return tuple(self._skills.values())

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._skills))

    def get(self, skill_id: str) -> SkillDescriptor:
        if not isinstance(skill_id, str) or not SKILL_ID_PATTERN.fullmatch(skill_id):
            raise UnknownSkillError(f"Unknown skill: {skill_id!r}")
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise UnknownSkillError(f"Unknown skill: {skill_id}") from exc

    def get_script(self, skill_id: str, script_name: str) -> tuple[SkillDescriptor, SkillScript]:
        """Return a manifest-declared script and its owning skill.

        Script names are resolved only through the repository manifest. Callers
        must not construct a filesystem path from model input and execute it.
        """

        descriptor = self.get(skill_id)
        normalized = str(script_name or "").replace("\\", "/").strip()
        if not normalized or "/" in normalized or normalized in {".", ".."}:
            raise UnknownSkillError(f"Unknown skill script: {skill_id}/{script_name}")
        for script in descriptor.scripts:
            if script.name == normalized:
                script_path = (descriptor.root / "scripts" / script.name).resolve(strict=False)
                scripts_root = (descriptor.root / "scripts").resolve(strict=False)
                try:
                    script_path.relative_to(scripts_root)
                except ValueError as exc:
                    raise SkillRegistryError(
                        f"Manifest script escapes its skill directory: {skill_id}/{script.name}"
                    ) from exc
                if not script_path.is_file():
                    raise SkillRegistryError(f"Manifest script is missing: {script_path}")
                return descriptor, script
        raise UnknownSkillError(f"Unknown skill script: {skill_id}/{script_name}")

    def load_skill_document(self, skill_id: str) -> str:
        descriptor = self.get(skill_id)
        return descriptor.skill_file.read_text(encoding="utf-8")

    def activation_allowed(
        self,
        skill_id: str,
        *,
        router_approved: bool,
        task_id: str | None = None,
        role: str | None = None,
        project_id: str | None = None,
    ) -> bool:
        """Apply the AI-Engineer routing boundary.

        The imported ``agents/openai.yaml`` is metadata only.  Even when it
        contains ``allow_implicit_invocation: true``, activation requires an
        explicit router decision and scoped task context.
        """

        descriptor = self.get(skill_id)
        if descriptor.activation_policy != "router_only":
            return False
        return bool(router_approved and task_id and role and project_id)

    def inventory(self) -> list[dict[str, Any]]:
        """Return bounded, filesystem-backed inventory data for reports."""

        rows: list[dict[str, Any]] = []
        for descriptor in self.skills:
            rows.append(
                {
                    "skill_id": descriptor.skill_id,
                    "skill_file": descriptor.skill_file.relative_to(self.repository_root).as_posix(),
                    "openai_metadata": descriptor.openai_metadata_file.relative_to(
                        self.repository_root
                    ).as_posix(),
                    "scripts": [script.name for script in descriptor.scripts],
                    "references": list(descriptor.references),
                    "assets": sorted(
                        path.name
                        for path in (descriptor.root / "assets").glob("*")
                        if path.is_file()
                    ),
                    "activation_policy": descriptor.activation_policy,
                    "state_authority": self.state_authority,
                }
            )
        return rows

    def _load_manifest(self) -> dict[str, SkillDescriptor]:
        if not self.manifest_path.is_file():
            raise SkillRegistryError(f"Skill manifest not found: {self.manifest_path}")
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SkillRegistryError(f"Unable to load skill manifest: {self.manifest_path}") from exc
        if not isinstance(payload, dict) or payload.get("state_authority") != self.state_authority:
            raise SkillRegistryError("Skill manifest must declare orchestrator_database as state authority")
        records = payload.get("skills")
        if not isinstance(records, list):
            raise SkillRegistryError("Skill manifest must contain a skills list")

        result: dict[str, SkillDescriptor] = {}
        for record in records:
            descriptor = self._descriptor_from_record(record)
            if descriptor.skill_id in result:
                raise SkillRegistryError(f"Duplicate skill id: {descriptor.skill_id}")
            result[descriptor.skill_id] = descriptor
        if not result:
            raise SkillRegistryError("Skill manifest contains no skills")
        return result

    def _descriptor_from_record(self, record: Any) -> SkillDescriptor:
        if not isinstance(record, dict):
            raise SkillRegistryError("Every skill manifest entry must be an object")
        skill_id = record.get("skill_id")
        if not isinstance(skill_id, str) or not SKILL_ID_PATTERN.fullmatch(skill_id):
            raise SkillRegistryError(f"Invalid skill id: {skill_id!r}")
        root = self.root / skill_id
        if not root.is_dir():
            raise SkillRegistryError(f"Skill directory missing for {skill_id}: {root}")
        for required in (root / "SKILL.md", root / "agents" / "openai.yaml"):
            if not required.is_file():
                raise SkillRegistryError(f"Required skill file missing: {required}")

        scripts: list[SkillScript] = []
        raw_scripts = record.get("scripts", [])
        if not isinstance(raw_scripts, list):
            raise SkillRegistryError(f"{skill_id}.scripts must be a list")
        for raw_script in raw_scripts:
            if not isinstance(raw_script, dict) or not isinstance(raw_script.get("name"), str):
                raise SkillRegistryError(f"Invalid script entry for {skill_id}")
            script_path = root / "scripts" / raw_script["name"]
            if not script_path.is_file():
                raise SkillRegistryError(f"Script missing for {skill_id}: {script_path}")
            classification = _as_tuple(
                raw_script.get("classification", []), field="scripts.classification", skill_id=skill_id
            )
            scripts.append(
                SkillScript(
                    name=raw_script["name"],
                    classification=classification,
                    execution=str(raw_script.get("execution", "local-agent-policy")),
                )
            )

        references = _as_tuple(record.get("references", []), field="references", skill_id=skill_id)
        missing_references = [name for name in references if not (root / "references" / name).is_file()]
        if missing_references:
            raise SkillRegistryError(
                f"Missing references for {skill_id}: {', '.join(missing_references)}"
            )

        # Never trust the external metadata's implicit-invocation flag.  It is
        # retained for audit visibility but cannot change this value.
        external = record.get("external_metadata")
        external_flag = bool(external.get("allow_implicit_invocation")) if isinstance(external, dict) else False
        return SkillDescriptor(
            skill_id=skill_id,
            display_name=str(record.get("display_name", skill_id)),
            version=record.get("version") if isinstance(record.get("version"), str) else None,
            purpose=str(record.get("purpose", "")),
            recommended_roles=_as_tuple(record.get("recommended_roles", []), field="recommended_roles", skill_id=skill_id),
            task_categories=_as_tuple(record.get("task_categories", []), field="task_categories", skill_id=skill_id),
            required_context=_as_tuple(record.get("required_context", []), field="required_context", skill_id=skill_id),
            allowed_tools=_as_tuple(record.get("allowed_tools", []), field="allowed_tools", skill_id=skill_id),
            risk_class=str(record.get("risk_class", "unknown")),
            scripts=tuple(scripts),
            references=references,
            activation_policy=str(record.get("activation_policy", "router_only")),
            stage_dependencies=_as_tuple(record.get("stage_dependencies", []), field="stage_dependencies", skill_id=skill_id),
            outputs=_as_tuple(record.get("outputs", []), field="outputs", skill_id=skill_id),
            root=root,
            source_outer_package=str(record.get("source_outer_package", skill_id)),
            normalized_outer_package=(
                str(record["normalized_outer_package"])
                if record.get("normalized_outer_package") is not None
                else None
            ),
            external_allow_implicit_invocation=external_flag,
        )


def iter_skill_ids(registry: SkillRegistry) -> Iterable[str]:
    """Small adapter for callers that prefer an iterator over ``ids()``."""

    return iter(registry.ids())
