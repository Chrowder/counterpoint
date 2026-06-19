"""Band 房间编排:程序化建房 → 拉 5 个 agent → 发起研究 → 用完清场。

签字不在这里代发:网页签字由 app 直接调 Chair 的 record_signoff 落库(带真实人类署名),
不经 agent 代发,避免把签字人记成 agent(否则破坏人工签字门的留痕,见硬约束 5)。


后端用某个 agent 的凭据当"发起方/房主"(Agent API 没有独立的人类 key),
所以触发消息技术上由该 agent 代发。建房用 RestClient(同步)即可,无需常驻 WebSocket。

注意:Agent/Human REST 都**没有删房端点**(本 SDK)。"用完即删"以"移除全部 agent 参与者"
近似实现——房间变空壳、不再产生轮询负载(免 Band 平台 429)。真删需 Enterprise/human API。

agent 进程仍须常驻(run_desk.sh / supervise),本模块只负责建房+发起+收尾。
"""

import re

from thenvoi_rest import (
    ChatMessageRequest,
    ChatMessageRequestMentionsItem,
    ChatRoomRequest,
    ParticipantRequest,
    RestClient,
)

from band.config import load_agent_config
from counterpoint.config import platform_urls

# 房主/发起方 + 要拉进房间的其余 agent(都在同一 Band 账号下,互为兄弟)
INITIATOR = "data_steward"
ROLES = ["data_steward", "bull", "bear", "risk", "chair"]
# 读房间用 Chair 的 key:Band 按 @mention 限定可见性,而几乎所有消息都 @Chair
# (Data 分发/双方初论/反驳/Risk 报告),故 Chair 视角≈全景;用别的 agent key 只能看到零星几条。
READER = "chair"


def _client_for(role: str) -> RestClient:
    _, rest_url = platform_urls()
    _, api_key = load_agent_config(role)
    return RestClient(api_key=api_key, base_url=rest_url)


def _client() -> RestClient:
    return _client_for(INITIATOR)


def _agent_id(role: str) -> str:
    aid, _ = load_agent_config(role)
    return aid


def start_research(ticker: str) -> str:
    """建房 → 拉 5 个 agent → 发 '@Chair 研究 <ticker>'。返回 room_id。"""
    ticker = ticker.upper()
    c = _client()
    # 返回 CreateAgentChatResponse,房间在 .data 里(不是顶层 .id)
    room_id = c.agent_api_chats.create_agent_chat(chat=ChatRoomRequest()).data.id

    # 显式拉入其余 agent;真实失败要冒出来(否则房间残缺还往下走)
    for role in ROLES:
        if role == INITIATOR:
            continue
        c.agent_api_participants.add_agent_chat_participant(
            room_id, participant=ParticipantRequest(participant_id=_agent_id(role))
        )
    # 不假设"建房者自动入房":显式补加,已在房则容忍重复
    try:
        c.agent_api_participants.add_agent_chat_participant(
            room_id, participant=ParticipantRequest(participant_id=_agent_id(INITIATOR))
        )
    except Exception:
        pass

    chair_id = _agent_id("chair")
    c.agent_api_messages.create_agent_chat_message(
        room_id,
        message=ChatMessageRequest(
            content=f"@Chair 研究 {ticker}",
            mentions=[ChatMessageRequestMentionsItem(id=chair_id, handle="Chair")],
        ),
    )
    return room_id


_MENTION_RE = re.compile(r"@\[\[[0-9a-f-]+\]\]\s*")


def clean_content(text: str) -> str:
    """去掉 Band 的内部 mention 编码 @[[uuid]](展示用,路由用不到)。"""
    return _MENTION_RE.sub("", text or "").strip()


def room_messages(room_id: str) -> list[dict]:
    """读房间消息(按时间正序),供前端进度推导与原生直播用。

    用 Chair 的 key:几乎所有消息都 @Chair,可见整场辩论(Data/Bull/Bear/Risk);
    Chair 自己发的编排消息不在其中(看不到自己),进度/直播以分析方发言为准,足够。
    """
    c = _client_for(READER)
    resp = c.agent_api_messages.list_agent_messages(room_id, status="all", page_size=200)
    msgs = []
    for m in resp.data or []:
        msgs.append({
            "sender": m.sender_name or m.sender_type or "?",
            "sender_type": m.sender_type,
            "type": m.message_type,
            "content": clean_content(m.content),
            "at": m.inserted_at.isoformat() if m.inserted_at else "",
        })
    msgs.sort(key=lambda x: x["at"])
    return msgs


def teardown(room_id: str) -> None:
    """用完清场:移除**全部** agent 参与者(含建房者),房间变空壳、彻底消除轮询负载。

    建房者留在房里会让它无限累积死房间订阅 → 重新触发 Band 平台 429,故一并移除;
    放最后移除(移除自身后可能失去房间访问权)。
    """
    c = _client()
    others = [r for r in ROLES if r != INITIATOR]
    for role in others + [INITIATOR]:
        try:
            c.agent_api_participants.remove_agent_chat_participant(room_id, _agent_id(role))
        except Exception:
            pass  # 尽力而为,个别移除失败不阻断
