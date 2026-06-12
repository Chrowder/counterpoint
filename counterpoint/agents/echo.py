"""M0 管道探针:连上 Band,在房间里被 @到就原样复述。

验证目标:agent_config.yaml 凭据有效、WebSocket 连得上、@mention 路由通、
回复能发回房间。与投研逻辑无关,M1 跑通后可删。

运行:uv run python -m counterpoint.agents.echo
"""

import asyncio
import logging

# band-sdk 1.0.0 起 import 名是 band(官方教程里的 thenvoi 是旧名)
from band import Agent
from band.adapters import AnthropicAdapter
from band.config import load_agent_config

from counterpoint.config import model_for, platform_urls

ECHO_PROMPT = (
    "You are Echo Probe, a pipeline test agent. When someone mentions you, "
    "reply with exactly the message you received, prefixed with 'echo: '. "
    "Do nothing else — no commentary, no extra tool calls."
)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Band 的关键行为:LLM 的普通文本输出被平台当作"内心思考",房间里没人能看到;
    # 真正的回复必须由模型调用 SDK 自动注入的 thenvoi_send_message 工具发出。
    # AnthropicAdapter 负责注入这些平台工具并在系统提示里教模型使用。
    adapter = AnthropicAdapter(
        model=model_for("echo"),
        custom_section=ECHO_PROMPT,
        # 工具调用/思考以 event 形式进房间,方便在 UI 里观察管道是否通
        enable_execution_reporting=True,
    )

    agent_id, api_key = load_agent_config("echo")  # 读项目根目录 agent_config.yaml
    ws_url, rest_url = platform_urls()
    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=ws_url,
        rest_url=rest_url,
    )

    logging.info("Echo Probe 已连接 Band,等待 @mention,Ctrl+C 退出")
    # 打开持久 WebSocket,订阅房间/参与者/联系人频道,阻塞监听
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
