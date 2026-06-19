"""chair.py 工具测试:评级校验、备忘录落盘、签字留痕。

用 monkeypatch 把 MEMOS_DIR/AUDIT_LOG 指到 tmp,不碰真实 memos/ 与 audit/。
"""

import json

import pytest

from counterpoint.agents import chair


@pytest.fixture
def tmp_dirs(tmp_path, monkeypatch):
    memos = tmp_path / "memos"
    audit = tmp_path / "audit" / "signoff.jsonl"
    monkeypatch.setattr(chair, "MEMOS_DIR", memos)
    monkeypatch.setattr(chair, "AUDIT_LOG", audit)
    return memos, audit


def _audit_lines(audit_path):
    return [json.loads(line) for line in audit_path.read_text().splitlines()]


def test_save_memo_valid_rating(tmp_dirs):
    memos, audit = tmp_dirs
    out = chair.save_memo(chair.SaveMemoInput(ticker="aapl", rating="overweight", thesis="t", kill_criteria="k", memo_markdown="# m"))
    assert "评级 Overweight" in out  # 大小写已归一化
    files = list(memos.glob("AAPL-*.md"))
    assert len(files) == 1 and files[0].read_text() == "# m"
    rec = _audit_lines(audit)[-1]
    assert rec["event"] == "memo_created" and rec["rating"] == "Overweight"


def test_save_memo_invalid_rating_rejected(tmp_dirs):
    memos, _ = tmp_dirs
    out = chair.save_memo(chair.SaveMemoInput(ticker="AAPL", rating="StrongBuy", thesis="t", kill_criteria="k", memo_markdown="# m"))
    assert "评级无效" in out
    assert list(memos.glob("*.md")) == []  # 非法评级不落盘


def test_record_signoff_appends_block_and_audits(tmp_dirs):
    memos, audit = tmp_dirs
    chair.save_memo(chair.SaveMemoInput(ticker="AAPL", rating="Hold", thesis="t", kill_criteria="k", memo_markdown="# m"))
    out = chair.record_signoff(
        chair.RecordSignoffInput(ticker="AAPL", decision="approve", signer="Chrowder Chen", comments="关注 E7")
    )
    assert "已记录" in out
    memo = list(memos.glob("AAPL-*.md"))[0].read_text()
    assert "## 签字记录(人工签字门)" in memo
    assert "APPROVE" in memo and "Chrowder Chen" in memo and "关注 E7" in memo
    rec = _audit_lines(audit)[-1]
    assert rec["event"] == "signed" and rec["decision"] == "APPROVE" and rec["comments"] == "关注 E7"


def test_record_signoff_invalid_decision(tmp_dirs):
    memos, _ = tmp_dirs
    chair.save_memo(chair.SaveMemoInput(ticker="AAPL", rating="Hold", thesis="t", kill_criteria="k", memo_markdown="# m"))
    out = chair.record_signoff(chair.RecordSignoffInput(ticker="AAPL", decision="maybe", signer="X"))
    assert "决定无效" in out


def test_record_signoff_missing_memo(tmp_dirs):
    out = chair.record_signoff(chair.RecordSignoffInput(ticker="ZZZ", decision="APPROVE", signer="X"))
    assert "找不到备忘录" in out
