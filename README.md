# Counterpoint

对抗式多空投研系统:多个 agent 通过 [Band](https://band.ai)(chat room + @mention)协作,对一只股票产出一份**研究备忘录**。

> 这是研究/决策支持工具,**不是交易系统**:不下单、不给买卖指令,最终人类签字。仅供教育研究。

## Agent 职责

| Agent | 职责 | 状态 |
|---|---|---|
| Echo Probe | M0 管道探针:@它它原样回,验证 Band 链路 | ✅ M0 |
| Data Steward | 确定性分发 stub Evidence Pack(无 LLM,零编造),同一条消息 @所有分析师 = 并行盲评入口 | ✅ M1 |
| Bull | 多头研究员,仅基于 Evidence Pack 立论,每条论断引用证据编号 | ✅ M1 |
| Chair (PM) | 主持流程,综合分析写研究备忘录(五档评级),savememo 工具落盘 memos/ | ✅ M1 |
| Bear | 空头研究员,与 Bull **跨模型家族**对抗 | M2 |
| Risk Officer | 对结论做风险压测 | M2 后 |

流程(M1 实现):人类 @Chair 研究 X → Chair @Data Steward 要证据 → Data 贴 Evidence Pack 并 @Bull(分析)+@Chair(通知)→ Bull 分析 @Chair → Chair 写备忘录落盘 memos/ 并贴回房间。

> 为什么是 Data 直接 @分析师而不是 Chair 转发:Band 里 agent 只能看到 @自己的消息,
> 让证据消息直接 @所有分析师,既保证大家拿到同一份原文,也正是目标态"同一条消息
> 并行 @Bull @Bear 盲评"的机制——M2 加 Bear 只需在 mentions 列表加一项。

## 环境准备

1. **Band 账号**:在 [app.band.ai](https://app.band.ai) 免费注册(无需信用卡)。
2. **注册 agent**:Agents → New Agent → 选 **External Agent**。M0 只需要建一个,命名 `Echo Probe`(别叫 Assistant/Bot 这类词,会干扰路由)。创建弹窗里的 **API Key 只显示一次**,立刻复制;Agent UUID 在该 agent 设置页右下角。
3. **建房间**:Chats → 新建房间 **Counterpoint Desk**,从参与者面板把 Echo Probe 加进去。
4. **本地配置**:

```bash
cp .env.example .env                              # 填 ANTHROPIC_API_KEY
cp agent_config.yaml.example agent_config.yaml    # 填 echo 的 agent_id + api_key
```

`.env` 和 `agent_config.yaml` 含真实密钥,已在 .gitignore 里,绝不提交。

## 运行 M1

前置:在 Band 上注册 **Data Steward**、**Bull**、**Chair** 三个 External Agent(名字照抄,@mention 按名字路由),凭据填进 `agent_config.yaml` 对应块,三个都加进 Counterpoint Desk 房间。

```bash
uv sync
./scripts/run_m1.sh        # 一键拉起 3 个 agent,Ctrl+C 全部退出
```

然后在房间里发:

```
@Chair 研究 AAPL
```

自动走完整条链,最终 Chair 在房间贴出备忘录,同时落盘 `memos/AAPL-<日期>.md`。

### 运行 M0(管道探针)

```bash
uv run python -m counterpoint.agents.echo
```

房间里 `@Echo Probe hello pipeline`,回 `echo: ...` 即通。

## 目录结构

```
counterpoint/
├── config.py              # .env 读取 + 角色→模型路由(换模型改 .env 不改代码)
└── agents/
    ├── echo.py            # M0 管道探针
    ├── data_steward.py    # 确定性 stub 证据分发(SimpleAdapter,无 LLM)
    ├── bull.py            # 多头研究员(AnthropicAdapter)
    └── chair.py           # 主席:备忘录综合 + savememo 落盘工具
data/evidence/             # stub Evidence Pack(显著标注假数据)
memos/                     # 备忘录输出(审计留痕,提交进库)
scripts/run_m1.sh          # 一键拉起 M1 三个 agent
reference/TradingAgents/   # 只读参考(辩论提示词结构),gitignored
```
