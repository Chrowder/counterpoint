# Counterpoint — CLAUDE.md
> 每个会话先读本文件,这些是持久约束,不要违背。

## 是什么
对抗式多空投研系统:多个 agent 通过 Band.ai(chat room + @mention)协作,对一只股票产出一份**研究备忘录**。
这是研究/决策支持工具,**不是交易系统**:不下单、不给买卖指令,最终人类签字。仅供教育研究。

## 硬性约束(不可违背)
1. 协调层必须是 Band(@mention 路由),不是进程内函数调用,不能做成薄包装。
2. Bull 与 Bear 跑在**不同模型家族**(cross-model 对抗)。
3. 并行盲评:同一条消息同时 @Bull @Bear,各自独立出结论后再交换反驳,避免锚定。
4. 所有论断接地到 Evidence Pack(结构化+引用);禁止编造新闻/日期/价格;脱离证据的论点无效。
5. 必须有人工签字门 + 审计留痕。
6. 不实现下单/执行。密钥只进 .env / agent_config.yaml,绝不写进代码。

## 范围纪律(单人项目)
- 只写当前里程碑需要的代码;不提前抽象、不搭通用框架、不留用不到的接口;依赖最小化。
- 落后时按序砍:① Sector expert ② 第二房间合并 ③ Risk agent ④ 真实数据退回 stub。
  保底:Data + Bull + Bear + Chair 跨模型辩论 + 备忘录 + 人工签字,全程走 Band。

## 架构与命名
- repo: counterpoint;主房间 "Counterpoint Desk"
- agents: Data Steward / Bull / Bear / Risk Officer / Chair(PM)
- 流程: 人类 @Chair → @Data Steward 出 Evidence Pack → 并行 @Bull @Bear 盲评 → 交换+反驳 → @Risk 压测 → Chair 综合备忘录 → 人类签字

## 技术栈与配置约定
- Python 3.11+,Band SDK(pip 包 band-sdk;1.0.0 起 import 名是 band,官方教程里的 thenvoi 是旧名)。每个 agent = 连 Band 的 remote agent:监听 @自己 → 调 LLM → 回房间。
- band-sdk 1.0.0 的 Agent.create 不读 THENVOI_* 环境变量,平台 URL 要显式传参(counterpoint/config.py 的 platform_urls() 统一处理)。
- 5 个 agent 建在**同一 Band 账号**下(兄弟 agent,无需联系人即可互 @/互拉)。本地/单机跑。
- 配置两文件:`.env`(THENVOI_REST_URL/THENVOI_WS_URL + LLM key + 角色模型路由 BULL_MODEL/BEAR_MODEL…);`agent_config.yaml`(每 agent 的 agent_id+api_key,用 load_agent_config("bull") 取)。两文件都进 .gitignore,只提交 .example。换模型走 env,不改代码。

## 里程碑与 Done 标准
- M0 管道:echo agent 进房间,我能 @它它能回 → 通。✅
- M1 闭环:Data(stub 假证据)+ Bull + Chair 顺序跑通,产出 markdown 备忘录,全程走 Band。✅
- M2 对抗:Bear 跨模型(featherless)+ 并行盲评 + 交换反驳 + 双边备忘录。✅
- M3 签字门:Chair 贴备忘录后请求签字,人类回 APPROVE/REJECT/REVISE,Chair recordsignoff 留痕。✅
  审计留痕在 `audit/signoff.jsonl`(append-only)+ 备忘录尾部签字区块;权威记录是房间历史 + git 提交。
- M5 真实数据:Data Steward 经 Finnhub 拉真实证据(counterpoint/evidence.py,纯函数无 LLM),
  DATA_SOURCE=finnhub|stub 切换;拉取失败报错中止、绝不退回假数据;pack 快照存 data/evidence/<T>-<日期>.md。✅
- M4 Risk Officer:非方向性红队,反应式单发——Chair 收齐反驳后转发证据+完整辩论唤醒它,
  出压测报告(证据盲区排序/改判条件/可靠性定级),Chair 综合进备忘录「风险压测」节。走 haiku。✅
  至此 5-agent 架构与 6 条硬性约束全部落地。
- M6 证据深化:evidence.py 加时间序列——/stock/earnings(近4季 EPS 实际vs预期)+
  /stock/financials-reported(SEC 10-Q,**去累计成单季**营收/利润率趋势)。填上"单点快照无法判趋势"的盲区。
  Finnhub 免费档:earnings/financials-reported 可用;financials(规整版)/price-target/eps-estimate/news-sentiment 是 403 付费。
  注意:10-Q 利润表是年初至今累计,必须去累计(单季=本期−上一季,Q1即单季)才能当季度趋势用,否则失真。✅
- M7 跨运行记忆(recall 半场):counterpoint/memory.py 读 audit/signoff.jsonl 渲染本台往期决策;
  Chair 写备忘录前调 recallmemory,备忘录加「往期对比」节;savememo 加 summary 入记忆。
  **只喂 Chair 不喂 Bull/Bear**——防锚定,保住盲评独立(约束 3)。✅
- M8 复盘(reflection 半场):savememo 的 summary 拆成 thesis+kill_criteria,加 reflection 字段;
  Chair 写备忘录前用本轮 [E*] 当前数据逐条判定上次 kill_criteria 兑现否(触发/未触发/数据不足),
  备忘录「往期对比与复盘」节。recall 对旧 summary 记录回落兼容。改判条件本身非证据,但"是否兑现"须由当前 [E*] 支撑。✅
- supervise.py 看门狗:resync 死循环(同一 id 连续 catch-up≥30)自动重启 agent;run_desk.sh 已套上。

## 工作方式
- 大改动前先给:计划 + 目录 + 依赖,等我确认。增量推进,每里程碑独立跑通再继续。
- 同步更新 README(如何运行 + 各 agent 职责)。Band 胶水代码加注释。卡在 Band 配额/认证时停下来问我。

## Band 关键事实(别重新推导)
- @mention:被 @的才处理;人类看房间全部消息;多 @ = 并行。
- 动态参与者:list/add/remove participant,运行时可招募。
- 兄弟 agent 同账号互通;免费档 local/单机(distributed 要付费 memory)。
- LLM 普通文本输出对房间不可见,必须调 thenvoi_send_message 才算发言;开源模型(DeepSeek 等)遵从度不稳,要把这条放提示词最顶部强调。
- AnthropicAdapter 默认 max_tokens=4096,长输出(如备忘录工具调用)会被截断且适配器对 stop_reason=max_tokens **静默丢弃**,表现为 agent"想了但没做"——已在 make_adapter 里调到 16384。
- 每条消息必须至少 @一个人(API 强制);消息处理失败超过重试上限会标记 failed,之后 /next 重新同步可能造成重复处理。
- Band 免费档有平台级速率限制:app.band.ai 的 /messages/next 会返回 429(Cloudflare)。诱因是 agent 数 × 每 agent 订阅房间数 × 轮询;清理历史房间到只剩 1 个能显著缓解。一天内跑多轮也会累积触限。
- 偶发故障:WebSocket 漏一条消息后走 /next resync 补,若此时撞 429 会陷入"Catching up missed message …"死循环(LangGraph/Bear 上见过,Anthropic 适配器未见),自身把 429 打得更凶。解法:重启该 agent,从全新连接经 /context 重新同步待处理消息即可恢复。