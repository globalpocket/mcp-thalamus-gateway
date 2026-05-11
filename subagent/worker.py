from __future__ import annotations

import asyncio
import os
from typing import Any

from nats.aio.client import Client as NATS

from schemas.events import EventScope, RuntimeEvent, make_event


class SubagentWorker:
    def __init__(self) -> None:
        self._nats = NATS()
        self._nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
        self._worker_id = os.getenv("WORKER_ID", "wk-local")
        self._task_id = os.getenv("TASK_ID", "task-local")
        self._session_id = os.getenv("SESSION_ID") or None
        self._llm_future: asyncio.Future[dict[str, Any]] | None = None

    async def run(self) -> None:
        await self._nats.connect(self._nats_url)
        await self._nats.subscribe("runtime.task.assign", cb=self._on_task_assign)
        await self._nats.subscribe("runtime.llm.response", cb=self._on_llm_response)
        await asyncio.Event().wait()

    async def _publish(self, event: RuntimeEvent) -> None:
        await self._nats.publish(event.type, event.model_dump_json().encode())

    async def _on_task_assign(self, msg: Any) -> None:
        event = RuntimeEvent.model_validate_json(msg.data.decode())
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

    async def _on_llm_response(self, msg: Any) -> None:
        if not self._llm_future or self._llm_future.done():
            return
        event = RuntimeEvent.model_validate_json(msg.data.decode())
        if not event.scope or event.scope.worker != self._worker_id:
            return
        result = event.payload.get("result", {})
        self._llm_future.set_result(result)


async def run_worker() -> None:
    worker = SubagentWorker()
    await worker.run()

