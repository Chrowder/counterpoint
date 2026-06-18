#!/usr/bin/env bash
# 一键拉起投研台全部 agent(Data Steward / Bull / Bear / Risk Officer / Chair),Ctrl+C 全部退出。
set -euo pipefail
cd "$(dirname "$0")/.."

trap 'kill 0' INT TERM

# 每个 agent 套 supervise 看门狗:resync 死循环时自动重启(见 counterpoint/supervise.py)
uv run python -m counterpoint.supervise counterpoint.agents.data_steward &
uv run python -m counterpoint.supervise counterpoint.agents.bull &
uv run python -m counterpoint.supervise counterpoint.agents.bear &
uv run python -m counterpoint.supervise counterpoint.agents.risk &
uv run python -m counterpoint.supervise counterpoint.agents.chair &

wait
