# Agent Collaboration, Discussion and Meetings

| Field | Value |
|---|---|
| Phase | 8B |
| Gregorian date | 2026-09-18 |
| Jalali date | 1405-06-27 |
| Status | Implemented on the existing persisted message bus |

## Collaboration model

The collaboration engine reuses agent_messages and the existing MessageBus. Conversations are durable scopes for direct, group, project and department communication. Messages carry a typed message type, sender, recipient, project/run/task scope, topic, references and participant roles.

Supported message types include QUESTION, ANSWER, PROPOSAL, EVIDENCE, CHALLENGE, COUNTER_PROPOSAL, REVISION_REQUEST, DECISION, DISSENT, STATUS, BLOCKER, HANDOFF and RESULT.

## Discussion and disagreement

DiscussionController enforces a bounded number of rounds and a timeout. It does not concatenate the entire project transcript into a model prompt. A decision can be persisted only by a participant or a manager with sufficient resolution authority. TechnicalDecision records retain context, options, arguments, evidence, affected tasks and the decision maker.

Resolution order is participants, Project Manager, Engineering Manager or Supervisor, Company Director and Human Owner. The final decision is also emitted as a DECISION message.

## Meetings

StructuredMeeting records objective, type, participants, agenda, messages, decisions, action items and unresolved questions. Supported types include kickoff, requirements, architecture, engineering sync, bug triage, security, release review and postmortem. A meeting cannot be closed empty; it must produce a message, decision, action item or unresolved question.

## Internal requests

agent_work_requests represents formal help requests between employees. A request is project-scoped and supports priority, task/run linkage, open/in-progress/answered/declined/cancelled status and a durable response.

## APIs

Routes are under /v1/collaboration:

- POST and GET /conversations
- POST /conversations/{id}/messages
- POST /conversations/{id}/discussion
- POST /conversations/{id}/resolve
- POST and GET /meetings
- POST /meetings/{id}/messages
- POST /meetings/{id}/decisions
- POST /meetings/{id}/close
- POST /work-requests
- POST /work-requests/{id}/respond

## Persistence and isolation

Migration 8 adds scoped fields to agent_messages and creates coordination_conversations, coordination_decisions, coordination_meetings and agent_work_requests. Migration 9 adds the project-management tables. All records are filtered by project/run/task and tests use temporary SQLite databases.

## Validation

tests/test_collaboration.py verifies scoped messages, project isolation, decision persistence, discussion round limits, meeting outcomes, and work-request responses. The collaboration suite is deterministic and uses real database writes; only the model layer remains outside this fixture.

## Limitations

Meeting messages currently create a durable group conversation for each append because the existing meeting schema stores message IDs rather than a conversation ID. This is bounded and queryable but can be consolidated in a later migration. Discussion confidence scoring and distributed meetings are not implemented.
