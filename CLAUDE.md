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
- M0 管道:echo agent 进房间,我能 @它它能回 → 通。
- M1 闭环:Data(stub 假证据)+ Bull + Chair 顺序跑通,产出 markdown 备忘录,全程走 Band。
- M1 后停下来给我看,再加 Bear/Risk/签字门/真实数据。**绝不一次写完所有 agent。**

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