from __future__ import annotations
import json
from typing import Mapping, Sequence
from . import store
from .roles import get_role_contract
class ContextBuilder:
    def __init__(self,database_path: str|None=None, *, max_chars: int=30000): self.database_path=database_path; self.max_chars=max(1000,int(max_chars))
    def build(self, *, task_id: str, role: str, validated_memory: Sequence[Mapping[str,object]]=()) -> dict[str,object]:
        task=store.get_task(task_id,database_path=self.database_path)
        if not task: raise KeyError(task_id)
        deps=[item for item in store.list_dependencies(task_id,database_path=self.database_path)]
        messages=store.list_messages(run_id=str(task.get("run_id") or "") or None,task_id=task_id,limit=50,database_path=self.database_path)
        handoffs=store.list_handoffs(run_id=str(task.get("run_id") or "") or None,task_id=task_id,limit=10,database_path=self.database_path)
        context={"task":task,"dependencies":deps,"messages":messages,"recent_handoffs":handoffs,"validated_memory":[dict(item) for item in validated_memory[:10]],"role_contract":get_role_contract(str(role)).as_dict()}
        encoded=json.dumps(context,ensure_ascii=False)
        if len(encoded)>self.max_chars:
            context["messages"]=messages[-10:]; context["validated_memory"]=context["validated_memory"][-5:]; context["truncated"]=True
        return context
