"""Data Steward:确定性证据分发 agent(不走 LLM)。

被 @到时识别 ticker,产出 Evidence Pack,同一条消息 @Bull @Bear(并行盲评)+ @Chair。
不走 LLM 的原因:硬性约束禁止编造证据,让模型转述只会引入失真。

两种证据来源(.env 的 DATA_SOURCE 切换):
- finnhub(默认):counterpoint.evidence.build_pack 拉真实数据;失败则报错中止,
  **绝不退回假数据顶替**(静默 stub 会污染接地)。成功则存快照供审计。
- stub:贴 data/evidence/<TICKER>.stub.md,离线/额度耗尽时的可砍回退。

运行:uv run python -m counterpoint.agents.data_steward
"""

import asyncio
import logging
import os
import re
from datetime import date
from pathlib import Path

from band.core import SimpleAdapter

from counterpoint.evidence import EvidenceError, build_pack
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

# 从 Chair/人类消息里抽 ticker:1–5 个大写字母,排除常见非代码缩写
_TICKER_RE = re.compile(r"\b([A-Z]{1,5})\b")
_STOP = {"AI", "PM", "US", "EU", "DOJ", "TAC", "TTM", "ROE", "EPS", "P", "E", "PE", "CEO", "CFO", "IPO"}


def extract_ticker(content: str) -> str | None:
    for m in _TICKER_RE.findall(content):
        if m not in _STOP:
            return m
    return None


def find_stub(content: str) -> tuple[str, str] | None:
    """stub 模式:匹配 data/evidence/<TICKER>.stub.md。"""
    for f in sorted(EVIDENCE_DIR.glob("*.stub.md")):
        ticker = f.name.split(".")[0]
        if re.search(rf"\b{ticker}\b", content, re.IGNORECASE):
            return ticker, f.read_text(encoding="utf-8")
    return None


def save_snapshot(ticker: str, pack: str) -> None:
    """真实 pack 存快照,留证据留痕(配合 git 可追溯)。"""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / f"{ticker}-{date.today().isoformat()}.md").write_text(pack, encoding="utf-8")


class EvidenceAdapter(SimpleAdapter):
    """@到即出证据,无 LLM、无状态。"""

    async def on_message(self, msg, tools, history, participants_msg, contacts_msg,
                         *, is_session_bootstrap, room_id) -> None:
        source = os.getenv("DATA_SOURCE", "finnhub").lower()
        requester = msg.sender_name or "Chair"

        if source == "stub":
            found = find_stub(msg.content)
            if found is None:
                avail = [f.name.split(".")[0] for f in sorted(EVIDENCE_DIR.glob("*.stub.md"))]
                await tools.send_message(
                    f"未识别到可用 ticker。stub 模式当前可用:{', '.join(avail) or '(无)'}",
                    mentions=[requester],
                )
                return
            ticker, pack = found
        else:
            ticker = extract_ticker(msg.content)
            if not ticker:
                await tools.send_message(
                    "未在消息中识别到股票代码(ticker),请用大写代码,如 AAPL。",
                    mentions=[requester],
                )
                return
            try:
                ticker, pack = build_pack(ticker)
                save_snapshot(ticker, pack)
            except EvidenceError as e:
                # 失败报错中止:不 @分析师,绝不用假数据顶替
                logging.warning("真实数据获取失败:%s", e)
                await tools.send_message(
                    f"无法获取 {ticker} 的真实数据:{e}。本轮中止——请检查 ticker 或 FINNHUB_API_KEY,"
                    f"或临时切 DATA_SOURCE=stub。",
                    mentions=[requester],
                )
                return

        logging.info("分发 %s Evidence Pack(来源=%s,@%s)", ticker, source, " @".join(ANALYST_MENTIONS))
        await tools.send_message(DELIVERY_TEMPLATE.format(pack=pack), mentions=ANALYST_MENTIONS)


if __name__ == "__main__":
    asyncio.run(
        serve(
            "data_steward",
            EvidenceAdapter(),
            f"Data Steward 已连接 Band(DATA_SOURCE={os.getenv('DATA_SOURCE', 'finnhub')},无 LLM)",
        )
    )
