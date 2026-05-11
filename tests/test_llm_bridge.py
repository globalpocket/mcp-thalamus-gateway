import pytest

from gateway.config import GatewayConfig
from gateway.llm_bridge import LLMBridge


class _Resp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class _Client:
    def __init__(self, *args, **kwargs):
        self.last_url = None
        self.last_json = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json):
        self.last_url = url
        self.last_json = json
        return _Resp({"ok": True, "echo": json})


@pytest.mark.asyncio
async def test_llm_bridge_infer(monkeypatch):
    # LLMBridgeが指定URLへPOSTし、レスポンスJSONをそのまま返すことを検証する
    import gateway.llm_bridge as mod

    client = _Client()
    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda timeout=60.0: client)

    cfg = GatewayConfig(llm_base_url="http://llm", llm_path="/v1/chat/completions", llm_model="m")
    b = LLMBridge(cfg)
    out = await b.infer("hello", session="s1")

    assert out["ok"] is True
    assert client.last_url == "http://llm/v1/chat/completions"
    assert client.last_json["model"] == "m"
