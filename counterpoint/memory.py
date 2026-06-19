"""跨运行记忆(recall 半场):从 audit/signoff.jsonl 读本台历次决策,供 Chair 综合时参考。

只读现有审计日志,不建新库。往期 desk 观点是**连续性参照,不是证据**——
调用方(Chair)须明确:不得当 [E*] 论据、不得盖过当前证据(硬约束 4)。
reflection(等真实结果出来复盘对错)是另一半,留作后续里程碑。
"""

import json
from pathlib import Path

from counterpoint.i18n import output_lang, pick

ROOT = Path(__file__).resolve().parents[1]
AUDIT_LOG = ROOT / "audit" / "signoff.jsonl"
MAX_RUNS = 5

# recall 渲染脚手架按语言切;往期记录的正文(thesis 等)保持入库时的原语言,不翻译。
_L = {
    "zh": {
        "header": "## 往期研究备忘(本台历史,非证据,仅供连续性参考)",
        "signed": "签字 {decision}", "comment": "(意见:{comments})", "unsigned": "未签字",
        "run": "- {date} · 评级 {rating} · {sign}",
        "thesis": "  - 论点:{thesis}",
        "kill": "  - 当时的改判条件(供复盘):{kill}",
    },
    "en": {
        "header": "## Prior Research Notes (this desk's history; not evidence, continuity reference only)",
        "signed": "signed {decision}", "comment": " (comment: {comments})", "unsigned": "unsigned",
        "run": "- {date} · rating {rating} · {sign}",
        "thesis": "  - Thesis: {thesis}",
        "kill": "  - Kill criteria at the time (for reflection): {kill}",
    },
}


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
                # 旧记录无 lang 字段 → 视为 zh(历史产出都是中文),供 recall 按语言隔离
                "lang": e.get("lang", "zh"),
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
    """某 ticker 的往期研究备忘 markdown(最近 MAX_RUNS 次,新→旧);无历史返回空串。

    按当前 OUTPUT_LANG 过滤:英文台只回放英文往期记录,中文台只回放中文,
    防止把异语言的旧 summary 喂给 Chair(锚定/混语污染)。
    """
    L = pick(_L)
    lang = output_lang()
    runs = [r for r in _runs_for(ticker, _load(audit_path)) if r["lang"] == lang]
    if not runs:
        return ""
    lines = [L["header"]]
    for r in reversed(runs[-MAX_RUNS:]):
        if r["decision"]:
            sign = L["signed"].format(decision=r["decision"])
            if r["comments"]:
                sign += L["comment"].format(comments=r["comments"])
        else:
            sign = L["unsigned"]
        lines.append(L["run"].format(date=r["date"], rating=r["rating"] or "—", sign=sign))
        thesis = r["thesis"] or r["summary"]  # 旧记录回落到合并的 summary
        if thesis:
            lines.append(L["thesis"].format(thesis=thesis))
        if r["kill_criteria"]:
            lines.append(L["kill"].format(kill=r["kill_criteria"]))
    return "\n".join(lines) + "\n"
