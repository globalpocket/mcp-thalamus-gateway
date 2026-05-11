from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class GatewayConfig:
    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    llm_path: str = os.getenv("LLM_PATH", "/v1/chat/completions")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    workspace_root: str = os.getenv("WORKSPACE_ROOT", "./.workspaces")
    subagent_image: str = os.getenv("SUBAGENT_IMAGE", "thalamus-subagent:dev")

