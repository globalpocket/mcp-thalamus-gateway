from pathlib import Path

import gateway.supervisor as mod
from gateway.config import GatewayConfig
from gateway.supervisor import Supervisor


class _Container:
    def __init__(self):
        self.stopped = False

    def stop(self, timeout=5):
        self.stopped = True


class _ContainersApi:
    def __init__(self):
        self.runs = []
        self._container = _Container()

    def run(self, *args, **kwargs):
        self.runs.append((args, kwargs))

    def get(self, name):
        return self._container


class _DockerClient:
    def __init__(self):
        self.containers = _ContainersApi()


def test_supervisor_spawn_and_terminate(monkeypatch, tmp_path: Path):
    dc = _DockerClient()
    monkeypatch.setattr(mod.docker, "from_env", lambda: dc)

    cfg = GatewayConfig(workspace_root=str(tmp_path), subagent_image="img:test")
    sp = Supervisor(cfg)
    _, workspace = sp.spawn(task_id="task-1", worker_id="wk-1", session_id="s1")

    assert Path(workspace).exists()
    assert len(dc.containers.runs) == 1

    sp.terminate("wk-1")
    assert dc.containers._container.stopped is True

