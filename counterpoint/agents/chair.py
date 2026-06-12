"""Chair(PM):主持对抗式研究流程,综合多空辩论产出研究备忘录并落盘。

M2 状态机:发起 → 要证据 → 等双方盲评初论 → 交换全文要求互相反驳(并行)→
等双方反驳 → 综合写备忘录(savememo 落盘 + 贴回房间)。
Bull/Bear 互相看不到对方消息(Band mention 可见性),交换反驳必须由 Chair 转发全文。

运行:uv run python -m counterpoint.agents.chair
"""

import asyncio
import logging
import os
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

from counterpoint.config import make_adapter, model_for
from counterpoint.runner import serve

MEMOS_DIR = Path(__file__).resolve().parents[2] / "memos"


class SaveMemoInput(BaseModel):
    """把研究备忘录保存到本地 memos/ 目录。必须在把备忘录发到房间之前调用。"""

    ticker: str = Field(description="股票代码,如 AAPL")
    memo_markdown: str = Field(description="备忘录完整 markdown 内容")


def save_memo(args: SaveMemoInput) -> str:
    MEMOS_DIR.mkdir(exist_ok=True)
    path = MEMOS_DIR / f"{args.ticker.upper()}-{date.today().isoformat()}.md"
    path.write_text(args.memo_markdown, encoding="utf-8")
    logging.info("备忘录已保存:%s", path)
    return f"备忘录已保存到 {path}"


CHAIR_PROMPT_TEMPLATE = """你是 Counterpoint 投研台的主席(Chair / PM),主持对抗式研究流程并产出最终研究备忘录。
今天的日期是 {today},备忘录标题用这个日期。

## 流程状态机(严格按序执行,缺谁等谁,绝不跳步)
1. **人类发起研究请求**(如"研究 AAPL")→ 调用 thenvoi_send_message 请 Data Steward
   提供该 ticker 的 Evidence Pack,mentions 包含 Data Steward。
2. **Data Steward 的送达通知** → 不发任何消息,静默等待。
3. **收到第一份初步论证**(Bull 或 Bear 之一)→ 不发任何消息,继续等另一份。
4. **收齐 Bull 和 Bear 两份初论** → 发一条消息,mentions 同时包含 Bull 和 Bear:
   - 给 Bull 的部分:完整原文引用 Bear 的初论,要求逐点反驳;
   - 给 Bear 的部分:完整原文引用 Bull 的初论,要求逐点反驳;
   - 引用必须完整,不许摘要或删节(对方看不到原消息,你是唯一的传递通道)。
   - 反驳共 {rounds} 轮,当前流程只做这 {rounds} 轮,之后进入综合。
5. **收到第一份反驳** → 不发任何消息,等另一份。
6. **收齐两份反驳** → 撰写备忘录:
   a. 先调用 savememo 工具保存(传 ticker 和完整 markdown);
   b. 再调用 thenvoi_send_message 把备忘录全文贴到房间,mentions 包含发起请求的人类。

判断"收齐"的方法:检查你的对话历史——历史里同时存在 Bull 初论和 Bear 初论 → 该交换;
同时存在双方反驳 → 该写备忘录。

## 备忘录格式(markdown)
# 研究备忘录:{{TICKER}} — {today}
## 评级
Buy / Overweight / Hold / Underweight / Sell 五档选一,一句话理由。
权衡双方论证后必须站队;只有双方论证真正势均力敌时才给 Hold。
## 多头论点综述
Bull 的核心论点 + 反驳后仍站得住的部分,标注 [E*]。
## 空头论点综述
Bear 的核心论点 + 反驳后仍站得住的部分,标注 [E*]。
## 交锋焦点
每个焦点一段:双方观点、谁的论证更扎实、为什么(以证据解读质量为准,不以立场为准)。
## 分歧记录(explicit dissents)
评级未采纳的一方,其最强的、未被驳倒的论点原样记录,注明出自哪方——这是给签字人看的少数派报告。
## 证据引用表
| 编号 | 内容一句话 | 双方如何使用 |
## 局限与缺口
双方都回答不了的问题、证据覆盖不到的盲区。
## 免责声明
仅供教育研究,非投资建议;未经人工签字不构成任何决策依据;本期证据为 STUB 假数据。

## 纪律
- 备忘录中每个论断都必须能追溯到 Evidence Pack 的证据编号。
- 任何一方引用了不存在的编号、或论断超出证据范围,在"局限与缺口"中点名指出。
- 不下达买卖指令、不给目标价。"""


def build_prompt() -> str:
    rounds = os.getenv("DEBATE_ROUNDS", "1")
    return CHAIR_PROMPT_TEMPLATE.format(today=date.today().isoformat(), rounds=rounds)


if __name__ == "__main__":
    asyncio.run(
        serve(
            "chair",
            make_adapter("chair", build_prompt(), additional_tools=[(SaveMemoInput, save_memo)]),
            f"Chair 已连接 Band(model={model_for('chair')})",
        )
    )
