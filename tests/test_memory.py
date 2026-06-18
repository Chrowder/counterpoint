"""memory.recall 测试:从 audit 流水渲染往期备忘(不碰真实 audit)。"""

import json

from counterpoint import memory


def _write(tmp_path, entries):
    p = tmp_path / "signoff.jsonl"
    p.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n", encoding="utf-8")
    return p


def test_recall_empty_when_no_history(tmp_path):
    p = _write(tmp_path, [{"event": "memo_created", "ticker": "AAPL", "ts": "2026-06-01T00:00:00",
                           "memo_file": "AAPL-2026-06-01.md", "rating": "Buy", "summary": "x"}])
    assert memory.recall("TSLA", audit_path=p) == ""  # 不同 ticker
    assert memory.recall("MSFT", audit_path=tmp_path / "none.jsonl") == ""  # 无文件


def test_recall_pairs_memo_and_signoff(tmp_path):
    p = _write(tmp_path, [
        {"event": "memo_created", "ticker": "MSFT", "ts": "2026-06-17T22:00:00",
         "memo_file": "MSFT-2026-06-17.md", "rating": "Hold", "summary": "云增长 vs 利润率压缩"},
        {"event": "signed", "ticker": "MSFT", "ts": "2026-06-17T22:05:00",
         "memo_file": "MSFT-2026-06-17.md", "decision": "APPROVE", "signer": "Chrowder", "comments": "盯 Azure"},
    ])
    out = memory.recall("msft", audit_path=p)  # 大小写不敏感
    assert "2026-06-17" in out and "评级 Hold" in out
    assert "签字 APPROVE" in out and "意见:盯 Azure" in out
    assert "云增长 vs 利润率压缩" in out
    assert "非证据" in out  # 接地纪律提示在标题里


def test_recall_unsigned_run(tmp_path):
    p = _write(tmp_path, [{"event": "memo_created", "ticker": "NVDA", "ts": "2026-06-10T00:00:00",
                           "memo_file": "NVDA-2026-06-10.md", "rating": "Overweight", "summary": "AI 需求"}])
    out = memory.recall("NVDA", audit_path=p)
    assert "未签字" in out and "评级 Overweight" in out


def test_recall_orders_new_to_old_and_caps(tmp_path):
    entries = []
    for i in range(7):  # 7 次运行,应只保留最近 MAX_RUNS=5,且新在前
        entries.append({"event": "memo_created", "ticker": "AMD", "ts": f"2026-06-0{i+1}T00:00:00",
                        "memo_file": f"AMD-d{i}.md", "rating": "Hold", "summary": f"run{i}"})
    out = memory.recall("AMD", audit_path=_write(tmp_path, entries))
    assert "run6" in out and "run2" in out      # 最近 5 条(run2..run6)
    assert "run0" not in out and "run1" not in out  # 最旧两条被截掉
    assert out.index("run6") < out.index("run2")    # 新→旧
