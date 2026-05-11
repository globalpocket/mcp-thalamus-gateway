from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from nats.aio.client import Client as NATS

from gateway.config import GatewayConfig
from gateway.llm_bridge import LLMBridge
from gateway.supervisor import Supervisor
from schemas.events import EventRefs, EventScope, RuntimeEvent, make_event


class NatsGateway:
    def __init__(self, config: GatewayConfig) -> None:
        self._config = config
        self._nats = NATS()
        self._llm = LLMBridge(config)
        self._supervisor = Supervisor(config)
        self._results: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        await self._nats.connect(self._config.nats_url)
        await self._nats.subscribe("runtime.llm.request", cb=self._on_llm_request)
        await self._nats.subscribe("runtime.task.result", cb=self._on_task_result)
        await self._nats.subscribe("runtime.agent.exit", cb=self._on_agent_exit)

    async def assign_task(self, objective: str, session_id: str | None = None) -> dict[str, Any]:
        task_id = f"task-{uuid4().hex[:8]}"
        worker_id = f"wk-{uuid4().hex[:8]}"
        _, workspace = self._supervisor.spawn(task_id=task_id, worker_id=worker_id, session_id=session_id)

        event = make_event(
            "runtime.task.assign",
            source="runtime.supervisor",
            payload={"objective": objective},
            scope=EventScope(worker=worker_id, task=task_id, session=session_id),
            refs=EventRefs(workspace=f"workspace://{task_id}", context=f"context://{session_id}" if session_id else None),
        )
        await self._publish(event)

        while task_id not in self._results:
            await asyncio.sleep(0.1)
        result = self._results.pop(task_id)
        result["workspace_path"] = workspace
        return result

    async def _publish(self, event: RuntimeEvent) -> None:
        await self._nats.publish(event.type, event.model_dump_json().encode())

    async def _on_llm_request(self, msg: Any) -> None:
        event = RuntimeEvent.model_validate_json(msg.data.decode())
        prompt = event.payload.get("prompt", "")
        llm_result = await self._llm.infer(prompt=prompt, session=event.scope.session if event.scope else None)
        response = make_event(
            "runtime.llm.response",
            source="runtime.gateway",
            payload={"result": llm_result},
            scope=event.scope,
            refs=event.refs,
        )
        await self._publish(response)

    async def _on_task_result(self, msg: Any) -> None:
        event = RuntimeEvent.model_validate_json(msg.data.decode())
        task_id = event.scope.task if event.scope else None
        if task_id:
            self._results[task_id] = event.payload

    async def _on_agent_exit(self, msg: Any) -> None:
        event = RuntimeEvent.model_validate_json(msg.data.decode())
        worker_id = event.scope.worker if event.scope else None
        if worker_id:
            self._supervisor.terminate(worker_id)

