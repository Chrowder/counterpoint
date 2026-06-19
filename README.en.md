# Counterpoint

> 🌐 [中文](README.md) · **English** (current)

An adversarial bull/bear research system: multiple agents collaborate through [Band](https://band.ai) (chat room + @mention) to produce a single **research memo** on a stock.

> This is a research / decision-support tool, **not a trading system**: it places no orders and gives no buy/sell instructions; a human signs off at the end. For education and research only.

## Project status

All planned milestones are complete; the 5-agent architecture and 6 hard constraints are fully in place, validated end-to-end on real AAPL / AMD / TSLA data.

**Milestones**

| Milestone | Delivered |
|---|---|
| M0 Pipeline | echo agent validates the Band @mention round-trip |
| M1 Loop | Data (stub) + Bull + Chair run in sequence, producing the first markdown memo |
| M2 Adversarial | Bear on a cross-model family (featherless/DeepSeek) + parallel blind review + rebuttal exchange + two-sided memo |
| M3 Sign-off gate | human APPROVE/REJECT/REVISE + memo sign-off block + `audit/signoff.jsonl` trail |
| M5 Real data | Finnhub real evidence (overview/fundamentals/valuation/sell-side/news); aborts on failure, never fabricates |
| M4 Risk stress-test | Risk Officer red team: ranked evidence blind spots + kill criteria + reliability rating |
| M6 Evidence depth | adds quarterly EPS and revenue/margin trends (SEC 10-Q de-cumulated), filling the single-snapshot blind spot |
| M7 Cross-run memory | when re-researching the same ticker, Chair recalls this desk's prior rating/sign-off/thesis, adding a "Prior Comparison" section (fed only to Chair, to prevent anchoring) |
| M8 Reflection | Chair checks last run's kill criteria against this round's real data one by one, adding "Prior Comparison & Reflection" — linking two analyses into a verifiable chain |
| Hardening | structured validation of the five-tier rating; self-healing watchdog for Bear's resync loop; pure-function unit tests in `tests/` (`uv run pytest`) |

**How the 6 hard constraints land**

1. The coordination layer is Band (@mention routing throughout, no in-process calls) · 2. Bull/Bear adversarial across model families ·
3. Parallel blind review (one message @Bull @Bear, isolated naturally by Band visibility) · 4. Claims grounded in the Evidence Pack, zero fabrication on real data ·
5. Human sign-off gate + audit trail · 6. No order execution; secrets live only in `.env`/`agent_config.yaml`.

## Agent roles

| Agent | Role | Status |
|---|---|---|
| Echo Probe | M0 pipeline probe: @it and it echoes back, validating the Band link | ✅ M0 |
| Data Steward | Deterministically produces the Evidence Pack (no LLM, zero fabrication): Finnhub real data / stub fallback; one message @Bull @Bear = parallel blind review | ✅ M1·M5 |
| Bull | Bull researcher (Anthropic family): blind-review thesis + point-by-point rebuttal; every claim must cite an evidence id | ✅ M1 |
| Bear | Bear researcher (**non-Anthropic family**, via featherless/OpenAI-compatible endpoint), adversarial across models vs. Bull | ✅ M2 |
| Risk Officer | Non-directional red team: stress-tests debate quality and evidence blind spots, gives kill criteria + reliability rating (Anthropic haiku) | ✅ M4 |
| Chair (PM) | Runs the state machine: collect blind reviews → exchange rebuttals → wake the stress-test → synthesize the two-sided memo → guard the human sign-off gate | ✅ M1 |

Flow (as of M4):

```
Human @Chair research X → Chair @Data Steward → Data posts the Evidence Pack @Bull @Bear @Chair
→ Bull/Bear blind-review in parallel (Band visibility guarantees they can't see each other) → each @Chair with an opening case
→ Chair, once both are in, forwards the other's full text and, in one message @Bull @Bear, asks for a point-by-point rebuttal (in parallel)
→ both rebuttals in → Chair forwards [evidence + full debate] @Risk Officer to stress-test → Risk @Chair with the report
→ Chair synthesizes the memo (savememo to memos/) → posts it back + requests sign-off
→ Human replies APPROVE / REJECT / REVISE → Chair recordsignoff for the trail (memo sign-off block + audit/signoff.jsonl)
```

> Why blind review and exchange work this way: in Band an agent only sees messages that @it — this naturally guarantees blind review
> (Bull/Bear can't see each other), and it means the exchange phase must have Chair forward the other side's full original text.
> Cross-model adversarial (hard constraint): Bull runs on Anthropic, Bear on another family configured in `.env`; switching models only edits `.env`.

## Language (bilingual zh/en)

Output language is a **config axis**, not a branch: one codebase, switched via `.env`, **defaulting to English on this branch**.

```bash
OUTPUT_LANG=zh ./scripts/run_desk.sh    # start a Chinese desk: memo / debate / evidence pack all in Chinese
```

`OUTPUT_LANG=en|zh` (default en) controls the language of the memo, the bull/bear debate, the Evidence Pack, and the tool descriptions; switching only edits `.env`, never code.
Only one language at a time (the 5 agents share one Band account). Cross-run memory is isolated by language — an English desk replays only English prior records, never feeding old Chinese conclusions to Chair (avoiding anchoring / mixed-language pollution).

**The web UI language is independent of `OUTPUT_LANG`**: the `EN/中` button at the top right toggles instantly (or `?lang=en`),
so you can run "English desk + Chinese UI" or vice versa. See `counterpoint/i18n.py` (output layer) and `web/ui/src/i18n.js` (UI layer).

## Setup

1. **Band account**: register free at [app.band.ai](https://app.band.ai) (no credit card).
2. **Register an agent**: Agents → New Agent → choose **External Agent**. M0 needs just one, named `Echo Probe` (don't use words like Assistant/Bot — they interfere with routing). The **API Key is shown only once** in the creation dialog — copy it immediately; the Agent UUID is at the bottom-right of that agent's settings page.
3. **Create the room**: Chats → new room **Counterpoint Desk**, add Echo Probe from the participants panel.
4. **Local config**:

```bash
cp .env.example .env                              # fill in ANTHROPIC_API_KEY
cp agent_config.yaml.example agent_config.yaml    # fill in echo's agent_id + api_key
```

`.env` and `agent_config.yaml` hold real secrets, are in .gitignore, and are never committed.

## Running

Prerequisite: register five External Agents on Band — **Data Steward**, **Bull**, **Bear**, **Risk Officer**, **Chair** (copy the names exactly; @mention routes by name) — put their credentials in the matching blocks of `agent_config.yaml`, add them all to the Counterpoint Desk room; fill `.env` with `ANTHROPIC_API_KEY`, `FEATHERLESS_API_KEY`, `BEAR_MODEL`, `RISK_MODEL`, plus `FINNHUB_API_KEY` for real data (free at [finnhub.io](https://finnhub.io)).

> **Data source**: `DATA_SOURCE=finnhub` (default) pulls real data; on fetch failure / invalid ticker the Data Steward
> aborts with an error and **does not fall back to fake data**. Offline or out of quota, you can temporarily set `DATA_SOURCE=stub` to use `data/evidence/*.stub.md`.
> Each real pack is snapshotted to `data/evidence/<TICKER>-<date>.md` for the trail.
>
> The Evidence Pack contains: overview / fundamentals (TTM) / **quarterly earnings & financials trends** (last 4 quarters of EPS actual-vs-estimate,
> revenue and single-quarter margins, the latter de-cumulated from SEC 10-Q) / valuation / sell-side ratings / news whose headline names the company.
> Paid endpoints (price target, EPS estimates, news sentiment) are unavailable on the free tier and not integrated.

```bash
uv sync
./scripts/run_desk.sh        # bring up all 5 agents at once; Ctrl+C exits them all
```

Then post in the room:

```
@Chair research AAPL
```

It runs the whole chain automatically; finally Chair posts the memo in the room (saved to `memos/AAPL-<date>.md`) and requests sign-off.
Reply with your decision in the room to pass the gate:

```
@Chair APPROVE agree with the conclusion, but keep monitoring the E7/E8 regulatory risk
```

The decision must be one of `APPROVE` / `REJECT` / `REVISE`. Chair appends the sign-off record to the memo file and adds one line to
`audit/signoff.jsonl` (append-only). Committing both to git forms a tamper-evident audit timeline.

### Running M0 (pipeline probe)

```bash
uv run python -m counterpoint.agents.echo
```

In the room, `@Echo Probe hello pipeline` should come back as `echo: ...`.

## Directory layout

```
counterpoint/
├── config.py              # .env reading + role→provider/model routing (switch models in .env, not code)
├── i18n.py                # output-language switch (OUTPUT_LANG=zh|en): prompts/memo/evidence/tools
├── runner.py              # shared startup logic (credentials→Agent.create→listen)
├── evidence.py            # Finnhub real data → deterministically formatted Evidence Pack (pure functions, no LLM); incl. quarterly EPS/financials trends
├── memory.py              # cross-run recall: reads audit, renders this desk's prior decisions (fed only to Chair)
├── supervise.py           # agent watchdog: auto-restart on resync loop
└── agents/
    ├── echo.py            # M0 pipeline probe
    ├── data_steward.py    # deterministic evidence dispatch (SimpleAdapter, no LLM): finnhub/stub switch
    ├── bull.py            # bull researcher (Anthropic)
    ├── bear.py            # bear researcher (featherless open model, cross-family)
    ├── risk.py            # risk officer: reactive single-shot, stress-tests debate quality & blind spots (haiku)
    └── chair.py           # chair: runs the state machine + two-sided memo + risk section + savememo + recordsignoff sign-off gate
tests/                     # pure-function unit tests (de-cumulation/ticker extraction/rating validation/sign-off), uv run pytest
data/evidence/             # stub Evidence Packs (clearly marked as fake data)
memos/                     # memo output (audit trail, committed)
audit/signoff.jsonl        # sign-off gate trail (append-only, generated at runtime, committed)
scripts/run_desk.sh        # bring up the agents at once
reference/TradingAgents/   # read-only reference (debate prompt structure), gitignored
```
