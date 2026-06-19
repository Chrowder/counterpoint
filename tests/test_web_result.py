"""web.result.latest_result 测试:只读 memos/ + audit,无网络。"""

import json

from counterpoint.web import result


def _setup(tmp_path, memo_name, memo_text, audit_entries):
    memos = tmp_path / "memos"
    memos.mkdir()
    (memos / memo_name).write_text(memo_text, encoding="utf-8")
    audit = tmp_path / "signoff.jsonl"
    audit.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in audit_entries) + "\n")
    return memos, audit


def test_not_found(tmp_path):
    memos = tmp_path / "memos"; memos.mkdir()
    out = result.latest_result("AAPL", memos_dir=memos, audit_path=tmp_path / "none.jsonl")
    assert out == {"found": False, "ticker": "AAPL"}


def test_found_unsigned(tmp_path):
    memos, audit = _setup(tmp_path, "AAPL-2026-06-18.md", "# 备忘录\n评级 Hold",
                          [{"event": "memo_created", "memo_file": "AAPL-2026-06-18.md",
                            "rating": "Hold", "reflection": "上次条件未触发"}])
    out = result.latest_result("aapl", memos_dir=memos, audit_path=audit)
    assert out["found"] and out["rating"] == "Hold" and out["reflection"] == "上次条件未触发"
    assert out["signed"] is False and "备忘录" in out["markdown"]


def test_found_signed(tmp_path):
    memos, audit = _setup(tmp_path, "TSLA-2026-06-18.md", "# m",
                          [{"event": "memo_created", "memo_file": "TSLA-2026-06-18.md", "rating": "Hold"},
                           {"event": "signed", "memo_file": "TSLA-2026-06-18.md",
                            "decision": "APPROVE", "signer": "Chrowder", "comments": "盯 Azure"}])
    out = result.latest_result("TSLA", memos_dir=memos, audit_path=audit)
    assert out["signed"] is True and out["decision"] == "APPROVE"
    assert out["signer"] == "Chrowder" and out["comments"] == "盯 Azure"


def test_since_filters_stale_memo(tmp_path):
    """旧备忘录早于本轮发起时刻 → 视为'本轮还没结果'(found=False),避免显示上一轮遗留。"""
    memos, audit = _setup(tmp_path, "AAPL-2026-06-12.md", "# 旧备忘录", [])
    stale_mtime = memos.joinpath("AAPL-2026-06-12.md").stat().st_mtime
    # 本轮发起时刻在旧备忘录之后
    out = result.latest_result("AAPL", memos_dir=memos, audit_path=audit, since=stale_mtime + 100)
    assert out == {"found": False, "ticker": "AAPL"}
    # 不设 since 则照常返回(查看模式)
    assert result.latest_result("AAPL", memos_dir=memos, audit_path=audit)["found"] is True


def test_picks_latest_by_mtime(tmp_path):
    import os, time
    memos = tmp_path / "memos"; memos.mkdir()
    (memos / "AMD-2026-06-10.md").write_text("old", encoding="utf-8")
    time.sleep(0.01)
    (memos / "AMD-2026-06-16.md").write_text("new", encoding="utf-8")
    out = result.latest_result("AMD", memos_dir=memos, audit_path=tmp_path / "none.jsonl")
    assert out["markdown"] == "new" and out["memo_file"] == "AMD-2026-06-16.md"
