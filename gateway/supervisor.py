from __future__ import annotations

import os
from pathlib import Path

import docker

from gateway.config import GatewayConfig


class Supervisor:
    def __init__(self, config: GatewayConfig) -> None:
        self._config = config
        self._docker = docker.from_env()
        self._containers: dict[str, str] = {}

    def spawn(self, task_id: str, worker_id: str, session_id: str | None = None) -> tuple[str, str]:
        workspace_path = Path(self._config.workspace_root) / task_id
        workspace_path.mkdir(parents=True, exist_ok=True)

        container_name = f"thalamus-worker-{worker_id}"
        env = {
            "NATS_URL": self._config.nats_url,
            "WORKER_ID": worker_id,
            "TASK_ID": task_id,
            "SESSION_ID": session_id or "",
        }
        self._docker.containers.run(
            self._config.subagent_image,
            detach=True,
            name=container_name,
            environment=env,
            volumes={os.path.abspath(workspace_path): {"bind": "/workspace", "mode": "rw"}},
            auto_remove=True,
        )
        self._containers[worker_id] = container_name
        return container_name, str(workspace_path)

    def terminate(self, worker_id: str) -> None:
        container_name = self._containers.pop(worker_id, None)
        if not container_name:
            return
        try:
            container = self._docker.containers.get(container_name)
            container.stop(timeout=5)
        except docker.errors.NotFound:
            return

