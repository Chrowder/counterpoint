# Counterpoint Web Frontend (web-frontend branch)

> 🌐 [中文](README.md) · **English** (current)

Type a ticker in the browser → the backend automatically creates a Band room, brings in the 5 agents, and starts the research → poll and display the research memo → sign off in the browser → tear down when done.

> **UI language**: the `EN/中` button at the top right toggles instantly (or `?lang=en`), independent of the backend `OUTPUT_LANG` (the memo output language). See `ui/src/i18n.js`.

## Architecture

```
Browser (static/index.html)
  └─ POST /api/research {ticker}  → desk.start_research: create room + bring in 5 agents + post "@Chair research X"
  └─ GET  /api/result/{ticker}    → result.latest_result: read memos/ + audit and render (poll every 8s)
  └─ POST /api/signoff {signer}   → call record_signoff directly (with a real human name, not via an agent)
  └─ POST /api/cleanup/{ticker}   → desk.teardown: after sign-off lands, remove all agents (a "delete" by emptying)
```

The frontend is **Vite + React**, in `counterpoint/web/ui/`. Build the static output once; FastAPI serves `ui/dist` (falling back to the old single page `static/index.html` if not built).

```bash
# 1) Build the frontend (needs Node; rebuild after editing ui/ source)
cd counterpoint/web/ui && npm install && npm run build && cd -
# 2) Keep the 5 agents running (with the resync watchdog)
./scripts/run_desk.sh
# 3) Start the backend (serves the UI + orchestrates)
uv run uvicorn counterpoint.web.app:app --port 8000
# Open http://localhost:8000
```

> When editing the UI you can also `cd counterpoint/web/ui && npm run dev` (port 5173, /api proxied to 8000) for hot-reload.

### Demo mode (zero-cost frontend debugging, no Band/agent/LLM)

You don't need to run the real multi-agent pipeline every time you tweak the frontend (it burns tokens + Band quota). `WEB_DEMO=1` makes the backend
replay a **real captured room transcript** (`fixtures/demo.json`), revealing messages and stages progressively over time
(~21 seconds), so progress animation, live stream, memo, and sign-off are all testable:

```bash
cd counterpoint/web/ui && npm run build && cd -   # only needed if you changed the UI
WEB_DEMO=1 uv run uvicorn counterpoint.web.app:app --port 8000   # no agents needed
```

Once the frontend fully works, drop `WEB_DEMO` and connect to the real thing (`run_desk.sh` + normal backend) for final validation.
The fixture was captured from a real room via `desk.room_messages` (Chair key) and can be re-captured anytime.

New panels: a **pipeline progress timeline** (`/api/progress` derives stages from Band room messages),
a **native Band room live stream** (`/api/room` — Band sets `X-Frame-Options: SAMEORIGIN` so it can't be iframed; we read messages and render them ourselves), memo markdown rendering, a rating pill, and the sign-off gate.

> Note: the bundled `fixtures/demo.json` is a Chinese transcript, so demo mode shows Chinese memo content regardless of the UI language. An English demo would need a re-captured English fixture.

## Design notes / trade-offs

- **Initiator**: the Agent API has no separate "human" key, so the backend uses `data_steward`'s credentials as the room owner to initiate; the trigger message is technically sent by that agent (functionally, Chair researches as usual).
- **The signer is a real person, not an agent**: browser sign-off calls `record_signoff` **directly**, taking the signer from the form's real name (required). It does **not** go through an agent in the room — otherwise Chair would record the signer as an agent, breaking the human sign-off trail (hard constraint 5).
- **Delete when done**: this SDK's Agent/Human REST has **no delete-room endpoint**, so `teardown` approximates it by "removing **all** agent participants (including the owner)" — the room becomes an empty shell and stops generating polling load (avoiding Band's platform 429). A true delete needs the Enterprise/human API. **Cleanup runs only after sign-off lands (signed=true)**, so Chair isn't removed early and the sign-off isn't lost.
- **Progress**: one research round takes a few minutes (blind review→rebuttal→stress-test→synthesis); the frontend polls + shows an "in progress" status; mid-message streaming isn't implemented (a possible future enhancement).
- **Room mapping persistence**: `_rooms` (ticker→room_id) is persisted to `.web_rooms.json` (gitignored) so cleanup still works after a restart, avoiding dead-room leaks. Under rate limits, run one round at a time.
- **Hard constraint 6**: the page only shows the memo + human sign-off; it offers **no order/trade actions** whatsoever.

## Validation status

- ✅ Result display (`result.latest_result`) + routing + home page: offline unit-tested + verified with TestClient (reading real memos/TSLA).
- ⚠️ Create room / initiate / sign-off / cleanup (`desk.py`): written against the band-sdk REST API (create_agent_chat / add_agent_chat_participant / create_agent_chat_message / remove_agent_chat_participant), **not yet live-validated against real Band** (needs running agents + credentials + quota).
