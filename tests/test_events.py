from schemas.events import EventScope, make_event


def test_event_envelope_fields() -> None:
    # canonical event envelopeの必須項目（id/type/source/scope）が正しく生成されることを検証する
    evt = make_event(
        "runtime.task.assign",
        source="runtime.supervisor",
        payload={"objective": "test"},
        scope=EventScope(worker="wk-1", task="task-1"),
    )
    dumped = evt.model_dump()
    assert dumped["id"].startswith("evt_")
    assert dumped["type"] == "runtime.task.assign"
    assert dumped["source"] == "runtime.supervisor"
    assert dumped["scope"]["worker"] == "wk-1"
