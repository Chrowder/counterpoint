"""Data Steward:确定性证据分发 agent(不走 LLM)。

被 @到时从消息里识别 ticker,把 data/evidence/<TICKER>.stub.md 原样贴进房间,
同一条消息 @Bull @Bear(并行盲评)+ @Chair(送达通知)。
不走 LLM 的原因:硬性约束禁止编造证据,stub 阶段让模型转述只会引入失真。

运行:uv run python -m counterpoint.agents.data_steward
"""

import asyncio
import logging
import re
from pathlib import Path

from band.core import SimpleAdapter

from counterpoint.runner import serve

EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "data" / "evidence"

# Evidence Pack 送达消息:pack 原文 + 给各角色的指令。
# 文本里的 @名字 是给人类读的;真正的路由靠 send_message 的 mentions 参数。
# 同一条消息 @Bull @Bear = 并行盲评:两人同时开始,互相看不到对方输出。
DELIVERY_TEMPLATE = """{pack}

---
@Bull @Bear 请各自仅基于以上 Evidence Pack **独立**完成多头/空头分析(你们互相看不到对方的消息),结论发回房间并 @Chair。
@Chair Evidence Pack 已送达,请等待双方分析结论。"""

ANALYST_MENTIONS = ["Bull", "Bear", "Chair"]


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


if __name__ == "__main__":
    asyncio.run(
        serve(
            "data_steward",
            StubEvidenceAdapter(),
            "Data Steward 已连接 Band(确定性 stub 模式,无 LLM)",
        )
    )
