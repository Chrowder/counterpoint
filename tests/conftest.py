"""测试默认语言钉在 zh。

本分支运行时默认英文(i18n.DEFAULT="en"),但多数单测断言的是中文产出
(evidence 字段、chair 返回文案、memory recall 等),且 chair 在 import 时就
解析 T=pick(_L),所以必须在任何测试模块导入前把 OUTPUT_LANG 设成 zh。
要测英文路径的用例用 monkeypatch.setenv("OUTPUT_LANG","en") 自行覆盖。
"""

import os

# 强制 zh(即使外部 shell 设了 OUTPUT_LANG=en,本套单测也按中文断言)。
# 单个用例要测英文路径时用 monkeypatch 覆盖。
os.environ["OUTPUT_LANG"] = "zh"
