from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional
from uuid import uuid4

from gateway.bus_adapter import create_nats_bus
from gateway.config import GatewayConfig
from gateway.llm_bridge import LLMBridge
from gateway.supervisor import Supervisor
from schemas.events import EventRefs, EventScope, RuntimeEvent, make_event


class NatsGateway:
    """Thalamus runtime の NatsBus を利用する Gateway 実装。"""

    def __init__(self, config: GatewayConfig) -> None:
        self._config = config
        self._bus = create_nats_bus(servers=[self._config.nats_url])
        self._llm = LLMBridge(config)
        self._supervisor = Supervisor(config)
        self._results: Dict[str, Dict[str, Any]] = {}

    async def start(self) -> None:
        await self._bus.connect()
        await self._bus.subscribe("runtime.llm.request", self._on_llm_request)
        await self._bus.subscribe("runtime.task.result", self._on_task_result)
        await self._bus.subscribe("runtime.agent.exit", self._on_agent_exit)

    async def assign_task(self, objective: str, session_id: Optional[str] = None) -> Dict[str, Any]:
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
        await self._bus.publish(event.type, json.dumps(event.model_dump()).encode())

    async def _on_llm_request(self, subject: str, event_payload: Dict[str, Any]) -> None:
        _ = subject
        event = RuntimeEvent.model_validate(event_payload)
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

    async def _on_task_result(self, subject: str, event_payload: Dict[str, Any]) -> None:
        _ = subject
        event = RuntimeEvent.model_validate(event_payload)
        task_id = event.scope.task if event.scope else None
        if task_id:
            self._results[task_id] = event.payload

    async def _on_agent_exit(self, subject: str, event_payload: Dict[str, Any]) -> None:
        _ = subject
        event = RuntimeEvent.model_validate(event_payload)
        worker_id = event.scope.worker if event.scope else None
        if worker_id:
            self._supervisor.terminate(worker_id)
