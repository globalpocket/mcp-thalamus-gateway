from __future__ import annotations

from typing import Any

import httpx

from gateway.config import GatewayConfig


class LLMBridge:
    def __init__(self, config: GatewayConfig) -> None:
        self._config = config

    async def infer(self, prompt: str, session: str | None = None) -> dict[str, Any]:
        payload = {
            "model": self._config.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "metadata": {"session": session} if session else {},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._config.llm_base_url}{self._config.llm_path}",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

