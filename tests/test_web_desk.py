"""web.desk 编排测试:用假 RestClient,不连 Band。

锁住关键契约:建房返回值取 .data.id(曾误写成 .id 会崩)、拉全 5 个 agent、发起消息内容。
"""

from counterpoint.web import desk


class _FakeChats:
    def __init__(self, rec): self.rec = rec
    def create_agent_chat(self, chat):
        self.rec.append(("create",))
        # 真实返回 CreateAgentChatResponse:room 在 .data.id,不是 .id
        data = type("D", (), {"id": "room-xyz"})()
        return type("R", (), {"data": data})()


class _FakeParts:
    def __init__(self, rec): self.rec = rec
    def add_agent_chat_participant(self, room_id, participant):
        self.rec.append(("add", room_id, participant.participant_id))
    def remove_agent_chat_participant(self, room_id, pid):
        self.rec.append(("remove", room_id, pid))


class _FakeMsgs:
    def __init__(self, rec): self.rec = rec
    def create_agent_chat_message(self, room_id, message):
        self.rec.append(("msg", room_id, message.content))


class _FakeClient:
    def __init__(self, rec):
        self.agent_api_chats = _FakeChats(rec)
        self.agent_api_participants = _FakeParts(rec)
        self.agent_api_messages = _FakeMsgs(rec)


def _patch(monkeypatch):
    rec = []
    monkeypatch.setattr(desk, "_client", lambda: _FakeClient(rec))
    monkeypatch.setattr(desk, "_agent_id", lambda role: f"id-{role}")
    return rec


def test_start_research_builds_room_and_kicks_off(monkeypatch):
    rec = _patch(monkeypatch)
    room_id = desk.start_research("aapl")
    assert room_id == "room-xyz"  # 取自 .data.id
    # 5 个 agent 全部加入(含建房者)
    added = {c[2] for c in rec if c[0] == "add"}
    assert added == {f"id-{r}" for r in desk.ROLES}
    # 发起消息:@Chair 研究 AAPL
    msgs = [c for c in rec if c[0] == "msg"]
    assert len(msgs) == 1 and msgs[0][2] == "@Chair 研究 AAPL"


def test_teardown_removes_all_including_initiator(monkeypatch):
    rec = _patch(monkeypatch)
    desk.teardown("room-xyz")
    removed = [c[2] for c in rec if c[0] == "remove"]
    assert set(removed) == {f"id-{r}" for r in desk.ROLES}      # 全部移除
    assert removed[-1] == f"id-{desk.INITIATOR}"                 # 建房者最后移除
