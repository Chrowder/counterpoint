"""读取某 ticker 的最新研究结果(备忘录 markdown + 审计派生的元信息)。

纯函数,只读现有产物(memos/ + audit/signoff.jsonl),便于单测、与 Band 解耦。
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEMOS_DIR = ROOT / "memos"
AUDIT_LOG = ROOT / "audit" / "signoff.jsonl"


def _latest_memo(ticker: str, memos_dir: Path) -> Path | None:
    files = list(memos_dir.glob(f"{ticker.upper()}-*.md"))
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def _audit_for(memo_file: str, audit_path: Path) -> dict:
    info: dict = {"rating": None, "reflection": "", "signed": False,
                  "decision": None, "signer": None, "comments": ""}
    if not audit_path.exists():
        return info
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("memo_file") != memo_file:
            continue
        if e.get("event") == "memo_created":
            info["rating"] = e.get("rating")
            info["reflection"] = e.get("reflection", "")
        elif e.get("event") == "signed":
            info.update(signed=True, decision=e.get("decision"),
                        signer=e.get("signer"), comments=e.get("comments", ""))
    return info


def latest_result(
    ticker: str,
    memos_dir: Path | None = None,
    audit_path: Path | None = None,
    since: float | None = None,
) -> dict:
    """返回 {found, ticker, memo_file, markdown, rating, reflection, signed, decision, signer, comments}。

    found=False 表示该 ticker 还没有(本轮的)备忘录。
    since(epoch 秒):只认此刻之后产出的备忘录——避免把上一轮的旧备忘录当成本轮结果。
    """
    memos_dir = memos_dir or MEMOS_DIR
    audit_path = audit_path or AUDIT_LOG
    memo = _latest_memo(ticker, memos_dir)
    if memo is None or (since is not None and memo.stat().st_mtime < since):
        return {"found": False, "ticker": ticker.upper()}
    info = _audit_for(memo.name, audit_path)
    return {
        "found": True,
        "ticker": ticker.upper(),
        "memo_file": memo.name,
        "markdown": memo.read_text(encoding="utf-8"),
        **info,
    }
