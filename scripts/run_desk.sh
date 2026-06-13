#!/usr/bin/env bash
# 一键拉起投研台全部 agent(Data Steward / Bull / Bear / Risk Officer / Chair),Ctrl+C 全部退出。
set -euo pipefail
cd "$(dirname "$0")/.."

trap 'kill 0' INT TERM

uv run python -m counterpoint.agents.data_steward &
uv run python -m counterpoint.agents.bull &
uv run python -m counterpoint.agents.bear &
uv run python -m counterpoint.agents.risk &
uv run python -m counterpoint.agents.chair &

wait
