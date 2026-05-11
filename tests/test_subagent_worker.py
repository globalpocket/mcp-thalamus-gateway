import asyncio

import pytest

from schemas.events import EventScope, make_event
from subagent.worker import SubagentWorker


class _Msg:
    def __init__(self, data: bytes):
        self.data = data


class _Nats:
    def __init__(self):
        self.published = []
        self.subscriptions = {}

    async def connect(self, url):
        self.url = url

    async def subscribe(self, subject, cb):
        self.subscriptions[subject] = cb

    async def publish(self, subject, data):
        self.published.append((subject, data))


@pytest.mark.asyncio
async def test_subagent_ignores_other_worker(monkeypatch):
    # 他worker向けのtask.assignイベントを無視し、publishしないことを検証する
    w = SubagentWorker()
    w._worker_id = "wk-1"
    w._task_id = "task-1"
    w._session_id = "s1"
    w._nats = _Nats()

    evt = make_event(
        "runtime.task.assign",
        source="runtime.supervisor",
        payload={"objective": "x"},
        scope=EventScope(worker="wk-2", task="task-2", session="s2"),
    )
    await w._on_task_assign(_Msg(evt.model_dump_json().encode()))
    assert w._nats.published == []


@pytest.mark.asyncio
async def test_subagent_full_flow_publish_result_and_exit(monkeypatch):
    # 自worker向けtask.assign受信後、llm.request→task.result→agent.exitを順にpublishすることを検証する
    w = SubagentWorker()
    w._worker_id = "wk-1"
    w._task_id = "task-1"
    w._session_id = "s1"
    w._nats = _Nats()

    evt = make_event(
        "runtime.task.assign",
        source="runtime.supervisor",
        payload={"objective": "hello"},
        scope=EventScope(worker="wk-1", task="task-1", session="s1"),
    )

    task = asyncio.create_task(w._on_task_assign(_Msg(evt.model_dump_json().encode())))
    await asyncio.sleep(0.01)
    assert w._nats.published[0][0] == "runtime.llm.request"

    response_evt = make_event(
        "runtime.llm.response",
        source="runtime.gateway",
        payload={"result": {"summary": "ok"}},
        scope=EventScope(worker="wk-1", task="task-1", session="s1"),
    )
    await w._on_llm_response(_Msg(response_evt.model_dump_json().encode()))
    await task

    subjects = [x[0] for x in w._nats.published]
    assert "runtime.task.result" in subjects
    assert "runtime.agent.exit" in subjects


@pytest.mark.asyncio
async def test_subagent_run_subscribes(monkeypatch):
    # run実行時に必要な購読（task.assign/llm.response）が登録されることを検証する
    w = SubagentWorker()
    n = _Nats()
    w._nats = n

    async def _stop_wait(self):
        raise RuntimeError("stop")

    monkeypatch.setattr(asyncio.Event, "wait", _stop_wait, raising=True)
    with pytest.raises(RuntimeError):
        await w.run()

    assert "runtime.task.assign" in n.subscriptions
    assert "runtime.llm.response" in n.subscriptions
