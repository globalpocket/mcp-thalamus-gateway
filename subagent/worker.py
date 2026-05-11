from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, Optional

from gateway.bus_adapter import create_nats_bus
from schemas.events import EventScope, RuntimeEvent, make_event


class SubagentWorker:
    """Thalamus runtime の NatsBus を利用する Subagent 実装。"""

    def __init__(self) -> None:
        self._nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
        self._worker_id = os.getenv("WORKER_ID", "wk-local")
        self._task_id = os.getenv("TASK_ID", "task-local")
        self._session_id = os.getenv("SESSION_ID") or None
        self._bus = create_nats_bus(servers=[self._nats_url])
        self._llm_future: Optional[asyncio.Future[Dict[str, Any]]] = None

    async def run(self) -> None:
        await self._bus.connect()
        await self._bus.subscribe("runtime.task.assign", self._on_task_assign)
        await self._bus.subscribe("runtime.llm.response", self._on_llm_response)
        await asyncio.Event().wait()

    async def _publish(self, event: RuntimeEvent) -> None:
        await self._bus.publish(event.type, json.dumps(event.model_dump()).encode())

    async def _on_task_assign(self, subject: str, event_payload: Dict[str, Any]) -> None:
        _ = subject
        event = RuntimeEvent.model_validate(event_payload)
        if not event.scope or event.scope.worker != self._worker_id:
            return

        objective = event.payload.get("objective", "")
        llm_request = make_event(
            "runtime.llm.request",
            source=f"runtime.worker.{self._worker_id}",
            payload={"prompt": objective},
            scope=EventScope(worker=self._worker_id, task=self._task_id, session=self._session_id),
            refs=event.refs,
        )

        self._llm_future = asyncio.get_event_loop().create_future()
        await self._publish(llm_request)
        llm_response = await self._llm_future

        result = make_event(
            "runtime.task.result",
            source=f"runtime.worker.{self._worker_id}",
            payload={"summary": llm_response.get("summary", "ok"), "raw": llm_response},
            scope=EventScope(worker=self._worker_id, task=self._task_id, session=self._session_id),
            refs=event.refs,
        )
        await self._publish(result)

        exit_evt = make_event(
            "runtime.agent.exit",
            source=f"runtime.worker.{self._worker_id}",
            payload={"reason": "completed"},
            scope=EventScope(worker=self._worker_id, task=self._task_id, session=self._session_id),
            refs=event.refs,
        )
        await self._publish(exit_evt)

    async def _on_llm_response(self, subject: str, event_payload: Dict[str, Any]) -> None:
        _ = subject
        if not self._llm_future or self._llm_future.done():
            return
        event = RuntimeEvent.model_validate(event_payload)
        if not event.scope or event.scope.worker != self._worker_id:
            return
        result = event.payload.get("result", {})
        self._llm_future.set_result(result)


async def run_worker() -> None:
    worker = SubagentWorker()
    await worker.run()
