"""evidence.py 纯函数测试(不打网络)。重点是 10-Q 去累计——M6 踩过的坑。"""

from counterpoint import evidence as ev


def _ic(**concepts):
    return [{"concept": c, "value": v} for c, v in concepts.items()]


def _q(year, quarter, form="10-Q", **concepts):
    return {"form": form, "year": year, "quarter": quarter, "report": {"ic": _ic(**concepts)}}


def test_ic_value_picks_concept_with_fallback():
    items = _ic(**{"us-gaap_Revenues": 100})
    assert ev._ic_value(items, "revenue") == 100.0
    # 首选 concept 缺失时回落到次选
    items2 = _ic(**{"us-gaap_ProfitLoss": 7})
    assert ev._ic_value(items2, "net") == 7.0
    # 完全缺失返回 None
    assert ev._ic_value([], "gross") is None


def test_financials_decumulates_ytd_to_quarterly():
    """10-Q 利润表是年初至今累计:Q1=单季,Q2=Q2_YTD−Q1_YTD。"""
    reported = {"data": [
        _q(2025, 1, **{"us-gaap_Revenues": 10e9, "us-gaap_GrossProfit": 2e9}),
        _q(2025, 2, **{"us-gaap_Revenues": 25e9, "us-gaap_GrossProfit": 5.5e9}),  # YTD
        _q(2024, 4, form="10-K", **{"us-gaap_Revenues": 99e9}),  # 年报应被排除
    ]}
    out = ev._financials_item(reported)
    assert len(out) == 1
    text = out[0]
    assert "2025Q1 营收 $10.00B" in text       # Q1 即单季
    assert "2025Q2 营收 $15.00B" in text       # 25−10=15,去累计正确
    assert "99" not in text                     # 10-K 全年数被排除
    # 毛利率:Q1 2/10=20.0%,Q2 单季 (5.5−2)/(15)=23.3%
    assert "毛利率 20.0%" in text
    assert "毛利率 23.3%" in text


def test_financials_skips_quarter_missing_prev():
    """缺上一季无法可靠去累计,不足两季 → 返回空,不冒充。"""
    reported = {"data": [_q(2025, 2, **{"us-gaap_Revenues": 25e9})]}  # 只有 Q2,无 Q1
    assert ev._financials_item(reported) == []


def test_earnings_item_formats_beat_miss():
    earnings = [
        {"year": 2025, "quarter": 3, "actual": 0.5, "estimate": 0.56, "surprisePercent": -10.5},
        {"year": 2026, "quarter": 1, "actual": 0.41, "estimate": 0.38, "surprisePercent": 8.7},
    ]
    out = ev._earnings_item(earnings)
    assert len(out) == 1
    assert "2025Q3 实际EPS 0.5/预期 0.56(逊10.5%)" in out[0]
    assert "2026Q1 实际EPS 0.41/预期 0.38(超8.7%)" in out[0]


def test_earnings_empty():
    assert ev._earnings_item([]) == []


def test_num_and_join():
    assert ev._num(None) is None
    assert ev._num(12.345, "%") == "12.35%"
    assert ev._num(1234.5, scale=1 / 1000, nd=1) == "1.2"
    assert ev._join("a", None, "b") == "a,b"
    assert ev._join(None, None) is None
