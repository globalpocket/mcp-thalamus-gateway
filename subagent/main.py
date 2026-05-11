from __future__ import annotations

import asyncio

from subagent.worker import run_worker


if __name__ == "__main__":
    asyncio.run(run_worker())

