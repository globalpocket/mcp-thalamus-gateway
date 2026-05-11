from gateway.config import GatewayConfig


def test_gateway_config_defaults(monkeypatch):
    monkeypatch.delenv("NATS_URL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_PATH", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("SUBAGENT_IMAGE", raising=False)

    c = GatewayConfig()
    assert c.nats_url == "nats://localhost:4222"
    assert c.llm_base_url.startswith("http://")


def test_gateway_config_env(monkeypatch):
    monkeypatch.setenv("NATS_URL", "nats://example:4222")
    monkeypatch.setenv("LLM_BASE_URL", "http://llm")
    monkeypatch.setenv("LLM_PATH", "/v1/test")
    monkeypatch.setenv("LLM_MODEL", "dummy")
    monkeypatch.setenv("WORKSPACE_ROOT", "/tmp/ws")
    monkeypatch.setenv("SUBAGENT_IMAGE", "img:test")

    c = GatewayConfig()
    assert c.nats_url == "nats://example:4222"
    assert c.llm_base_url == "http://llm"
    assert c.llm_path == "/v1/test"
    assert c.llm_model == "dummy"
    assert c.workspace_root == "/tmp/ws"
    assert c.subagent_image == "img:test"

