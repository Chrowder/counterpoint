"""web.progress.derive_progress 测试(纯函数)。"""

from counterpoint.web.progress import derive_progress


def _msgs(*senders):
    return [{"sender": s, "content": ""} for s in senders]


def test_empty_first_stage_active():
    stages = derive_progress([])
    assert stages[0]["key"] == "evidence" and stages[0]["status"] == "active"
    assert all(s["status"] in ("pending", "active") for s in stages)


def test_evidence_done_theses_active():
    stages = {s["key"]: s["status"] for s in derive_progress(_msgs("Data Steward"))}
    assert stages["evidence"] == "done" and stages["theses"] == "active"


def test_theses_done_after_both():
    stages = {s["key"]: s["status"] for s in derive_progress(_msgs("Data Steward", "Bull", "Bear"))}
    assert stages["theses"] == "done"
    assert stages["rebuttal"] == "active"  # 前一步完成、自己 pending → active


def test_rebuttal_needs_second_round():
    # 双方各两条 = 初论 + 反驳
    msgs = _msgs("Data Steward", "Bull", "Bear", "Bull", "Bear")
    st = {s["key"]: s["status"] for s in derive_progress(msgs)}
    assert st["rebuttal"] == "done" and st["risk"] == "active"


def test_risk_memo_signed():
    msgs = _msgs("Data Steward", "Bull", "Bear", "Bull", "Bear", "Risk Officer")
    st = {s["key"]: s["status"] for s in derive_progress(msgs, memo_done=True, signed=True)}
    assert st["risk"] == "done" and st["memo"] == "done" and st["signed"] == "done"
