# Counterpoint

对抗式多空投研系统:多个 agent 通过 [Band](https://band.ai)(chat room + @mention)协作,对一只股票产出一份**研究备忘录**。

> 这是研究/决策支持工具,**不是交易系统**:不下单、不给买卖指令,最终人类签字。仅供教育研究。

## Agent 职责

| Agent | 职责 | 状态 |
|---|---|---|
| Echo Probe | M0 管道探针:@它它原样回,验证 Band 链路 | ✅ M0 |
| Data Steward | 确定性产出 Evidence Pack(无 LLM,零编造):Finnhub 真实数据 / stub 回退,同一条消息 @Bull @Bear = 并行盲评 | ✅ M1·M5 |
| Bull | 多头研究员(Anthropic 家族),盲评立论 + 逐点反驳,论断必须引用证据编号 | ✅ M1 |
| Bear | 空头研究员(**非 Anthropic 家族**,经 featherless/OpenAI 兼容端点),与 Bull 跨模型对抗 | ✅ M2 |
| Risk Officer | 非方向性红队:压测辩论质量与证据盲区,给改判条件 + 可靠性定级(Anthropic haiku) | ✅ M4 |
| Chair (PM) | 状态机主持:等齐盲评 → 交换反驳 → 唤醒压测 → 综合双边备忘录 → 守人工签字门 | ✅ M1 |

流程(M4 实现):

```
人类 @Chair 研究 X → Chair @Data Steward → Data 贴 Evidence Pack @Bull @Bear @Chair
→ Bull/Bear 并行盲评(Band 可见性保证互相看不到)→ 各自 @Chair 交初论
→ Chair 收齐后转发对方全文,同一条消息 @Bull @Bear 要求逐点反驳(并行)
→ 收齐反驳 → Chair 转发【证据+完整辩论】@Risk Officer 压测 → Risk @Chair 出压测报告
→ Chair 综合写备忘录(savememo 落盘 memos/)→ 贴回房间 + 请求签字
→ 人类回复 APPROVE / REJECT / REVISE → Chair recordsignoff 留痕(备忘录追加签字区块 + audit/signoff.jsonl)
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

前置:在 Band 上注册 **Data Steward**、**Bull**、**Bear**、**Risk Officer**、**Chair** 五个 External Agent(名字照抄,@mention 按名字路由),凭据填进 `agent_config.yaml` 对应块,全部加进 Counterpoint Desk 房间;`.env` 填 `ANTHROPIC_API_KEY`、`FEATHERLESS_API_KEY`、`BEAR_MODEL`、`RISK_MODEL`,以及真实数据用的 `FINNHUB_API_KEY`([finnhub.io](https://finnhub.io) 免费注册)。

> **数据源**:`DATA_SOURCE=finnhub`(默认)拉真实数据;拉取失败/ticker 无效时 Data Steward
> 报错中止、**不退回假数据**。离线或额度耗尽时可临时设 `DATA_SOURCE=stub` 用 `data/evidence/*.stub.md`。
> 真实 pack 每次拉取会快照到 `data/evidence/<TICKER>-<日期>.md` 留痕。
>
> Evidence Pack 含:概况 / 基本面(TTM)/ **盈利与财报逐季趋势**(近 4 季 EPS 实际vs预期、
> 营收与单季利润率,后者从 SEC 10-Q 去累计而来)/ 估值 / 卖方评级 / 标题点名公司的新闻。
> 付费端点(目标价、盈利预期、新闻情绪)免费档不可用,未接入。

```bash
uv sync
./scripts/run_desk.sh        # 一键拉起 4 个 agent,Ctrl+C 全部退出
```

然后在房间里发:

```
@Chair 研究 AAPL
```

自动走完整条链,最终 Chair 在房间贴出备忘录(落盘 `memos/AAPL-<日期>.md`)并请求签字。
你在房间回复决定即过签字门:

```
@Chair APPROVE 同意结论,但需持续监控 E7/E8 监管风险
```

决定为 `APPROVE` / `REJECT` / `REVISE` 之一。Chair 会把签字记录追加到备忘录文件,并向
`audit/signoff.jsonl` 追加一行(append-only)。提交这两者到 git 即形成防篡改的审计时间线。

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
├── evidence.py            # Finnhub 真实数据 → 确定性格式化 Evidence Pack(纯函数,无 LLM);含 EPS/财报逐季趋势
└── agents/
    ├── echo.py            # M0 管道探针
    ├── data_steward.py    # 确定性证据分发(SimpleAdapter,无 LLM):finnhub/stub 切换
    ├── bull.py            # 多头研究员(Anthropic)
    ├── bear.py            # 空头研究员(featherless 开源模型,跨家族)
    ├── risk.py            # 风险官:反应式单发,压测辩论质量与证据盲区(haiku)
    └── chair.py           # 主席:状态机主持 + 双边备忘录 + 风险压测节 + savememo + 签字门 recordsignoff
tests/                     # 纯函数单测(去累计/ticker抽取/评级校验/签字),uv run pytest
data/evidence/             # stub Evidence Pack(显著标注假数据)
memos/                     # 备忘录输出(审计留痕,提交进库)
audit/signoff.jsonl        # 签字门留痕(append-only,运行时生成,提交进库)
scripts/run_desk.sh        # 一键拉起 4 个 agent
reference/TradingAgents/   # 只读参考(辩论提示词结构),gitignored
```
