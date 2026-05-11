from __future__ import annotations

import json
from typing import Any, Callable, List


try:
    from runtime.runtime import NatsBus as RuntimeNatsBus
except Exception:  # pragma: no cover
    RuntimeNatsBus = None


class FallbackNatsBus:
    def __init__(self, servers: List[str]):
        from nats.aio.client import Client as NATS

        self.servers = servers
        self.nc = NATS()

    async def connect(self) -> None:
        await self.nc.connect(servers=self.servers)

    async def close(self) -> None:
        await self.nc.close()

    async def publish(self, subject: str, payload: bytes) -> None:
        await self.nc.publish(subject, payload)

    async def subscribe(self, subject: str, handler: Callable[[str, dict[str, Any]], Any]) -> None:
        async def wrapped(msg: Any) -> None:
            payload = json.loads(msg.data.decode())
            await handler(msg.subject, payload)

        await self.nc.subscribe(subject, cb=wrapped)


def create_nats_bus(servers: List[str]):
    if RuntimeNatsBus is not None:
        return RuntimeNatsBus(servers=servers)
    return FallbackNatsBus(servers=servers)

