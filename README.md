# Counterpoint

对抗式多空投研系统:多个 agent 通过 [Band](https://band.ai)(chat room + @mention)协作,对一只股票产出一份**研究备忘录**。

> 这是研究/决策支持工具,**不是交易系统**:不下单、不给买卖指令,最终人类签字。仅供教育研究。

## Agent 职责

| Agent | 职责 | 状态 |
|---|---|---|
| Echo Probe | M0 管道探针:@它它原样回,验证 Band 链路 | ✅ M0 |
| Data Steward | 产出 Evidence Pack(结构化证据+引用),所有论断的接地来源 | M1 |
| Bull | 多头研究员,基于 Evidence Pack 立论 | M1 |
| Chair (PM) | 主持流程,综合辩论写研究备忘录 | M1 |
| Bear | 空头研究员,与 Bull **跨模型家族**对抗 | M1 后 |
| Risk Officer | 对结论做风险压测 | M1 后 |

流程(目标态):人类 @Chair → @Data Steward 出 Evidence Pack → 同一条消息并行 @Bull @Bear 盲评 → 交换+反驳 → @Risk 压测 → Chair 综合备忘录 → 人类签字。

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

## 运行 M0

```bash
uv sync
uv run python -m counterpoint.agents.echo
```

看到 `Echo Probe 已连接 Band` 后,到 Counterpoint Desk 房间里发:

```
@Echo Probe hello pipeline
```

它回 `echo: ...` 即 M0 通过。

## 目录结构

```
counterpoint/
├── config.py          # .env 读取 + 角色→模型路由(换模型改 .env 不改代码)
└── agents/
    └── echo.py        # M0 管道探针
reference/TradingAgents/   # 只读参考(辩论提示词结构),gitignored
```
