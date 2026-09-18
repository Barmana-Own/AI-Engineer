from __future__ import annotations
from datetime import datetime, timezone
from typing import Iterable
from . import store
from .models import AgentHandoff, AgentMessage, MessageType
from .roles import get_role_contract
class MessageBus:
    def __init__(self,database_path: str|None=None): self.database_path=database_path
    def publish(self, *, sender_role: str, message_type: MessageType|str, subject: str, body: str, run_id: str|None=None, project_id: str|None=None, task_id: str|None=None, recipient_role: str|None=None, references: Iterable[str]=(), discussion_round: int=0) -> dict[str,object]:
        kind=message_type if isinstance(message_type,MessageType) else MessageType(str(message_type))
        message=AgentMessage(sender_role=sender_role,message_type=kind,subject=subject,body=body,run_id=run_id,project_id=project_id,task_id=task_id,recipient_role=recipient_role,references=tuple(references),discussion_round=discussion_round)
        return store.create_message(message,database_path=self.database_path)
    def relevant(self, *, run_id: str|None=None, project_id: str|None=None, task_id: str|None=None, limit: int=50) -> list[dict[str,object]]:
        return store.list_messages(run_id=run_id,project_id=project_id,task_id=task_id,limit=limit,database_path=self.database_path)
class DiscussionController:
    def __init__(self,bus: MessageBus, *, max_rounds: int=3, timeout_seconds: int=900, confidence_threshold: float=0.75):
        self.bus=bus; self.max_rounds=max(1,int(max_rounds)); self.timeout_seconds=max(1,int(timeout_seconds)); self.confidence_threshold=max(0.0,min(float(confidence_threshold),1.0))
    def can_continue(self, messages: list[dict[str,object]]) -> bool:
        if not messages:
            return True
        rounds=[int(item.get("discussion_round") or 0) for item in messages]
        if rounds and max(rounds) >= self.max_rounds:
            return False
        latest=max((str(item.get("created_at") or "") for item in messages), default="")
        if latest:
            try:
                created=datetime.fromisoformat(latest.replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created=created.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc)-created).total_seconds() > self.timeout_seconds:
                    return False
            except ValueError:
                pass
        return True
    def submit(self, *, sender_role: str, message_type: MessageType, subject: str, body: str, run_id: str, project_id: str, task_id: str|None=None, recipient_role: str|None=None, references: Iterable[str]=()) -> dict[str,object]:
        existing=self.bus.relevant(run_id=run_id,task_id=task_id,limit=100)
        if not self.can_continue(existing): raise RuntimeError("discussion round limit reached; supervisor resolution required")
        round_no=max([int(item.get("discussion_round") or 0) for item in existing] or [0])+1
        return self.bus.publish(sender_role=sender_role,message_type=message_type,subject=subject,body=body,run_id=run_id,project_id=project_id,task_id=task_id,recipient_role=recipient_role,references=references,discussion_round=round_no)
    def resolve(self, *, run_id: str, project_id: str, subject: str, decision: str, evidence: Iterable[str]=(), task_id: str|None=None) -> dict[str,object]:
        return self.bus.publish(sender_role="supervisor",message_type=MessageType.DECISION,subject=subject,body=decision,run_id=run_id,project_id=project_id,task_id=task_id,references=evidence,discussion_round=self.max_rounds)
class HandoffProtocol:
    def __init__(self,database_path: str|None=None): self.database_path=database_path
    def submit(self, handoff: AgentHandoff) -> dict[str,object]: return store.create_handoff(handoff,database_path=self.database_path)
    def list(self, *, run_id: str|None=None, project_id: str|None=None, task_id: str|None=None, limit: int=50) -> list[dict[str,object]]: return store.list_handoffs(run_id=run_id,project_id=project_id,task_id=task_id,limit=limit,database_path=self.database_path)
