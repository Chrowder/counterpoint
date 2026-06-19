"""离线 demo 回放:用一次抓取的真实房间记录(fixtures/demo.json)模拟整条流程,
不连 Band、不跑 agent、不烧 LLM——专供前端反复调试。WEB_DEMO=1 启用。

按发起后的经过时间渐进揭示消息与阶段(复用真实 derive_progress),所以进度时间线
和直播区的动画都能在零成本下验证。签字由 UI 触发(fixture 末条人类签字不自动放)。
"""

import json
import time
from pathlib import Path

from counterpoint.web.progress import derive_progress

_FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "demo.json").read_text("utf-8"))
_REVEALABLE = _FIXTURE["messages"][:7]  # 末条人类签字留给 UI
STEP_S = 3                               # 每 3 秒亮一条消息
MEMO_AT = STEP_S * len(_REVEALABLE)      # 辩论消息全亮 → 备忘录就绪

_state: dict[str, dict] = {}  # ticker -> {start, signed, decision, signer}


def start(ticker: str) -> None:
    _state[ticker] = {"start": time.time(), "signed": False, "decision": None, "signer": None}


def _elapsed(ticker: str) -> float:
    s = _state.get(ticker)
    return (time.time() - s["start"]) if s else 0.0


def _revealed(ticker: str) -> list[dict]:
    n = int(_elapsed(ticker) // STEP_S) + 1
    return _REVEALABLE[: max(0, min(n, len(_REVEALABLE)))]


def room(ticker: str) -> list[dict]:
    return _revealed(ticker)


def progress(ticker: str) -> list[dict]:
    s = _state.get(ticker)
    memo_done = bool(s) and _elapsed(ticker) >= MEMO_AT
    signed = bool(s) and s["signed"]
    return derive_progress(_revealed(ticker), memo_done=memo_done, signed=signed)


def result(ticker: str) -> dict:
    s = _state.get(ticker)
    if not s or _elapsed(ticker) < MEMO_AT:
        return {"found": False, "ticker": ticker}
    return {
        "found": True, "ticker": ticker, "memo_file": "DEMO.md",
        "markdown": _FIXTURE["memo_markdown"], "rating": _FIXTURE["rating"], "reflection": "",
        "signed": s["signed"], "decision": s["decision"], "signer": s["signer"], "comments": "",
    }


def signoff(ticker: str, decision: str, signer: str) -> dict:
    s = _state.get(ticker)
    if not s or _elapsed(ticker) < MEMO_AT:
        return {"ok": False, "error": "demo:备忘录尚未生成"}
    s.update(signed=True, decision=decision.upper(), signer=signer)
    return {"ok": True, "message": "demo 已记录(未写真实文件)"}


def cleanup(ticker: str) -> None:
    _state.pop(ticker, None)
