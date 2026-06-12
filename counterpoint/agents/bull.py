"""Bull:多头研究员。

收到 Data Steward 的 Evidence Pack 后,仅基于其中证据构建多头论证,@Chair 回报。
提示词骨架移植自 reference/TradingAgents 的 bull_researcher(成长/优势/正面信号 +
预判反方),加上 Counterpoint 的接地纪律:每条论断必须引用证据编号。

运行:uv run python -m counterpoint.agents.bull
"""

import asyncio
import logging

from band import AdapterFeatures, Agent, Emit
from band.adapters import AnthropicAdapter
from band.config import load_agent_config

from counterpoint.config import model_for, platform_urls

BULL_PROMPT = """你是 Counterpoint 投研台的多头研究员(Bull)。收到 Evidence Pack 后,\
仅基于其中列出的证据构建多头论证。

## 输出结构
1. **核心论点**(2-4 条):围绕成长潜力、竞争优势、正面信号展开,每条论断末尾标注证据编号,如 [E1][E5]。
2. **预判反方**:列出空头最可能攻击的 2-3 个点,并基于证据回应(同样标注编号)。
3. **结论**:一句话多头观点 + 信心度(高/中/低)。

## 接地纪律(违反即无效)
- 禁止使用 Evidence Pack 之外的任何事实、新闻、价格、日期;你训练记忆里的知识不算证据。
- 没有证据编号支撑的论断不许写;证据不足以支撑时,明确写"证据不足"。
- 不给出买卖指令或目标价,这是研究论证,不是交易建议。

完成分析后调用 thenvoi_send_message 把全文发回房间,mentions 必须包含 Chair。"""


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    adapter = AnthropicAdapter(
        model=model_for("bull"),
        prompt=BULL_PROMPT,
        features=AdapterFeatures(emit={Emit.EXECUTION}),
    )
    agent_id, api_key = load_agent_config("bull")
    ws_url, rest_url = platform_urls()
    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=ws_url,
        rest_url=rest_url,
    )
    logging.info("Bull 已连接 Band(model=%s)", model_for("bull"))
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
