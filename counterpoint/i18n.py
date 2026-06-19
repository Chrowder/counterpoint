"""语言开关:OUTPUT_LANG=zh|en 决定 LLM 产出(备忘录/辩论/证据包)与界面后端
串的语言。默认 zh,不配置时行为与历史完全一致。换语言走 .env,不改代码
(CLAUDE.md 约定:语言和模型路由一样,是配置轴而非分支)。

用法:
    from counterpoint.i18n import output_lang, pick
    PROMPT = {"zh": "你是…", "en": "You are…"}
    adapter = make_adapter("bull", pick(PROMPT))
"""

import os

SUPPORTED = ("zh", "en")
DEFAULT = "zh"


def output_lang() -> str:
    """当前产出语言,读 OUTPUT_LANG;非法值回落 DEFAULT。"""
    lang = os.getenv("OUTPUT_LANG", DEFAULT).strip().lower()
    return lang if lang in SUPPORTED else DEFAULT


def pick(bundle: dict, lang: str | None = None):
    """从 {"zh": …, "en": …} 按当前语言取;缺该语言时回落到 zh。

    bundle 必须含 "zh" 键(中文是基线,缺失即编码错误,直接 KeyError)。
    """
    lang = lang or output_lang()
    return bundle.get(lang, bundle[DEFAULT])
