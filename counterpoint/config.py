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


def make_adapter(role: str, prompt: str, additional_tools: list | None = None):
    """按 {ROLE}_PROVIDER 选适配器:anthropic 走原生,其余走 OpenAI 兼容端点。

    跨模型对抗(Bull vs Bear 不同模型家族)就在这里实现:换家族只改 .env,
    OpenAI 兼容端点(featherless / aimlapi …)读 {PROVIDER}_BASE_URL/{PROVIDER}_API_KEY。
    """
    from band import AdapterFeatures, Emit

    provider = os.getenv(f"{role.upper()}_PROVIDER", "anthropic").lower()
    features = AdapterFeatures(emit={Emit.EXECUTION})

    if provider == "anthropic":
        from band.adapters import AnthropicAdapter

        return AnthropicAdapter(
            model=model_for(role),
            prompt=prompt,
            additional_tools=additional_tools,
            features=features,
            # 默认 4096 会把长备忘录的 savememo 工具调用截断,适配器对
            # stop_reason=max_tokens 是静默丢弃,表现为 agent"想了但没做"
            max_tokens=16384,
        )

    base_url = os.getenv(f"{provider.upper()}_BASE_URL")
    api_key = os.getenv(f"{provider.upper()}_API_KEY")
    if not (base_url and api_key):
        raise RuntimeError(
            f"{role} 配置为 provider={provider},请在 .env 里配置 "
            f"{provider.upper()}_BASE_URL 和 {provider.upper()}_API_KEY"
        )

    # band-sdk 的 Python 适配器没有 OpenAI 兼容直连项,官方主路径是 LangGraph + ChatOpenAI
    from band.adapters import LangGraphAdapter
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver

    return LangGraphAdapter(
        llm=ChatOpenAI(model=model_for(role), base_url=base_url, api_key=api_key),
        checkpointer=InMemorySaver(),
        custom_section=prompt,
        additional_tools=additional_tools,
        features=features,
    )
