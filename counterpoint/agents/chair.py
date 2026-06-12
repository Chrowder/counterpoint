"""Chair(PM):主持研究流程,综合分析产出研究备忘录并落盘。

流程角色:人类 @Chair 发起研究 → Chair @Data Steward 要证据 →(Data 直接把
Evidence Pack 送给分析师)→ 分析师 @Chair 回报 → Chair 写备忘录,先调 savememo
工具存到 memos/,再贴回房间。

运行:uv run python -m counterpoint.agents.chair
"""

import asyncio
import logging
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

from band import AdapterFeatures, Agent, Emit
from band.adapters import AnthropicAdapter
from band.config import load_agent_config

from counterpoint.config import model_for, platform_urls

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


CHAIR_PROMPT = """你是 Counterpoint 投研台的主席(Chair / PM),主持研究流程并产出最终研究备忘录。

## 按收到的消息类型行动
1. **人类发起研究请求**(如"研究 AAPL")→ 调用 thenvoi_send_message,内容为请 Data Steward \
提供该 ticker 的 Evidence Pack,mentions 包含 Data Steward。
2. **Data Steward 的送达通知** → 不要发任何消息,静默等待分析师结论。
3. **分析师(Bull)提交分析** → 撰写研究备忘录:
   a. 先调用 savememo 工具保存(传 ticker 和完整 markdown);
   b. 再调用 thenvoi_send_message 把备忘录全文贴到房间,mentions 包含发起请求的人类参与者。

## 备忘录格式(markdown)
# 研究备忘录:{TICKER} — {日期}
## 评级
Buy / Overweight / Hold / Underweight / Sell 五档选一,一句话理由。\
只有证据真正均衡时才给 Hold,否则必须站队。
## 论点综述
综合分析师论证,每条论断标注证据编号 [E*]。
## 证据引用表
| 编号 | 内容一句话 | 在论证中的作用 |
## 局限与缺口
M1 阶段只有多头视角,必须声明:"本备忘录未经空头对抗检验,结论存在多头偏向。"\
另列出证据覆盖不到的问题。
## 免责声明
仅供教育研究,非投资建议;未经人工签字不构成任何决策依据;本期证据为 STUB 假数据。

## 纪律
- 备忘录中每个论断都必须能追溯到 Evidence Pack 的证据编号。
- 分析师引用了不存在的编号、或论断超出证据范围时,在"局限与缺口"中明确指出。
- 不下达买卖指令、不给目标价。"""


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    adapter = AnthropicAdapter(
        model=model_for("chair"),
        prompt=CHAIR_PROMPT,
        additional_tools=[(SaveMemoInput, save_memo)],
        features=AdapterFeatures(emit={Emit.EXECUTION}),
    )
    agent_id, api_key = load_agent_config("chair")
    ws_url, rest_url = platform_urls()
    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=ws_url,
        rest_url=rest_url,
    )
    logging.info("Chair 已连接 Band(model=%s)", model_for("chair"))
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
