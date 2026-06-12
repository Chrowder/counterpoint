"""公共启动逻辑:读凭据 → Agent.create → 持久 WebSocket 监听。"""

import logging

from band import Agent
from band.config import load_agent_config

from counterpoint.config import platform_urls


async def serve(role: str, adapter, banner: str) -> None:
    logging.basicConfig(level=logging.INFO)
    agent_id, api_key = load_agent_config(role)
    ws_url, rest_url = platform_urls()
    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=ws_url,
        rest_url=rest_url,
    )
    logging.info(banner)
    await agent.run()
