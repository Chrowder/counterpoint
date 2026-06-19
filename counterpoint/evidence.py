"""真实 Evidence Pack 构建:从 Finnhub 拉数据,确定性格式化为编号证据。

全程纯代码、无 LLM:每条证据都从真实 API 字段直接搬运,带真实来源与日期。
这是硬性约束 4("禁止编造新闻/日期/价格")的接地保证——数据路径里没有模型,
就没有编造的入口。字段缺失则跳过该条,绝不填 0 或臆造;有效证据过少则报错中止。

证据包语言走 OUTPUT_LANG(zh|en):只是字段标签/来源措辞按语言切,数值与来源不变。
"""

import os
from datetime import date, datetime, timedelta, timezone

import httpx

from counterpoint.i18n import pick

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

# 渲染标签按语言切。section 用稳定 key,标题另查 _L["sections"];zh 文案须与历史逐字一致
# (test_evidence 断言中文输出)。
_L = {
    "zh": {
        "sections": {
            "overview": "公司概况", "fundamentals": "基本面", "earnings_trend": "盈利与财报趋势",
            "valuation": "估值与市场", "sellside": "卖方观点", "risk_news": "风险与新闻",
        },
        "fetched": "拉取",
        "src": "来源: ",
        "src_profile": "Finnhub /stock/profile2",
        "industry": "行业 {x}", "mktcap": "市值约 ${x}", "shares": "流通股 {x}",
        "overview_end": "。",
        "growth_label": "增长:", "profit_label": "盈利能力(TTM):", "val_label": "估值:",
        "rev_ttm_yoy": "营收 TTM 同比 {x}", "rev_q_yoy": "最近季度营收同比 {x}", "eps_ttm_yoy": "EPS TTM 同比 {x}",
        "gross_m": "毛利率 {x}", "op_m": "营业利润率 {x}", "net_m": "净利率 {x}", "roe": "ROE {x}",
        "price": "现价 ${x}", "price_chg": ",较前收盘 {x}。", "price_end": "。",
        "pe": "P/E(TTM) {x}", "range52": "52 周区间 ${lo}–${hi}", "div_yield": "股息率 {x}",
        "sellside_src": "Finnhub /stock/recommendation, 期 {period}",
        "sellside_body": "卖方评级分布:强买 {sb} / 买入 {b} / 持有 {h} / 卖出 {s} / 强卖 {ss}。",
        "news_link": "链接",
        # 时间序列
        "earn_src": "(来源: Finnhub /stock/earnings)近 {n} 季 EPS 实际 vs 预期:",
        "earn_actual": "{y}Q{q} 实际EPS {actual}", "earn_est": "/预期 {est}",
        "earn_beat": "超", "earn_miss": "逊", "earn_surprise": "({dir}{pct}%)",
        "fin_src": "(来源: Finnhub /stock/financials-reported, SEC 10-Q,已去累计为单季)逐季趋势:",
        "fin_rev": "{label} 营收 ${rev}B", "fin_gm": "、毛利率 {x}%",
        "fin_om": "、营业利润率 {x}%", "fin_nm": "、净利率 {x}%",
        "seg_join": ";", "end": "。",
        "header_title": "# Evidence Pack: {ticker}({name})",
        "header_note": "> 数据来源:Finnhub(finnhub.io),拉取时间 {fetched_at}。以下为**真实市场数据**,"
        "每条带编号与来源;禁止使用编号外的事实,下游所有论断必须引用编号。",
    },
    "en": {
        "sections": {
            "overview": "Company Overview", "fundamentals": "Fundamentals",
            "earnings_trend": "Earnings & Financials Trend", "valuation": "Valuation & Market",
            "sellside": "Sell-side View", "risk_news": "Risks & News",
        },
        "fetched": "fetched",
        "src": "source: ",
        "src_profile": "Finnhub /stock/profile2",
        "industry": "industry {x}", "mktcap": "market cap ~${x}", "shares": "shares outstanding {x}",
        "overview_end": ".",
        "growth_label": "Growth: ", "profit_label": "Profitability (TTM): ", "val_label": "Valuation: ",
        "rev_ttm_yoy": "revenue TTM YoY {x}", "rev_q_yoy": "latest-quarter revenue YoY {x}", "eps_ttm_yoy": "EPS TTM YoY {x}",
        "gross_m": "gross margin {x}", "op_m": "operating margin {x}", "net_m": "net margin {x}", "roe": "ROE {x}",
        "price": "price ${x}", "price_chg": ", change vs prev close {x}.", "price_end": ".",
        "pe": "P/E (TTM) {x}", "range52": "52-week range ${lo}–${hi}", "div_yield": "dividend yield {x}",
        "sellside_src": "Finnhub /stock/recommendation, period {period}",
        "sellside_body": "analyst rating distribution: Strong Buy {sb} / Buy {b} / Hold {h} / Sell {s} / Strong Sell {ss}.",
        "news_link": "link",
        "earn_src": "(source: Finnhub /stock/earnings) Last {n} quarters, EPS actual vs estimate: ",
        "earn_actual": "{y}Q{q} actual EPS {actual}", "earn_est": "/est {est}",
        "earn_beat": "beat", "earn_miss": "missed", "earn_surprise": " ({dir} {pct}%)",
        "fin_src": "(source: Finnhub /stock/financials-reported, SEC 10-Q, de-cumulated to single quarters) Quarterly trend: ",
        "fin_rev": "{label} revenue ${rev}B", "fin_gm": ", gross margin {x}%",
        "fin_om": ", operating margin {x}%", "fin_nm": ", net margin {x}%",
        "seg_join": "; ", "end": ".",
        "header_title": "# Evidence Pack: {ticker} ({name})",
        "header_note": "> Data source: Finnhub (finnhub.io), fetched at {fetched_at}. The following is **real market data**, "
        "each item carrying an id and source; do not use any fact outside the ids, and every downstream claim must cite an id.",
    },
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
    L = pick(_L)
    rows = sorted(
        [e for e in earnings if e.get("actual") is not None],
        key=lambda e: (e.get("year", 0), e.get("quarter", 0)),
    )[-EARNINGS_MAX:]
    if not rows:
        return []
    segs = []
    for e in rows:
        seg = L["earn_actual"].format(y=e.get("year"), q=e.get("quarter"), actual=e.get("actual"))
        if e.get("estimate") is not None:
            seg += L["earn_est"].format(est=e.get("estimate"))
        sp = e.get("surprisePercent")
        if sp is not None:
            d = L["earn_beat"] if sp >= 0 else L["earn_miss"]
            seg += L["earn_surprise"].format(dir=d, pct=f"{abs(sp):.1f}")
        segs.append(seg)
    return [L["earn_src"].format(n=len(rows)) + L["seg_join"].join(segs) + L["end"]]


_IC_FLOW = ("revenue", "gross", "operating", "net")


def _financials_item(reported: dict) -> list[str]:
    """近 N 个季度的营收与单季利润率趋势,来自真实 SEC 申报(10-Q)。

    关键:10-Q 利润表是**年初至今累计**,需去累计成单季(单季 = 本期累计 − 上一季累计,
    Q1 即单季);缺上一季无法可靠去累计就跳过,绝不让累计值冒充单季(约束 4 不容失真)。
    10-K 的 Q4 是全年数,排除。
    """
    L = pick(_L)
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
        seg = L["fin_rev"].format(label=d["label"], rev=f"{rev / 1e9:.2f}")
        if d.get("gross") is not None:
            seg += L["fin_gm"].format(x=f"{d['gross'] / rev * 100:.1f}")
        if d.get("operating") is not None:
            seg += L["fin_om"].format(x=f"{d['operating'] / rev * 100:.1f}")
        if d.get("net") is not None:
            seg += L["fin_nm"].format(x=f"{d['net'] / rev * 100:.1f}")
        segs.append(seg)
    if len(segs) < 2:  # 不足两季不成趋势
        return []
    return [L["fin_src"] + L["seg_join"].join(segs) + L["end"]]


def build_pack(ticker: str) -> tuple[str, str]:
    """拉取并构建真实 Evidence Pack。返回 (规范化 ticker, markdown)。失败抛 EvidenceError。"""
    if not os.environ.get("FINNHUB_API_KEY"):
        raise EvidenceError("未配置 FINNHUB_API_KEY")

    L = pick(_L)
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
    src_meta = f"{L['src']}Finnhub /stock/metric, {L['fetched']} {today}"
    src_quote = f"{L['src']}Finnhub /quote, {L['fetched']} {today}"

    # 稳定 key → 证据条目;标题在渲染时查 _L["sections"]。"earnings_trend" 承载时间序列证据。
    sections: dict[str, list[str]] = {
        "overview": [], "fundamentals": [], "earnings_trend": [],
        "valuation": [], "sellside": [], "risk_news": [],
    }

    # 公司概况
    cap_b = _num(profile.get("marketCapitalization"), "B", scale=1 / 1000, nd=1)
    shares = _num(profile.get("shareOutstanding"), "M", nd=2)
    overview = _join(
        f"{name}",
        L["industry"].format(x=profile.get("finnhubIndustry")) if profile.get("finnhubIndustry") else None,
        L["mktcap"].format(x=cap_b) if cap_b else None,
        L["shares"].format(x=shares) if shares else None,
    )
    if overview:
        sections["overview"].append(
            f"({L['src']}{L['src_profile']}, {L['fetched']} {today}){overview}{L['overview_end']}"
        )

    # 基本面(TTM)
    growth = _join(
        L["rev_ttm_yoy"].format(x=_num(metric.get('revenueGrowthTTMYoy'), '%')) if metric.get("revenueGrowthTTMYoy") is not None else None,
        L["rev_q_yoy"].format(x=_num(metric.get('revenueGrowthQuarterlyYoy'), '%')) if metric.get("revenueGrowthQuarterlyYoy") is not None else None,
        L["eps_ttm_yoy"].format(x=_num(metric.get('epsGrowthTTMYoy'), '%')) if metric.get("epsGrowthTTMYoy") is not None else None,
    )
    if growth:
        sections["fundamentals"].append(f"({src_meta}){L['growth_label']}{growth}{L['end']}")
    margins = _join(
        L["gross_m"].format(x=_num(metric.get('grossMarginTTM'), '%')) if metric.get("grossMarginTTM") is not None else None,
        L["op_m"].format(x=_num(metric.get('operatingMarginTTM'), '%')) if metric.get("operatingMarginTTM") is not None else None,
        L["net_m"].format(x=_num(metric.get('netProfitMarginTTM'), '%')) if metric.get("netProfitMarginTTM") is not None else None,
        L["roe"].format(x=_num(metric.get('roeTTM'), '%')) if metric.get("roeTTM") is not None else None,
    )
    if margins:
        sections["fundamentals"].append(f"({src_meta}){L['profit_label']}{margins}{L['end']}")

    # 盈利与财报趋势(时间序列,填补单点快照无法判断趋势的盲区)
    sections["earnings_trend"].extend(_earnings_item(earnings))
    sections["earnings_trend"].extend(_financials_item(reported))

    # 估值与市场
    price = _num(quote.get("c"), nd=2)
    chg = _num(quote.get("dp"), "%")
    if price:
        sections["valuation"].append(
            f"({src_quote}){L['price'].format(x=price)}"
            + (L["price_chg"].format(x=chg) if chg else L["price_end"])
        )
    val = _join(
        L["pe"].format(x=_num(metric.get('peTTM'))) if metric.get("peTTM") is not None else None,
        L["range52"].format(lo=_num(metric.get('52WeekLow')), hi=_num(metric.get('52WeekHigh')))
        if metric.get("52WeekLow") is not None and metric.get("52WeekHigh") is not None else None,
        L["div_yield"].format(x=_num(metric.get('currentDividendYieldTTM'), '%')) if metric.get("currentDividendYieldTTM") is not None else None,
    )
    if val:
        sections["valuation"].append(f"({src_meta}){L['val_label']}{val}{L['end']}")

    # 卖方观点(最新一期)
    if rec:
        r0 = rec[0]
        sections["sellside"].append(
            f"({L['src']}{L['sellside_src'].format(period=r0.get('period'))})"
            + L["sellside_body"].format(
                sb=r0.get('strongBuy'), b=r0.get('buy'), h=r0.get('hold'),
                s=r0.get('sell'), ss=r0.get('strongSell'),
            )
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
        sections["risk_news"].append(
            f"({L['src']}{n.get('source', 'Finnhub')}, {ndate}){n.get('headline', '').strip()}{L['end']}"
            + (f"{summary} " if summary else "")
            + f"[{L['news_link']}]({n.get('url', '')})"
        )

    total = sum(len(v) for v in sections.values())
    if total < MIN_ITEMS:
        raise EvidenceError(f"{ticker}:有效证据仅 {total} 条(<{MIN_ITEMS}),数据不足,中止")

    # 渲染:跨板块顺序分配 [E1][E2]… 编号
    lines = [
        L["header_title"].format(ticker=ticker, name=name),
        "",
        L["header_note"].format(fetched_at=fetched_at),
        "",
    ]
    n = 0
    titles = L["sections"]
    for key, items in sections.items():
        if not items:
            continue
        lines.append(f"## {titles[key]}")
        lines.append("")
        for body in items:
            n += 1
            lines.append(f"- **[E{n}]**{body}")
        lines.append("")

    return ticker, "\n".join(lines).rstrip() + "\n"
