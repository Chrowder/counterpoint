"""data_steward.py ticker 抽取测试。"""

from counterpoint.agents import data_steward as ds


def test_extract_picks_first_valid_ticker():
    assert ds.extract_ticker("请为 AAPL 准备 Evidence Pack") == "AAPL"
    assert ds.extract_ticker("研究 TSLA 谢谢") == "TSLA"


def test_extract_skips_stopwords():
    # AI / DOJ 等是停用词,应跳过,取真正的 ticker
    assert ds.extract_ticker("用 AI 研究 NVDA 的 DOJ 风险") == "NVDA"


def test_extract_none_when_no_ticker():
    assert ds.extract_ticker("研究苹果公司") is None
