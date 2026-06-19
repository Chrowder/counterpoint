"""Counterpoint Web 前端后端:网页输入 ticker → 后台建房+发起 → 轮询展示备忘录 → 签字 → 清场。

agent 进程须另行常驻(./scripts/run_desk.sh)。本服务只负责编排与展示。
运行:uv run uvicorn counterpoint.web.app:app --reload
"""

import json
import os
import re
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from counterpoint.agents.chair import RecordSignoffInput, record_signoff
from counterpoint.web import demo, desk
from counterpoint.web.progress import derive_progress
from counterpoint.web.result import latest_result

# WEB_DEMO=1:离线回放 fixture,不连 Band/agent/LLM,供前端零成本调试
DEMO = os.getenv("WEB_DEMO", "").lower() in ("1", "true", "yes")

STATIC = Path(__file__).resolve().parent / "static"
STATE_FILE = Path(__file__).resolve().parents[2] / ".web_rooms.json"  # 进行中房间,gitignored

app = FastAPI(title="Counterpoint Desk")


def _load_rooms() -> dict[str, str]:
    """ticker(大写)→ room_id。落盘以便服务重启后仍能清场(否则死房间泄漏 → 轮询负载累积)。"""
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_rooms(rooms: dict[str, str]) -> None:
    STATE_FILE.write_text(json.dumps(rooms, ensure_ascii=False), encoding="utf-8")


_rooms: dict[str, str] = _load_rooms()
# 每轮研究的发起时刻(epoch);仅内存——用于让 /api/result 只认本轮之后产出的备忘录,
# 避免显示上一轮遗留的旧备忘录。重启丢失只是退化为"显示最新备忘录",可接受。
_started: dict[str, float] = {}


class ResearchReq(BaseModel):
    ticker: str


class SignoffReq(BaseModel):
    ticker: str
    decision: str
    signer: str            # 真实人类签字人,必填——记入审计留痕,不可由 agent 代填
    comments: str = ""


@app.post("/api/research")
def research(req: ResearchReq):
    ticker = req.ticker.strip().upper()
    # 只收 1–5 位英文代码:中文公司名会被 Chair 译成代码(如 微软→MSFT),
    # 备忘录按代码命名,而前端按输入名查找 → 对不上。入口挡掉,避免错配。
    if not re.fullmatch(r"[A-Z]{1,5}", ticker):
        return {"ok": False, "error": "请输入 1–5 位英文股票代码(如 AAPL / MSFT),不要用中文公司名"}
    if DEMO:
        demo.start(ticker)
        return {"ticker": ticker, "room_id": "DEMO", "status": "started"}
    _started[ticker] = time.time()  # 先记发起时刻,确保只认此后产出的备忘录
    room_id = desk.start_research(ticker)
    _rooms[ticker] = room_id
    _save_rooms(_rooms)
    return {"ticker": ticker, "room_id": room_id, "status": "started"}


@app.get("/api/result/{ticker}")
def result(ticker: str):
    ticker = ticker.strip().upper()
    if DEMO:
        return demo.result(ticker)
    return latest_result(ticker, since=_started.get(ticker))


def _messages_for(ticker: str) -> list[dict]:
    room_id = _rooms.get(ticker)
    if not room_id:
        return []
    try:
        return desk.room_messages(room_id)
    except Exception:
        return []  # 房间已清场/网络抖动:返回空,前端按"无消息"处理


@app.get("/api/progress/{ticker}")
def progress(ticker: str):
    """流水线进度(6 阶段),驱动前端时间线。"""
    ticker = ticker.strip().upper()
    if DEMO:
        return {"ticker": ticker, "stages": demo.progress(ticker)}
    res = latest_result(ticker, since=_started.get(ticker))
    return {
        "ticker": ticker,
        "stages": derive_progress(_messages_for(ticker), memo_done=res.get("found", False),
                                  signed=res.get("signed", False)),
    }


@app.get("/api/room/{ticker}")
def room(ticker: str):
    """房间消息原文,供前端原生直播 agent 协作(替代无法 iframe 的 Band 页面)。"""
    ticker = ticker.strip().upper()
    if DEMO:
        return {"ticker": ticker, "messages": demo.room(ticker)}
    return {"ticker": ticker, "messages": _messages_for(ticker)}


@app.post("/api/signoff")
def signoff(req: SignoffReq):
    ticker = req.ticker.strip().upper()
    signer = req.signer.strip()
    if not signer:
        return {"ok": False, "error": "请填写签字人姓名(人工签字门需真实署名)"}
    if DEMO:
        return demo.signoff(ticker, req.decision, signer)
    # 直接落库:签字人取自网页表单的真实人名,绕开 agent 代发(否则签字人会被记成 agent)
    msg = record_signoff(
        RecordSignoffInput(ticker=ticker, decision=req.decision, signer=signer, comments=req.comments)
    )
    ok = "已记录" in msg
    return {"ok": ok, "message": msg}


@app.post("/api/cleanup/{ticker}")
def cleanup(ticker: str):
    ticker = ticker.strip().upper()
    if DEMO:
        demo.cleanup(ticker)
        return {"ok": True, "room_id": "DEMO"}
    _started.pop(ticker, None)
    room_id = _rooms.pop(ticker, None)
    if room_id:
        desk.teardown(room_id)
        _save_rooms(_rooms)
    return {"ok": True, "room_id": room_id}


UI_DIST = Path(__file__).resolve().parent / "ui" / "dist"  # Vite 构建产物(npm run build)

if (UI_DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=UI_DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(UI_DIST / "index.html")

    @app.get("/favicon.svg")
    def favicon():
        return FileResponse(UI_DIST / "favicon.svg")
else:
    # 未构建 UI 时回退到旧单页(也便于纯后端调试)
    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
