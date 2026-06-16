"""真实 Evidence Pack 构建:从 Finnhub 拉数据,确定性格式化为编号证据。

全程纯代码、无 LLM:每条证据都从真实 API 字段直接搬运,带真实来源与日期。
这是硬性约束 4("禁止编造新闻/日期/价格")的接地保证——数据路径里没有模型,
就没有编造的入口。字段缺失则跳过该条,绝不填 0 或臆造;有效证据过少则报错中止。
"""

import os
from datetime import date, datetime, timedelta, timezone

import httpx

FINNHUB_BASE = "https://finnhub.io/api/v1"
MIN_ITEMS = 5  # 有效证据少于此数视为拉取失败,中止而非凑数
NEWS_DAYS = 30
NEWS_MAX = 4
EARNINGS_MAX = 4   # 盈利趋势取最近几季
FIN_QUARTERS = 4   # 财报趋势取最近几个季报(10-Q)

# 利润表字段在不同公司的 concept 名略有差异,用 us-gaap 标准名按优先级兜底匹配
_IC_CONCEPTS = {
    "revenue": (
        "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap_Revenues",
        "us-gaap_RevenuesNetOfInterestExpense",
    ),
    "gross": ("us-gaap_GrossProfit",),
    "operating": ("us-gaap_OperatingIncomeLoss",),
    "net": ("us-gaap_NetIncomeLoss", "us-gaap_ProfitLoss"),
}


class EvidenceError(RuntimeError):
    """真实数据不可用(网络/额度/ticker 无效/字段过少),由调用方报错中止。"""


def _get(client: httpx.Client, path: str, **params) -> object:
    params["token"] = os.environ["FINNHUB_API_KEY"]
    try:
        r = client.get(FINNHUB_BASE + path, params=params)
    except httpx.HTTPError as e:
        raise EvidenceError(f"Finnhub 请求失败({path}): {e}") from e
    if r.status_code != 200:
        raise EvidenceError(f"Finnhub 返回 {r.status_code}({path}): {r.text[:120]}")
    return r.json()


def _soft_get(client: httpx.Client, path: str, **params):
    """增强类端点用:取不到(权限/网络)返回 None,不让整个 pack 失败。"""
    try:
        return _get(client, path, **params)
    except EvidenceError:
        return None


def _num(v, suffix: str = "", scale: float = 1.0, nd: int = 2):
    """把可能为 None 的数值格式化;None → None(调用方据此跳过)。"""
    if v is None:
        return None
    try:
        return f"{float(v) * scale:,.{nd}f}{suffix}"
    except (TypeError, ValueError):
        return None


def _join(*parts: str | None) -> str | None:
    kept = [p for p in parts if p]
    return ",".join(kept) if kept else None


def _ic_value(ic_items: list, key: str):
    """从利润表条目里按 concept 优先级取数值,取不到返回 None。"""
    by_concept = {it.get("concept"): it.get("value") for it in ic_items}
    for concept in _IC_CONCEPTS[key]:
        v = by_concept.get(concept)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _earnings_item(earnings: list) -> list[str]:
    """近 N 季 实际 vs 预期 EPS + 超预期方向,合成一条趋势证据。"""
    rows = sorted(
        [e for e in earnings if e.get("actual") is not None],
        key=lambda e: (e.get("year", 0), e.get("quarter", 0)),
    )[-EARNINGS_MAX:]
    if not rows:
        return []
    segs = []
    for e in rows:
        seg = f"{e.get('year')}Q{e.get('quarter')} 实际EPS {e.get('actual')}"
        if e.get("estimate") is not None:
            seg += f"/预期 {e.get('estimate')}"
        sp = e.get("surprisePercent")
        if sp is not None:
            seg += f"({'超' if sp >= 0 else '逊'}{abs(sp):.1f}%)"
        segs.append(seg)
    return [f"(来源: Finnhub /stock/earnings)近 {len(rows)} 季 EPS 实际 vs 预期:" + ";".join(segs) + "。"]


_IC_FLOW = ("revenue", "gross", "operating", "net")


def _financials_item(reported: dict) -> list[str]:
    """近 N 个季度的营收与单季利润率趋势,来自真实 SEC 申报(10-Q)。

    关键:10-Q 利润表是**年初至今累计**,需去累计成单季(单季 = 本期累计 − 上一季累计,
    Q1 即单季);缺上一季无法可靠去累计就跳过,绝不让累计值冒充单季(约束 4 不容失真)。
    10-K 的 Q4 是全年数,排除。
    """
    data = reported.get("data", []) if isinstance(reported, dict) else []
    ytd: dict[tuple, dict] = {}
    for rep in data:
        if rep.get("form") != "10-Q":
            continue
        ic = (rep.get("report") or {}).get("ic", [])
        rev = _ic_value(ic, "revenue")
        if not rev:
            continue
        ytd[(rep.get("year"), rep.get("quarter"))] = {k: _ic_value(ic, k) for k in _IC_FLOW}

    discrete = []
    for (yr, q) in sorted(ytd):
        cur = ytd[(yr, q)]
        if q == 1:
            d = dict(cur)
        else:
            prev = ytd.get((yr, q - 1))
            if not prev:  # 缺上一季,去累计不可靠,跳过
                continue
            d = {
                k: (cur[k] - prev[k]) if cur.get(k) is not None and prev.get(k) is not None else None
                for k in _IC_FLOW
            }
        d["label"] = f"{yr}Q{q}"
        discrete.append(d)

    segs = []
    for d in discrete[-FIN_QUARTERS:]:
        rev = d.get("revenue")
        if not rev or rev <= 0:
            continue
        seg = f"{d['label']} 营收 ${rev / 1e9:.2f}B"
        if d.get("gross") is not None:
            seg += f"、毛利率 {d['gross'] / rev * 100:.1f}%"
        if d.get("operating") is not None:
            seg += f"、营业利润率 {d['operating'] / rev * 100:.1f}%"
        if d.get("net") is not None:
            seg += f"、净利率 {d['net'] / rev * 100:.1f}%"
        segs.append(seg)
    if len(segs) < 2:  # 不足两季不成趋势
        return []
    return ["(来源: Finnhub /stock/financials-reported, SEC 10-Q,已去累计为单季)逐季趋势:" + ";".join(segs) + "。"]


def build_pack(ticker: str) -> tuple[str, str]:
    """拉取并构建真实 Evidence Pack。返回 (规范化 ticker, markdown)。失败抛 EvidenceError。"""
    if not os.environ.get("FINNHUB_API_KEY"):
        raise EvidenceError("未配置 FINNHUB_API_KEY")

    ticker = ticker.upper()
    today = date.today().isoformat()
    fetched_at = datetime.now().isoformat(timespec="seconds")

    with httpx.Client(timeout=20) as c:
        profile = _get(c, "/stock/profile2", symbol=ticker)
        if not profile or not profile.get("name"):
            raise EvidenceError(f"{ticker}:无公司数据,ticker 可能无效")
        quote = _get(c, "/quote", symbol=ticker) or {}
        metric = (_get(c, "/stock/metric", symbol=ticker, metric="all") or {}).get("metric", {})
        rec = _get(c, "/stock/recommendation", symbol=ticker) or []
        frm = (date.today() - timedelta(days=NEWS_DAYS)).isoformat()
        news = _get(c, "/company-news", symbol=ticker, **{"from": frm, "to": today}) or []
        # 时间序列(增强项,取不到则跳过,不影响主 pack)
        earnings = _soft_get(c, "/stock/earnings", symbol=ticker) or []
        reported = _soft_get(c, "/stock/financials-reported", symbol=ticker, freq="quarterly") or {}

    name = profile.get("name", ticker)
    src_meta = f"Finnhub /stock/metric, 拉取 {today}"
    src_quote = f"Finnhub /quote, 拉取 {today}"

    # (板块, 正文带来源) —— 仅在底层字段非空时加入。"盈利与财报趋势"承载时间序列证据。
    sections: dict[str, list[str]] = {
        "公司概况": [], "基本面": [], "盈利与财报趋势": [],
        "估值与市场": [], "卖方观点": [], "风险与新闻": [],
    }

    # 公司概况
    cap_b = _num(profile.get("marketCapitalization"), "B", scale=1 / 1000, nd=1)
    shares = _num(profile.get("shareOutstanding"), "M", nd=2)
    overview = _join(
        f"{name}",
        f"行业 {profile.get('finnhubIndustry')}" if profile.get("finnhubIndustry") else None,
        f"市值约 ${cap_b}" if cap_b else None,
        f"流通股 {shares}" if shares else None,
    )
    if overview:
        sections["公司概况"].append(f"(来源: Finnhub /stock/profile2, 拉取 {today}){overview}。")

    # 基本面(TTM)
    growth = _join(
        f"营收 TTM 同比 {_num(metric.get('revenueGrowthTTMYoy'), '%')}" if metric.get("revenueGrowthTTMYoy") is not None else None,
        f"最近季度营收同比 {_num(metric.get('revenueGrowthQuarterlyYoy'), '%')}" if metric.get("revenueGrowthQuarterlyYoy") is not None else None,
        f"EPS TTM 同比 {_num(metric.get('epsGrowthTTMYoy'), '%')}" if metric.get("epsGrowthTTMYoy") is not None else None,
    )
    if growth:
        sections["基本面"].append(f"(来源: {src_meta})增长:{growth}。")
    margins = _join(
        f"毛利率 {_num(metric.get('grossMarginTTM'), '%')}" if metric.get("grossMarginTTM") is not None else None,
        f"营业利润率 {_num(metric.get('operatingMarginTTM'), '%')}" if metric.get("operatingMarginTTM") is not None else None,
        f"净利率 {_num(metric.get('netProfitMarginTTM'), '%')}" if metric.get("netProfitMarginTTM") is not None else None,
        f"ROE {_num(metric.get('roeTTM'), '%')}" if metric.get("roeTTM") is not None else None,
    )
    if margins:
        sections["基本面"].append(f"(来源: {src_meta})盈利能力(TTM):{margins}。")

    # 盈利与财报趋势(时间序列,填补单点快照无法判断趋势的盲区)
    sections["盈利与财报趋势"].extend(_earnings_item(earnings))
    sections["盈利与财报趋势"].extend(_financials_item(reported))

    # 估值与市场
    price = _num(quote.get("c"), nd=2)
    chg = _num(quote.get("dp"), "%")
    if price:
        sections["估值与市场"].append(
            f"(来源: {src_quote})现价 ${price}" + (f",较前收盘 {chg}。" if chg else "。")
        )
    val = _join(
        f"P/E(TTM) {_num(metric.get('peTTM'))}" if metric.get("peTTM") is not None else None,
        f"52 周区间 ${_num(metric.get('52WeekLow'))}–${_num(metric.get('52WeekHigh'))}"
        if metric.get("52WeekLow") is not None and metric.get("52WeekHigh") is not None else None,
        f"股息率 {_num(metric.get('currentDividendYieldTTM'), '%')}" if metric.get("currentDividendYieldTTM") is not None else None,
    )
    if val:
        sections["估值与市场"].append(f"(来源: {src_meta})估值:{val}。")

    # 卖方观点(最新一期)
    if rec:
        r0 = rec[0]
        sections["卖方观点"].append(
            f"(来源: Finnhub /stock/recommendation, 期 {r0.get('period')})卖方评级分布:"
            f"强买 {r0.get('strongBuy')} / 买入 {r0.get('buy')} / 持有 {r0.get('hold')} / "
            f"卖出 {r0.get('sell')} / 强卖 {r0.get('strongSell')}。"
        )

    # 风险与新闻:只保留**标题**点名公司的(正文捎带提及精度太低),按时间倒序取前 N,
    # 真实标题+日期+链接。基本面已有足够底数,新闻宁缺毋滥。
    kw = {ticker.lower(), name.split()[0].lower()}
    rel = [
        n for n in sorted(news, key=lambda x: x.get("datetime", 0), reverse=True)
        if any(w in str(n.get("headline", "")).lower() for w in kw)
    ][:NEWS_MAX]
    for n in rel:
        ndate = datetime.fromtimestamp(n["datetime"], tz=timezone.utc).date().isoformat() if n.get("datetime") else today
        summary = (n.get("summary") or "").strip().replace("\n", " ")
        if len(summary) > 160:
            summary = summary[:157] + "…"
        sections["风险与新闻"].append(
            f"(来源: {n.get('source', 'Finnhub')}, {ndate}){n.get('headline', '').strip()}。"
            + (f"{summary} " if summary else "")
            + f"[链接]({n.get('url', '')})"
        )

    total = sum(len(v) for v in sections.values())
    if total < MIN_ITEMS:
        raise EvidenceError(f"{ticker}:有效证据仅 {total} 条(<{MIN_ITEMS}),数据不足,中止")

    # 渲染:跨板块顺序分配 [E1][E2]… 编号
    lines = [
        f"# Evidence Pack: {ticker}({name})",
        "",
        f"> 数据来源:Finnhub(finnhub.io),拉取时间 {fetched_at}。以下为**真实市场数据**,"
        "每条带编号与来源;禁止使用编号外的事实,下游所有论断必须引用编号。",
        "",
    ]
    n = 0
    for title, items in sections.items():
        if not items:
            continue
        lines.append(f"## {title}")
        lines.append("")
        for body in items:
            n += 1
            lines.append(f"- **[E{n}]**{body}")
        lines.append("")

    return ticker, "\n".join(lines).rstrip() + "\n"
