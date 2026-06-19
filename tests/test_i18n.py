"""i18n 语言开关基线测试。"""

import pytest

from counterpoint import i18n


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("OUTPUT_LANG", raising=False)


def test_default_is_en():
    # 本分支默认英文(env 未设时)
    assert i18n.output_lang() == "en"


def test_env_switches_lang(monkeypatch):
    monkeypatch.setenv("OUTPUT_LANG", "zh")
    assert i18n.output_lang() == "zh"


def test_case_and_whitespace_tolerant(monkeypatch):
    monkeypatch.setenv("OUTPUT_LANG", "  ZH ")
    assert i18n.output_lang() == "zh"


def test_illegal_value_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("OUTPUT_LANG", "fr")
    assert i18n.output_lang() == "en"


def test_pick_selects_by_current_lang(monkeypatch):
    bundle = {"zh": "中", "en": "EN"}
    assert i18n.pick(bundle) == "EN"  # 默认 en
    monkeypatch.setenv("OUTPUT_LANG", "zh")
    assert i18n.pick(bundle) == "中"


def test_pick_falls_back_when_lang_missing():
    # 目标语言缺失 → 回落 DEFAULT,再回落任意可用值
    assert i18n.pick({"zh": "中"}, lang="en") == "中"
    assert i18n.pick({"zh": "中", "en": "EN"}, lang="fr") == "EN"
