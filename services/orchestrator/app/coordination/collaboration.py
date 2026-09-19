from __future__ import annotations

from typing import Iterable

from .bus import DiscussionController, MessageBus
from .collaboration_store import (
    create_conversation,
    create_decision,
    create_meeting,
    create_work_request,
    get_conversation,
    get_meeting,
    list_conversations,
    list_meetings,
    update_meeting,
    update_work_request,
)
from .models import (
    ConversationType,
    InternalWorkRequest,
    MeetingType,
    MessageType,
    StructuredMeeting,
    TechnicalDecision,
    WorkRequestStatus,
)


_RESOLUTION_RANK = {
    "participant": 10,
    "architect": 10,
    "backend": 10,
    "frontend": 10,
    "tester": 10,
    "security": 10,
    "reviewer": 10,
    "project_manager": 20,
    "engineering_manager": 30,
    "supervisor": 30,
    "company_director": 40,
    "owner": 50,
    "human_owner": 50,
}


class CollaborationEngine:
    """Structured collaboration on top of the persisted message bus."""

    def __init__(self, database_path: str | None = None, *, max_rounds: int = 3, timeout_seconds: int = 900):
        self.database_path = database_path
        self.bus = MessageBus(database_path)
        self.discussions = DiscussionController(self.bus, max_rounds=max_rounds, timeout_seconds=timeout_seconds)

    def create_conversation(
        self,
        *,
        project_id: str | None,
        subject: str,
        conversation_type: ConversationType | str = ConversationType.DIRECT,
        participants: Iterable[str] = (),
        topic: str = "",
        department: str | None = None,
        run_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, object]:
        return create_conversation(
            project_id=project_id,
            subject=subject,
            conversation_type=conversation_type,
            participants=participants,
            topic=topic,
            department=department,
            run_id=run_id,
            task_id=task_id,
            database_path=self.database_path,
        )

    def conversations(self, *, project_id: str | None = None, conversation_type: str | None = None, participant: str | None = None, limit: int = 100) -> list[dict[str, object]]:
        return list_conversations(
            project_id=project_id,
            conversation_type=conversation_type,
            participant=participant,
            limit=limit,
            database_path=self.database_path,
        )

    def send(
        self,
        *,
        conversation_id: str,
        sender_role: str,
        message_type: MessageType | str,
        subject: str,
        body: str,
        recipient_role: str | None = None,
        references: Iterable[str] = (),
        topic: str = "",
    ) -> dict[str, object]:
        conversation = get_conversation(conversation_id, database_path=self.database_path)
        if not conversation:
            raise KeyError(conversation_id)
        participants = {str(item) for item in conversation.get("participants", [])}
        if participants and sender_role not in participants:
            raise PermissionError("sender is not a conversation participant")
        kind = message_type if isinstance(message_type, MessageType) else MessageType(str(message_type).upper())
        return self.bus.publish(
            sender_role=sender_role,
            recipient_role=recipient_role,
            message_type=kind,
            subject=subject,
            body=body,
            run_id=str(conversation["run_id"]) if conversation.get("run_id") else None,
            project_id=str(conversation["project_id"]) if conversation.get("project_id") else None,
            task_id=str(conversation["task_id"]) if conversation.get("task_id") else None,
            references=references,
            conversation_id=conversation_id,
            audience_type=str(conversation["conversation_type"]),
            audience_id=str(conversation.get("department") or conversation_id),
            participant_roles=participants,
            topic=topic or str(conversation.get("topic") or ""),
        )

    def discuss(
        self,
        *,
        conversation_id: str,
        sender_role: str,
        message_type: MessageType | str,
        subject: str,
        body: str,
        recipient_role: str | None = None,
        references: Iterable[str] = (),
    ) -> dict[str, object]:
        conversation = get_conversation(conversation_id, database_path=self.database_path)
        if not conversation:
            raise KeyError(conversation_id)
        run_id = str(conversation.get("run_id") or "")
        project_id = str(conversation.get("project_id") or "")
        if not run_id or not project_id:
            raise ValueError("discussion requires run_id and project_id")
        kind = message_type if isinstance(message_type, MessageType) else MessageType(str(message_type).upper())
        return self.discussions.submit(
            sender_role=sender_role,
            message_type=kind,
            subject=subject,
            body=body,
            run_id=run_id,
            project_id=project_id,
            task_id=str(conversation["task_id"]) if conversation.get("task_id") else None,
            recipient_role=recipient_role,
            references=references,
            conversation_id=conversation_id,
        )

    def resolve_discussion(
        self,
        *,
        conversation_id: str,
        decision_maker: str,
        title: str,
        decision: str,
        context: str = "",
        options: Iterable[str] = (),
        arguments: Iterable[str] = (),
        evidence: Iterable[str] = (),
        affected_tasks: Iterable[str] = (),
    ) -> dict[str, object]:
        conversation = get_conversation(conversation_id, database_path=self.database_path)
        if not conversation:
            raise KeyError(conversation_id)
        participants = [str(item) for item in conversation.get("participants", [])]
        participant_rank = max((_RESOLUTION_RANK.get(item, 10) for item in participants), default=10)
        maker_rank = _RESOLUTION_RANK.get(decision_maker, 10)
        if maker_rank < participant_rank and decision_maker not in {"participant"}:
            raise PermissionError("decision maker does not have resolution authority")
        project_id = str(conversation.get("project_id") or "")
        if not project_id:
            raise ValueError("decision requires a project")
        record = create_decision(
            TechnicalDecision(
                project_id=project_id,
                run_id=str(conversation.get("run_id") or "") or None,
                title=title,
                context=context,
                options=tuple(options),
                arguments=tuple(arguments),
                decision=decision,
                decision_maker=decision_maker,
                supporting_evidence=tuple(evidence),
                affected_tasks=tuple(affected_tasks),
                meeting_id=None,
            ),
            database_path=self.database_path,
        )
        message = self.bus.publish(
            sender_role=decision_maker,
            message_type=MessageType.DECISION,
            subject=title,
            body=decision,
            run_id=str(conversation.get("run_id") or "") or None,
            project_id=project_id,
            task_id=str(conversation.get("task_id") or "") or None,
            references=evidence,
            discussion_round=self.discussions.max_rounds,
            conversation_id=conversation_id,
            audience_type=str(conversation["conversation_type"]),
            participant_roles=participants,
        )
        return {"decision": record, "message": message}

    def start_meeting(
        self,
        *,
        project_id: str,
        meeting_type: MeetingType | str,
        objective: str,
        participants: Iterable[str],
        agenda: Iterable[str] = (),
        run_id: str | None = None,
    ) -> dict[str, object]:
        return create_meeting(
            StructuredMeeting(
                project_id=project_id,
                run_id=run_id,
                meeting_type=meeting_type,
                objective=objective,
                participants=tuple(participants),
                agenda=tuple(agenda),
                status="scheduled",
            ),
            database_path=self.database_path,
        )

    def meetings(self, *, project_id: str | None = None, status: str | None = None, limit: int = 100) -> list[dict[str, object]]:
        return list_meetings(project_id=project_id, status=status, limit=limit, database_path=self.database_path)

    def add_meeting_message(
        self,
        *,
        meeting_id: str,
        sender_role: str,
        message_type: MessageType | str,
        subject: str,
        body: str,
        recipient_role: str | None = None,
        references: Iterable[str] = (),
    ) -> dict[str, object]:
        meeting = get_meeting(meeting_id, database_path=self.database_path)
        if not meeting:
            raise KeyError(meeting_id)
        if sender_role not in set(str(item) for item in meeting["participants"]):
            raise PermissionError("sender is not a meeting participant")
        conversation = self.create_conversation(
            project_id=str(meeting["project_id"]),
            run_id=str(meeting.get("run_id") or "") or None,
            subject=str(meeting["objective"]),
            conversation_type=ConversationType.GROUP,
            participants=meeting["participants"],
            topic=str(meeting["meeting_type"]),
        )
        message = self.send(
            conversation_id=str(conversation["conversation_id"]),
            sender_role=sender_role,
            message_type=message_type,
            subject=subject,
            body=body,
            recipient_role=recipient_role,
            references=references,
            topic=str(meeting["meeting_type"]),
        )
        update_meeting(
            meeting_id,
            status="active",
            message_ids=tuple(meeting["message_ids"]) + (str(message["message_id"]),),
            database_path=self.database_path,
        )
        return message

    def record_meeting_decision(
        self,
        *,
        meeting_id: str,
        title: str,
        context: str,
        decision: str,
        decision_maker: str,
        evidence: Iterable[str] = (),
        affected_tasks: Iterable[str] = (),
    ) -> dict[str, object]:
        meeting = get_meeting(meeting_id, database_path=self.database_path)
        if not meeting:
            raise KeyError(meeting_id)
        project_id = str(meeting["project_id"])
        record = create_decision(
            TechnicalDecision(
                project_id=project_id,
                run_id=str(meeting.get("run_id") or "") or None,
                meeting_id=meeting_id,
                title=title,
                context=context,
                decision=decision,
                decision_maker=decision_maker,
                supporting_evidence=tuple(evidence),
                affected_tasks=tuple(affected_tasks),
            ),
            database_path=self.database_path,
        )
        update_meeting(
            meeting_id,
            status="active",
            decision_ids=tuple(meeting["decision_ids"]) + (str(record["decision_id"]),),
            database_path=self.database_path,
        )
        return record

    def close_meeting(
        self,
        meeting_id: str,
        *,
        action_items: Iterable[str] = (),
        unresolved_questions: Iterable[str] = (),
    ) -> dict[str, object]:
        meeting = get_meeting(meeting_id, database_path=self.database_path)
        if not meeting:
            raise KeyError(meeting_id)
        actions = tuple(str(item) for item in action_items if str(item).strip())
        questions = tuple(str(item) for item in unresolved_questions if str(item).strip())
        if not meeting["message_ids"] and not meeting["decision_ids"] and not actions and not questions:
            raise ValueError("meeting must produce a decision, action item, question, or message")
        return update_meeting(
            meeting_id,
            status="completed",
            action_items=actions,
            unresolved_questions=questions,
            database_path=self.database_path,
        )

    def request_help(
        self,
        *,
        sender: str,
        recipient: str,
        project_id: str,
        request_type: str,
        description: str,
        priority: int = 50,
        run_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, object]:
        return create_work_request(
            InternalWorkRequest(
                sender=sender,
                recipient=recipient,
                project_id=project_id,
                run_id=run_id,
                task_id=task_id,
                request_type=request_type,
                description=description,
                priority=priority,
            ),
            database_path=self.database_path,
        )

    def respond_help(
        self,
        request_id: str,
        *,
        response: str,
        status: WorkRequestStatus | str = WorkRequestStatus.ANSWERED,
    ) -> dict[str, object]:
        return update_work_request(request_id, status=status, response=response, database_path=self.database_path)

