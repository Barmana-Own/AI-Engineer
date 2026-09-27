"""Structured multi-agent coordination primitives."""
from .models import (AgentMessage, AgentHandoff, CoordinationTask, RoleContract, TaskState, MessageType, WritePermission)
from .roles import ROLE_REGISTRY, get_role_contract, resolve_role
__all__ = ["AgentMessage", "AgentHandoff", "CoordinationTask", "RoleContract", "TaskState", "MessageType", "WritePermission", "ROLE_REGISTRY", "get_role_contract", "resolve_role"]
