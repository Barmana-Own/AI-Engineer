from __future__ import annotations

import json
from typing import Mapping, Sequence

from app.memory import MemoryStore
from . import store
from .roles import get_role_contract


class ContextBuilder:
    def __init__(self, database_path: str | None = None, *, max_chars: int = 30_000):
        self.database_path = database_path
        self.max_chars = max(1_000, int(max_chars))
        self.memory = MemoryStore(database_path)

    def build(
        self,
        *,
        task_id: str,
        role: str,
        validated_memory: Sequence[Mapping[str, object]] = (),
    ) -> dict[str, object]:
        task = store.get_task(task_id, database_path=self.database_path)
        if not task:
            raise KeyError(task_id)
        dependencies = [
            item
            for item in store.list_dependencies(task_id, database_path=self.database_path)
        ]
        run_id = str(task.get("run_id") or "") or None
        messages = store.list_messages(
            run_id=run_id,
            task_id=task_id,
            limit=50,
            database_path=self.database_path,
        )
        handoffs = store.list_handoffs(
            run_id=run_id,
            task_id=task_id,
            limit=10,
            database_path=self.database_path,
        )
        task_title = str(task.get("title") or task.get("task_type") or "")
        task_description = str(task.get("description") or task.get("instruction") or "")
        query = f"{task_title} {task_description}".strip()
        files = task.get("files") or task.get("scope") or ()
        if isinstance(files, str):
            files = (files,)
        experience = self.memory.retrieve(
            project_id=str(task.get("project_id") or "") or None,
            run_id=run_id,
            task_id=task_id,
            query=query,
            role=role,
            task_type=task_title or None,
            files=files if isinstance(files, (list, tuple, set)) else (),
            limit=8,
            include_candidate=True,
        )
        context: dict[str, object] = {
            "task": task,
            "dependencies": dependencies,
            "messages": messages,
            "recent_handoffs": handoffs,
            "validated_memory": [dict(item) for item in validated_memory[:10]],
            "experience_memory": experience,
            "role_contract": get_role_contract(str(role)).as_dict(),
        }
        encoded = json.dumps(context, ensure_ascii=False, default=str)
        if len(encoded) > self.max_chars:
            context["messages"] = messages[-10:]
            context["validated_memory"] = context["validated_memory"][-5:]
            context["experience_memory"] = experience[:4]
            context["truncated"] = True
        return context
