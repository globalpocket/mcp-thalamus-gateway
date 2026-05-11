import asyncio

import pytest

from gateway.config import GatewayConfig
from gateway.nats_gateway import NatsGateway
from schemas.events import EventScope, make_event


class _Msg:
    def __init__(self, data: bytes):
        self.data = data


class _Nats:
    def __init__(self):
        self.published = []
        self.subscriptions = {}
        self.connected = None

    async def connect(self, url):
        self.connected = url

    async def subscribe(self, subject, cb):
        self.subscriptions[subject] = cb

    async def publish(self, subject, data):
        self.published.append((subject, data))


class _Sup:
    def __init__(self):
        self.spawned = []
        self.terminated = []

    def spawn(self, task_id, worker_id, session_id=None):
        self.spawned.append((task_id, worker_id, session_id))
        return (f"c-{worker_id}", f"/tmp/{task_id}")

    def terminate(self, worker_id):
        self.terminated.append(worker_id)


class _Llm:
    async def infer(self, prompt, session=None):
        return {"summary": f"ok:{prompt}", "session": session}


@pytest.mark.asyncio
async def test_gateway_start_subscriptions():
    # Gateway起動時に必要なNATS購読（llm.request/task.result/agent.exit）が登録されることを検証する
    gw = NatsGateway(GatewayConfig())
    gw._nats = _Nats()
    await gw.start()
    assert gw._nats.connected is not None
    assert "runtime.llm.request" in gw._nats.subscriptions
    assert "runtime.task.result" in gw._nats.subscriptions
    assert "runtime.agent.exit" in gw._nats.subscriptions


@pytest.mark.asyncio
async def test_gateway_llm_request_response_publish():
    # runtime.llm.request受信時にLLM推論を実行し、runtime.llm.responseをpublishすることを検証する
    gw = NatsGateway(GatewayConfig())
    gw._nats = _Nats()
    gw._llm = _Llm()

    evt = make_event(
        "runtime.llm.request",
        source="runtime.worker.wk-1",
        payload={"prompt": "hello"},
        scope=EventScope(worker="wk-1", task="task-1", session="s1"),
    )
    await gw._on_llm_request(_Msg(evt.model_dump_json().encode()))
    assert len(gw._nats.published) == 1
    subject, raw = gw._nats.published[0]
    assert subject == "runtime.llm.response"
    assert b"runtime.llm.response" in raw


@pytest.mark.asyncio
async def test_gateway_result_and_exit_handlers():
    # task.resultで結果が保存され、agent.exitでSupervisor.terminateが呼ばれることを検証する
    gw = NatsGateway(GatewayConfig())
    gw._nats = _Nats()
    gw._supervisor = _Sup()

    result_evt = make_event(
        "runtime.task.result",
        source="runtime.worker.wk-1",
        payload={"summary": "done"},
        scope=EventScope(worker="wk-1", task="task-1"),
    )
    await gw._on_task_result(_Msg(result_evt.model_dump_json().encode()))
    assert gw._results["task-1"]["summary"] == "done"

    exit_evt = make_event(
        "runtime.agent.exit",
        source="runtime.worker.wk-1",
        payload={"reason": "completed"},
        scope=EventScope(worker="wk-1", task="task-1"),
    )
    await gw._on_agent_exit(_Msg(exit_evt.model_dump_json().encode()))
    assert gw._supervisor.terminated == ["wk-1"]


@pytest.mark.asyncio
async def test_gateway_assign_task_waits_result(monkeypatch):
    # assign_taskがtask.assign発行後に結果到着まで待機し、workspace_path付きで返すことを検証する
    gw = NatsGateway(GatewayConfig())
    gw._nats = _Nats()
    gw._supervisor = _Sup()

    async def _later_set_result():
        await asyncio.sleep(0.02)
        task_id = gw._supervisor.spawned[0][0]
        gw._results[task_id] = {"summary": "ok"}

    t = asyncio.create_task(_later_set_result())
    out = await gw.assign_task("do x", session_id="s1")
    await t
    assert out["summary"] == "ok"
    assert out["workspace_path"].startswith("/tmp/task-")
