"""Data Steward:确定性证据分发 agent(不走 LLM)。

被 @到时从消息里识别 ticker,把 data/evidence/<TICKER>.stub.md 原样贴进房间,
同一条消息 @Bull(开始分析)+ @Chair(送达通知)。
不走 LLM 的原因:硬性约束禁止编造证据,stub 阶段让模型转述只会引入失真;
同一条消息 @多个分析师 = Band 的并行盲评机制,M2 加 Bear 时只改 mentions 列表。

运行:uv run python -m counterpoint.agents.data_steward
"""

import asyncio
import logging
import re
from pathlib import Path

from band import Agent
from band.core import SimpleAdapter
from band.config import load_agent_config

from counterpoint.config import platform_urls

EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "data" / "evidence"

# Evidence Pack 送达消息:pack 原文 + 给各角色的指令。
# 文本里的 @名字 是给人类读的;真正的路由靠 send_message 的 mentions 参数。
DELIVERY_TEMPLATE = """{pack}

---
@Bull 请仅基于以上 Evidence Pack 独立完成多头分析,结论发回房间并 @Chair。
@Chair Evidence Pack 已送达,请等待分析结论。"""

ANALYST_MENTIONS = ["Bull", "Chair"]  # M2 加 Bear:插到列表里即并行盲评


def find_pack(content: str) -> tuple[str, str] | None:
    """在消息里找能匹配到证据文件的 ticker,返回 (ticker, pack 原文)。"""
    for f in sorted(EVIDENCE_DIR.glob("*.stub.md")):
        ticker = f.name.split(".")[0]
        if re.search(rf"\b{ticker}\b", content, re.IGNORECASE):
            return ticker, f.read_text(encoding="utf-8")
    return None


class StubEvidenceAdapter(SimpleAdapter):
    """@到即贴证据,无 LLM、无状态。"""

    async def on_message(
        self,
        msg,
        tools,
        history,
        participants_msg,
        contacts_msg,
        *,
        is_session_bootstrap,
        room_id,
    ) -> None:
        found = find_pack(msg.content)
        if found is None:
            available = [f.name.split(".")[0] for f in sorted(EVIDENCE_DIR.glob("*.stub.md"))]
            # Band 要求每条消息至少 @一个人,回给请求方
            await tools.send_message(
                f"未在消息中识别到可用 ticker。当前有 stub 证据的:{', '.join(available)}",
                mentions=[msg.sender_name or "Chair"],
            )
            return

        ticker, pack = found
        logging.info("分发 %s Evidence Pack(@%s)", ticker, " @".join(ANALYST_MENTIONS))
        await tools.send_message(
            DELIVERY_TEMPLATE.format(pack=pack),
            mentions=ANALYST_MENTIONS,
        )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    agent_id, api_key = load_agent_config("data_steward")
    ws_url, rest_url = platform_urls()
    agent = Agent.create(
        adapter=StubEvidenceAdapter(),
        agent_id=agent_id,
        api_key=api_key,
        ws_url=ws_url,
        rest_url=rest_url,
    )
    logging.info("Data Steward 已连接 Band(确定性 stub 模式,无 LLM)")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
