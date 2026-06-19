#!/usr/bin/env python3
"""从一轮真实研究的产物拼出 demo fixture(供 WEB_DEMO 后端回放 + 纯前端 demo)。

素材:
  data/rooms/<TICKER>.json   —— 房间消息快照(签字后清场时落盘,见 web/app.py)
  memos/<TICKER>-<日期>.md    —— 研究备忘录(取最新一份,或 --date 指定)

产出(同一份内容写两处,保持后端/前端一致):
  counterpoint/web/fixtures/demo.json        —— 后端 WEB_DEMO 用
  counterpoint/web/ui/src/demo-fixture.json  —— 前端纯客户端 demo 打包用

处理:第 0 条触发消息(Data Steward 以房主身份代发的 "research X")还原成人类发起;
备忘录去掉尾部签字区块(demo 的签字由 UI 模拟)。

用法:
  uv run python scripts/build_demo_fixture.py NVDA
  uv run python scripts/build_demo_fixture.py AAPL --date 2026-06-18 --human "Chrowder"
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOMS_DIR = ROOT / "data" / "rooms"
MEMOS_DIR = ROOT / "memos"
OUT_PATHS = [
    ROOT / "counterpoint" / "web" / "fixtures" / "demo.json",
    ROOT / "counterpoint" / "web" / "ui" / "src" / "demo-fixture.json",
]

_RATINGS = ("Buy", "Overweight", "Hold", "Underweight", "Sell")
# 签字区块的两种语言标题(record_signoff 追加),从这里之后整段砍掉
_SIGNOFF_RE = re.compile(r"\n+---\n+##\s*(?:Sign-off Record|签字记录)")
# 触发消息识别:research/研究 + ticker(大小写不敏感)
_TRIGGER_RE = re.compile(r"(?:research|研究)\s+", re.IGNORECASE)


def _latest_memo(ticker: str, date: str | None) -> Path:
    if date:
        p = MEMOS_DIR / f"{ticker}-{date}.md"
        if not p.exists():
            sys.exit(f"找不到备忘录 {p}")
        return p
    files = sorted(MEMOS_DIR.glob(f"{ticker}-*.md"))
    if not files:
        sys.exit(f"{MEMOS_DIR} 下没有 {ticker}-*.md;先跑一轮研究产出备忘录。")
    return max(files, key=lambda p: p.stat().st_mtime)


def _parse_rating(memo: str) -> str:
    m = re.search(rf"##\s*(?:Rating|评级)\s*\n+\**\s*({'|'.join(_RATINGS)})", memo)
    if m:
        return m.group(1)
    m = re.search(rf"\b({'|'.join(_RATINGS)})\b", memo)  # 兜底:正文首个评级词
    return m.group(1) if m else "Hold"


def build(ticker: str, date: str | None, human: str) -> tuple[dict, Path]:
    ticker = ticker.upper()
    snap = ROOMS_DIR / f"{ticker}.json"
    if not snap.exists():
        sys.exit(f"找不到房间快照 {snap};该轮需经 web 跑完并签字清场后才会落盘。")
    messages = json.loads(snap.read_text(encoding="utf-8"))
    if not messages:
        sys.exit(f"{snap} 为空。")

    memo_path = _latest_memo(ticker, date)
    memo = _SIGNOFF_RE.split(memo_path.read_text(encoding="utf-8"))[0].rstrip() + "\n"
    rating = _parse_rating(memo)

    # 第 0 条若是 Data Steward 代发的触发消息,还原成人类发起
    first = messages[0]
    if first.get("sender") == "Data Steward" and _TRIGGER_RE.search(first.get("content", "")):
        first["sender"] = human
        first["sender_type"] = "User"

    # 只保留 fixture 需要的字段
    msgs = [
        {
            "sender": m.get("sender"),
            "sender_type": m.get("sender_type"),
            "type": m.get("type", "text"),
            "content": m.get("content", ""),
            "at": m.get("at", ""),
        }
        for m in messages
    ]
    return {"ticker": ticker, "rating": rating, "messages": msgs, "memo_markdown": memo}, memo_path


def main() -> None:
    ap = argparse.ArgumentParser(description="从真实跑的产物拼 demo fixture")
    ap.add_argument("ticker", help="股票代码,如 NVDA")
    ap.add_argument("--date", help="指定备忘录日期(YYYY-MM-DD),默认取最新")
    ap.add_argument("--human", default="Chrowder", help="发起人显示名(默认 Chrowder)")
    args = ap.parse_args()

    fixture, memo_path = build(args.ticker, args.date, args.human)
    blob = json.dumps(fixture, ensure_ascii=False)
    for p in OUT_PATHS:
        p.write_text(blob, encoding="utf-8")

    senders = [m["sender"] for m in fixture["messages"]]
    print(f"✅ {fixture['ticker']} demo fixture 已生成")
    print(f"   评级:{fixture['rating']}  | 消息 {len(senders)} 条:{senders}")
    print(f"   备忘录:{memo_path.name}(已去签字块,{len(fixture['memo_markdown'])} 字)")
    print("   写入:")
    for p in OUT_PATHS:
        print(f"     - {p.relative_to(ROOT)}")
    print("   下一步:cd counterpoint/web/ui && npm run build(让前端 demo 用上新 fixture)")


if __name__ == "__main__":
    main()
