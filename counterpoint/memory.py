"""跨运行记忆(recall 半场):从 audit/signoff.jsonl 读本台历次决策,供 Chair 综合时参考。

只读现有审计日志,不建新库。往期 desk 观点是**连续性参照,不是证据**——
调用方(Chair)须明确:不得当 [E*] 论据、不得盖过当前证据(硬约束 4)。
reflection(等真实结果出来复盘对错)是另一半,留作后续里程碑。
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_LOG = ROOT / "audit" / "signoff.jsonl"
MAX_RUNS = 5


def _load(audit_path: Path | None = None) -> list[dict]:
    path = audit_path or AUDIT_LOG
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _runs_for(ticker: str, entries: list[dict]) -> list[dict]:
    """把审计流水按 ticker 聚成历次运行(memo_created 起一条,signed 补签字)。"""
    ticker = ticker.upper()
    runs: list[dict] = []
    by_file: dict[str, dict] = {}
    for e in entries:
        if str(e.get("ticker", "")).upper() != ticker:
            continue
        if e.get("event") == "memo_created":
            run = {
                "date": str(e.get("ts", ""))[:10],
                "rating": e.get("rating"),
                # M8 起拆成 thesis + kill_criteria;旧记录只有合并的 summary,回落兼容
                "thesis": e.get("thesis", ""),
                "kill_criteria": e.get("kill_criteria", ""),
                "summary": e.get("summary", ""),
                "decision": None,
                "comments": "",
            }
            runs.append(run)
            by_file[e.get("memo_file")] = run
        elif e.get("event") == "signed":
            run = by_file.get(e.get("memo_file")) or (runs[-1] if runs else None)
            if run is not None:
                run["decision"] = e.get("decision")
                run["comments"] = e.get("comments", "")
    return runs


def recall(ticker: str, audit_path: Path | None = None) -> str:
    """某 ticker 的往期研究备忘 markdown(最近 MAX_RUNS 次,新→旧);无历史返回空串。"""
    runs = _runs_for(ticker, _load(audit_path))
    if not runs:
        return ""
    lines = ["## 往期研究备忘(本台历史,非证据,仅供连续性参考)"]
    for r in reversed(runs[-MAX_RUNS:]):
        if r["decision"]:
            sign = f"签字 {r['decision']}" + (f"(意见:{r['comments']})" if r["comments"] else "")
        else:
            sign = "未签字"
        lines.append(f"- {r['date']} · 评级 {r['rating'] or '—'} · {sign}")
        thesis = r["thesis"] or r["summary"]  # 旧记录回落到合并的 summary
        if thesis:
            lines.append(f"  - 论点:{thesis}")
        if r["kill_criteria"]:
            lines.append(f"  - 当时的改判条件(供复盘):{r['kill_criteria']}")
    return "\n".join(lines) + "\n"
