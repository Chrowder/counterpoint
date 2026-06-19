"""从 Band 房间消息推导流水线进度(纯函数,可单测)。

按各 agent 发言条数粗粒度判断走到哪一步——足够驱动前端时间线,不追求精确。
memo/signed 两步靠落盘事实(备忘录文件 / 审计 signed),由调用方传入。
"""

# (key, 标题, 负责方)——固定 6 步,顺序即流水线
STAGES = [
    ("evidence", "证据就绪", "Data Steward"),
    ("theses", "多空盲评", "Bull / Bear"),
    ("rebuttal", "交换反驳", "Bull / Bear"),
    ("risk", "风险压测", "Risk Officer"),
    ("memo", "综合备忘录", "Chair"),
    ("signed", "人工签字", "人类"),
]


def _counts(messages: list[dict]) -> dict[str, int]:
    c: dict[str, int] = {}
    for m in messages:
        name = (m.get("sender") or "").strip()
        c[name] = c.get(name, 0) + 1
    return c


def derive_progress(messages: list[dict], memo_done: bool = False, signed: bool = False) -> list[dict]:
    """返回 6 个阶段 [{step,key,title,agent,status}],status ∈ pending/active/done。"""
    c = _counts(messages)
    bull, bear = c.get("Bull", 0), c.get("Bear", 0)

    st: dict[str, str] = {}
    st["evidence"] = "done" if c.get("Data Steward", 0) >= 1 else "pending"
    # 盲评:两份初论都到为 done,到一份为进行中
    st["theses"] = "done" if bull >= 1 and bear >= 1 else ("active" if bull or bear else "pending")
    # 反驳:双方都发出第二条(交换后的反驳)为 done
    st["rebuttal"] = "done" if bull >= 2 and bear >= 2 else ("active" if bull >= 2 or bear >= 2 else "pending")
    st["risk"] = "done" if c.get("Risk Officer", 0) >= 1 else "pending"
    st["memo"] = "done" if memo_done else "pending"
    st["signed"] = "done" if signed else "pending"

    events = [
        {"step": i, "key": key, "title": title, "agent": agent, "status": st[key]}
        for i, (key, title, agent) in enumerate(STAGES, start=1)
    ]
    # 把"前一步已完成、自己还 pending"的第一步标成 active(当前正在做)
    for i, e in enumerate(events):
        if e["status"] == "pending" and (i == 0 or events[i - 1]["status"] == "done"):
            e["status"] = "active"
            break
    return events
