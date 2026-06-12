# Counterpoint

对抗式多空投研系统:多个 agent 通过 [Band](https://band.ai)(chat room + @mention)协作,对一只股票产出一份**研究备忘录**。

> 这是研究/决策支持工具,**不是交易系统**:不下单、不给买卖指令,最终人类签字。仅供教育研究。

## Agent 职责

| Agent | 职责 | 状态 |
|---|---|---|
| Echo Probe | M0 管道探针:@它它原样回,验证 Band 链路 | ✅ M0 |
| Data Steward | 确定性分发 stub Evidence Pack(无 LLM,零编造),同一条消息 @Bull @Bear = 并行盲评 | ✅ M1 |
| Bull | 多头研究员(Anthropic 家族),盲评立论 + 逐点反驳,论断必须引用证据编号 | ✅ M1 |
| Bear | 空头研究员(**非 Anthropic 家族**,经 featherless/OpenAI 兼容端点),与 Bull 跨模型对抗 | ✅ M2 |
| Chair (PM) | 状态机主持:等齐盲评 → 转发全文交换反驳 → 综合双边备忘录(评级+交锋焦点+分歧记录) | ✅ M1 |
| Risk Officer | 对结论做风险压测 | M3 |

流程(M2 实现):

```
人类 @Chair 研究 X → Chair @Data Steward → Data 贴 Evidence Pack @Bull @Bear @Chair
→ Bull/Bear 并行盲评(Band 可见性保证互相看不到)→ 各自 @Chair 交初论
→ Chair 收齐后转发对方全文,同一条消息 @Bull @Bear 要求逐点反驳(并行)
→ 收齐反驳 → Chair 综合写备忘录(savememo 落盘 memos/)→ 贴回房间
```

> 盲评和交换为什么这样做:Band 里 agent 只能看到 @自己的消息——这天然保证了盲评
> (Bull/Bear 互不可见),也意味着交换阶段必须由 Chair 完整转发对方原文。
> 跨模型对抗(硬性约束):Bull 走 Anthropic,Bear 走 .env 配置的其他家族,换模型只改 .env。

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

## 运行

前置:在 Band 上注册 **Data Steward**、**Bull**、**Bear**、**Chair** 四个 External Agent(名字照抄,@mention 按名字路由),凭据填进 `agent_config.yaml` 对应块,全部加进 Counterpoint Desk 房间;`.env` 填 `ANTHROPIC_API_KEY`、`FEATHERLESS_API_KEY` 和 `BEAR_MODEL`。

```bash
uv sync
./scripts/run_desk.sh        # 一键拉起 4 个 agent,Ctrl+C 全部退出
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
├── config.py              # .env 读取 + 角色→provider/模型路由(换模型改 .env 不改代码)
├── runner.py              # 公共启动逻辑(凭据→Agent.create→监听)
└── agents/
    ├── echo.py            # M0 管道探针
    ├── data_steward.py    # 确定性 stub 证据分发(SimpleAdapter,无 LLM)
    ├── bull.py            # 多头研究员(Anthropic)
    ├── bear.py            # 空头研究员(featherless 开源模型,跨家族)
    └── chair.py           # 主席:状态机主持 + 双边备忘录 + savememo 落盘
data/evidence/             # stub Evidence Pack(显著标注假数据)
memos/                     # 备忘录输出(审计留痕,提交进库)
scripts/run_desk.sh        # 一键拉起 4 个 agent
reference/TradingAgents/   # 只读参考(辩论提示词结构),gitignored
```
