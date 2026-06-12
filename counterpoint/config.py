"""读 .env 的集中入口。

注意:band-sdk 1.0.0 的 Agent.create 不读 THENVOI_* 环境变量,
平台 URL 必须显式传参,所以这里统一读出来供各 agent 使用。
角色 → 模型路由也在这里:换模型改 .env,不改代码(CLAUDE.md 约定)。
"""

import os

from dotenv import load_dotenv

load_dotenv()

# .env 里没配置时的兜底
_DEFAULT_MODELS = {
    "echo": "claude-haiku-4-5-20251001",
}


def model_for(role: str) -> str:
    """取角色对应的模型名,如 model_for("bull") 读 BULL_MODEL。"""
    model = os.getenv(f"{role.upper()}_MODEL") or _DEFAULT_MODELS.get(role)
    if not model:
        raise RuntimeError(f"请在 .env 里配置 {role.upper()}_MODEL")
    return model


def platform_urls() -> tuple[str, str]:
    """(ws_url, rest_url),默认指向 Band 生产环境;rest 去掉尾斜杠以免拼接出 //。"""
    ws = os.getenv("THENVOI_WS_URL", "wss://app.band.ai/api/v1/socket/websocket")
    rest = os.getenv("THENVOI_REST_URL", "https://app.band.ai").rstrip("/")
    return ws, rest
