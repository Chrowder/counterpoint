# Counterpoint Web 前端(web-frontend 分支)

> 🌐 **中文**(当前) · [English](README.en.md)

网页输入股票代码 → 后台自动在 Band 建房间、拉 5 个 agent、发起研究 → 轮询展示研究备忘录 → 网页签字 → 用完清场。

> **界面语言**:右上角 `EN/中` 即时切换(或 `?lang=en`),独立于后端 `OUTPUT_LANG`(备忘录产出语言)。实现见 `ui/src/i18n.js`。

## 架构

```
浏览器(static/index.html)
  └─ POST /api/research {ticker}  → desk.start_research:建房 + 拉 5 agent + 发"@Chair 研究 X"
  └─ GET  /api/result/{ticker}    → result.latest_result:读 memos/ + audit 渲染(每 8s 轮询)
  └─ POST /api/signoff {signer}   → 直接调 record_signoff 落库(带真实人类署名,不经 agent 代发)
  └─ POST /api/cleanup/{ticker}   → desk.teardown:签字落库后移除全部 agent(用完即"删")
```

前端是 **Vite + React**,在 `counterpoint/web/ui/`。先构建一次出静态产物,FastAPI 托管 `ui/dist`(未构建则回退到 `static/index.html` 旧单页)。

```bash
# 1) 构建前端(需 Node;改了 ui/ 源码后重跑)
cd counterpoint/web/ui && npm install && npm run build && cd -
# 2) 常驻 5 个 agent(带 resync 看门狗)
./scripts/run_desk.sh
# 3) 起后端(托管 UI + 编排)
uv run uvicorn counterpoint.web.app:app --port 8000
# 浏览器打开 http://localhost:8000
```

> 改 UI 时也可 `cd counterpoint/web/ui && npm run dev`(5173,/api 代理到 8000)热更调试。

### Demo 模式(零成本前端调试,不连 Band/agent/LLM)

调前端时不必每次跑真实多 agent 流水线(烧 token + Band 配额)。`WEB_DEMO=1` 让后端
离线回放一份**真实抓取的房间记录**(`fixtures/demo.json`),按时间渐进揭示消息与阶段
(~21 秒走完),进度动画、直播、备忘录、签字全可测:

```bash
cd counterpoint/web/ui && npm run build && cd -   # 改了 UI 才需重建
WEB_DEMO=1 uv run uvicorn counterpoint.web.app:app --port 8000   # 不用起 agent
```

前端完全跑通后,去掉 `WEB_DEMO` 再连真实(`run_desk.sh` + 正常后端)做最终验证。
fixture 由 `desk.room_messages`(Chair key)抓取真实房间所得,可随时重抓更新。

新增展示:**流水线进度时间线**(`/api/progress` 读 Band 房间消息推导阶段)、
**Band 房间原生直播**(`/api/room`,因 Band 设了 `X-Frame-Options: SAMEORIGIN` 无法 iframe,改为读消息自渲染)、备忘录 markdown 渲染、评级 pill、签字门。

## 设计要点 / 取舍

- **发起方**:Agent API 没有独立的"人类" key,后端用 `data_steward` 的凭据当房主发起,触发消息技术上由该 agent 代发(功能上 Chair 照常研究)。
- **签字人是真人,不是 agent**:网页签字由 app **直接调 `record_signoff`** 落库,签字人取自表单的真实姓名(必填)。**不**用 agent 在房间代发——否则 Chair 会把签字人记成 agent,破坏人工签字门留痕(硬约束 5)。
- **用完即删**:本 SDK 的 Agent/Human REST **都没有删房端点**,故 `teardown` 以"移除**全部** agent 参与者(含建房者)"近似——房间变空壳、不再产生轮询负载(规避 Band 平台 429)。真删需 Enterprise/human API。**清场在签字落库(signed=true)后才执行**,避免 Chair 被提前移出导致签字丢失。
- **进度**:一轮研究约数分钟(盲评→反驳→压测→综合),前端轮询 + "进行中"状态;未做中间消息流式直播(可作后续增强)。
- **房间映射持久化**:`_rooms`(ticker→room_id)落盘 `.web_rooms.json`(gitignored),服务重启后仍能清场,避免死房间泄漏。限流下建议一次只跑一轮。
- **硬约束 6**:页面只展示备忘录 + 人工签字,**不提供任何下单/交易动作**。

## 验证状态

- ✅ 结果展示(`result.latest_result`)+ 路由 + 首页:已离线单测 + TestClient 验证(读真实 memos/TSLA)。
- ⚠️ 建房/发起/签字/清场(`desk.py`):按 band-sdk REST API(create_agent_chat / add_agent_chat_participant / create_agent_chat_message / remove_agent_chat_participant)编写,**尚未连真实 Band 活体验证**(需常驻 agent + 凭据 + 配额)。
