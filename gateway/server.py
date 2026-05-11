from __future__ import annotations

import asyncio

from gateway.config import GatewayConfig
from gateway.nats_gateway import NatsGateway


async def run_gateway() -> None:
    config = GatewayConfig()
    gateway = NatsGateway(config)
    await gateway.start()
    await asyncio.Event().wait()
