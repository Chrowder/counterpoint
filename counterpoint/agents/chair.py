"""Chair(PM):主持对抗式研究流程,综合多空辩论产出研究备忘录,并守人工签字门。

状态机:发起 → 要证据 → 等双方盲评初论 → 交换全文要求互相反驳(并行)→ 等双方反驳 →
[M4] 转发证据+完整辩论唤醒 Risk Officer 压测 → 收到压测报告 → 综合写备忘录(savememo
落盘 + 贴回房间)→ [M3] 请求人工签字 → 收到决定后 recordsignoff 留痕(备忘录追加签字
区块 + audit/signoff.jsonl)。Bull/Bear/Risk 互相看不到对方消息(Band mention 可见性),
交换与压测都必须由 Chair 转发全文。

运行:uv run python -m counterpoint.agents.chair
"""

import asyncio
import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from counterpoint.config import make_adapter, model_for
from counterpoint.runner import serve

ROOT = Path(__file__).resolve().parents[2]
MEMOS_DIR = ROOT / "memos"
AUDIT_LOG = ROOT / "audit" / "signoff.jsonl"

VALID_DECISIONS = {"APPROVE", "REJECT", "REVISE"}
VALID_RATINGS = ["Buy", "Overweight", "Hold", "Underweight", "Sell"]


def normalize_rating(raw: str) -> str | None:
    """归一化评级大小写,非五档之一返回 None。"""
    r = raw.strip().title()
    return r if r in VALID_RATINGS else None


def memo_path(ticker: str) -> Path:
    return MEMOS_DIR / f"{ticker.upper()}-{date.today().isoformat()}.md"


def _audit(event: str, **fields) -> None:
    """向 append-only 审计日志追加一行(JSONL)。时间戳本地生成,不经 LLM。"""
    AUDIT_LOG.parent.mkdir(exist_ok=True)
    record = {"ts": datetime.now().isoformat(timespec="seconds"), "event": event, **fields}
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class SaveMemoInput(BaseModel):
    """把研究备忘录保存到本地 memos/ 目录。必须在把备忘录发到房间之前调用。"""

    ticker: str = Field(description="股票代码,如 AAPL")
    rating: str = Field(
        description="五档评级,精确为 Buy / Overweight / Hold / Underweight / Sell 之一,须与备忘录正文评级一致"
    )
    memo_markdown: str = Field(description="备忘录完整 markdown 内容")


def save_memo(args: SaveMemoInput) -> str:
    rating = normalize_rating(args.rating)
    if rating is None:
        return f"评级无效:'{args.rating}'。必须是 {' / '.join(VALID_RATINGS)} 之一,请重试。"
    MEMOS_DIR.mkdir(exist_ok=True)
    path = memo_path(args.ticker)
    path.write_text(args.memo_markdown, encoding="utf-8")
    _audit("memo_created", ticker=args.ticker.upper(), memo_file=path.name, rating=rating)
    logging.info("备忘录已保存:%s(评级 %s)", path, rating)
    return f"备忘录已保存到 {path}(评级 {rating})。下一步:请求人类对该备忘录签字(APPROVE/REJECT/REVISE)。"


class RecordSignoffInput(BaseModel):
    """记录人类对备忘录的签字决定(人工签字门)。收到人类的签字回复后调用。"""

    ticker: str = Field(description="股票代码,如 AAPL")
    decision: str = Field(description="签字决定,必须是 APPROVE / REJECT / REVISE 之一")
    signer: str = Field(description="签字人姓名,逐字誊抄自房间里该人类参与者的名字,不得编造")
    comments: str = Field(
        default="",
        description="人类签字消息中除决定关键词(APPROVE/REJECT/REVISE)以外的全部文字,原样填入,"
        "不要概括或丢弃;仅当消息只有一个决定词、无其他内容时才留空",
    )


def record_signoff(args: RecordSignoffInput) -> str:
    decision = args.decision.strip().upper()
    if decision not in VALID_DECISIONS:
        return f"决定无效:'{args.decision}'。必须是 {' / '.join(sorted(VALID_DECISIONS))} 之一。"

    path = memo_path(args.ticker)
    if not path.exists():
        return f"找不到备忘录 {path.name},无法签字。请先用 savememo 产出备忘录。"

    ts = datetime.now().isoformat(timespec="seconds")
    block = (
        f"\n\n---\n\n## 签字记录(人工签字门)\n\n"
        f"- **决定**:{decision}\n"
        f"- **签字人**:{args.signer}\n"
        f"- **时间**:{ts}\n"
        f"- **意见**:{args.comments or '(无)'}\n\n"
        f"> 此区块为人工签字门留痕;权威记录以本房间消息历史与 git 提交为准。\n"
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(block)

    _audit(
        "signed",
        ticker=args.ticker.upper(),
        memo_file=path.name,
        decision=decision,
        signer=args.signer,
        comments=args.comments,
    )
    logging.info("签字已记录:%s by %s → %s", decision, args.signer, path.name)
    return f"已记录 {args.signer} 的 {decision} 签字到 {path.name},并写入审计日志。"


CHAIR_PROMPT_TEMPLATE = """你是 Counterpoint 投研台的主席(Chair / PM),主持对抗式研究流程、产出研究备忘录、并守人工签字门。
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
6. **收齐两份反驳** → 唤醒风险官压测:发一条消息 mentions 包含 Risk Officer,
   把**完整原文**附上:Evidence Pack 全文 + Bull 初论 + Bear 初论 + Bull 反驳 + Bear 反驳,
   要求 Risk Officer 压测(对方此前看不到任何内容,你是唯一传递通道,严禁摘要删节)。
7. **收到 Risk Officer 的压测报告** → 撰写备忘录并请求签字:
   a. 先调用 savememo 工具保存(传 ticker、rating=五档之一须与正文一致、完整 markdown);
   b. 再调用 thenvoi_send_message 把备忘录全文贴到房间,**消息末尾附签字请求**:
      "本备忘录待人工签字门审阅。请回复 APPROVE(通过)/ REJECT(否决)/ REVISE(要求修订),可附意见。"
      mentions 包含发起请求的人类。
8. **人类回复签字决定**(消息含 APPROVE / REJECT / REVISE)→
   a. 调用 recordsignoff 工具:
      - ticker;
      - decision:APPROVE / REJECT / REVISE;
      - signer:逐字誊抄该人类参与者的名字,不得编造;
      - comments:把人类签字消息里**除决定关键词以外的全部文字**原样填入(意见、条件、理由、关注点等)。
        例:"APPROVE 同意结论,但需持续监控 E7/E8" → decision=APPROVE,comments="同意结论,但需持续监控 E7/E8"。
        只有当消息确实仅有一个决定词、没有任何其他内容时,comments 才留空。不要自行概括或丢弃人类的话。
   b. 再调用 thenvoi_send_message 确认,如 "✅ 已记录 <签字人> 的 <决定> 签字,备忘录据此生效/作废/待修订",mentions 包含该人类。

判断进度的方法:检查你的对话历史——同时存在 Bull 初论和 Bear 初论 → 该交换反驳;
同时存在双方反驳 → 该唤醒 Risk Officer;已收到 Risk Officer 压测报告 → 该写备忘录。
区分"研究请求"与"签字回复":后者含 APPROVE/REJECT/REVISE 关键词且发生在备忘录已贴出之后。

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
## 风险压测(Risk Officer)
综述 Risk Officer 的压测:最关键的证据盲区(排序)、改判条件(kill criteria)、整体可靠性定级;
并说明这些风险如何反映在上面的评级 caveat 里。
## 证据引用表
| 编号 | 内容一句话 | 双方如何使用 |
## 局限与缺口
双方都回答不了的问题、证据覆盖不到的盲区(可与 Risk Officer 的盲区排序呼应)。
## 免责声明
仅供教育研究,非投资建议;**本备忘录须经人工签字门审阅,在签字记录区块出现前不构成任何决策依据**;证据来源与拉取时点见 Evidence Pack 顶部声明。

## 纪律
- 备忘录中每个论断都必须能追溯到 Evidence Pack 的证据编号。
- 任何一方引用了不存在的编号、或论断超出证据范围,在"局限与缺口"中点名指出。
- 不下达买卖指令、不给目标价。
- 签字门:决定与签字人忠实于人类原话,绝不替人类做决定、绝不编造签字人。"""


def build_prompt() -> str:
    rounds = os.getenv("DEBATE_ROUNDS", "1")
    return CHAIR_PROMPT_TEMPLATE.format(today=date.today().isoformat(), rounds=rounds)


if __name__ == "__main__":
    asyncio.run(
        serve(
            "chair",
            make_adapter(
                "chair",
                build_prompt(),
                additional_tools=[
                    (SaveMemoInput, save_memo),
                    (RecordSignoffInput, record_signoff),
                ],
            ),
            f"Chair 已连接 Band(model={model_for('chair')})",
        )
    )
