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


def test_only_chair_or_human_triggers_dispatch():
    # Chair(agent)放行
    assert ds.is_research_requester("Agent", "Chair") is True
    # 人类(User/其它非 agent 类型)放行
    assert ds.is_research_requester("User", "Chrowder") is True
    assert ds.is_research_requester("Human", "Someone") is True
    # 其它 agent(Bull/Bear/Risk)误 @ → 挡掉
    assert ds.is_research_requester("Agent", "Bear") is False
    assert ds.is_research_requester("Agent", "Bull") is False
    assert ds.is_research_requester("Agent", "Risk Officer") is False
    # 大小写容错;sender_type 缺失时按非 agent(人类)放行,宁松勿误杀真人请求
    assert ds.is_research_requester("agent", "Bear") is False
    assert ds.is_research_requester(None, None) is True
