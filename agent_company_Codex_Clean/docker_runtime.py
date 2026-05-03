from __future__ import annotations

import asyncio

import main as runtime_main
import settings
from agents.ceo import CEOAgent
from core import browser as browser_module
from core.db import init_managers_db
from core.runtime import RUNTIME


async def run() -> None:
    runtime_main.setup_logging()
    settings._validate()

    await init_managers_db()
    await runtime_main.ensure_active_chat_session()

    ceo = CEOAgent()
    await RUNTIME.spawn(ceo)

    poller = asyncio.create_task(runtime_main.web_action_poller())
    try:
        await asyncio.Event().wait()
    finally:
        poller.cancel()
        await RUNTIME.stop_all()
        await browser_module.shutdown_all()


if __name__ == "__main__":
    asyncio.run(run())
