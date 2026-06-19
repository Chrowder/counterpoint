"""i18n 语言开关基线测试。"""

import pytest

from counterpoint import i18n


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("OUTPUT_LANG", raising=False)


def test_default_is_zh():
    assert i18n.output_lang() == "zh"


def test_env_switches_lang(monkeypatch):
    monkeypatch.setenv("OUTPUT_LANG", "en")
    assert i18n.output_lang() == "en"


def test_case_and_whitespace_tolerant(monkeypatch):
    monkeypatch.setenv("OUTPUT_LANG", "  EN ")
    assert i18n.output_lang() == "en"


def test_illegal_value_falls_back_to_zh(monkeypatch):
    monkeypatch.setenv("OUTPUT_LANG", "fr")
    assert i18n.output_lang() == "zh"


def test_pick_selects_by_current_lang(monkeypatch):
    bundle = {"zh": "中", "en": "EN"}
    assert i18n.pick(bundle) == "中"
    monkeypatch.setenv("OUTPUT_LANG", "en")
    assert i18n.pick(bundle) == "EN"


def test_pick_falls_back_to_zh_when_lang_missing():
    bundle = {"zh": "中"}
    assert i18n.pick(bundle, lang="en") == "中"
