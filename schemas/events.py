from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


EventType = Literal[
    "runtime.task.assign",
    "runtime.task.result",
    "runtime.llm.request",
    "runtime.llm.response",
    "runtime.agent.spawn",
    "runtime.agent.exit",
    "runtime.agent.error",
]


class EventScope(BaseModel):
    sandbox: Optional[str] = None
    worker: Optional[str] = None
    task: Optional[str] = None
    session: Optional[str] = None


class EventRefs(BaseModel):
    workspace: Optional[str] = None
    context: Optional[str] = None
    artifact: Optional[str] = None


class RuntimeEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str
    scope: Optional[EventScope] = None
    refs: Optional[EventRefs] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


def make_event(
    event_type: EventType,
    source: str,
    payload: Optional[Dict[str, Any]] = None,
    scope: Optional[EventScope] = None,
    refs: Optional[EventRefs] = None,
) -> RuntimeEvent:
    return RuntimeEvent(
        type=event_type,
        source=source,
        payload=payload or {},
        scope=scope,
        refs=refs,
    )
