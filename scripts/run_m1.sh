#!/usr/bin/env bash
# 一键拉起 M1 的三个 agent(Data Steward / Bull / Chair),Ctrl+C 全部退出。
set -euo pipefail
cd "$(dirname "$0")/.."

trap 'kill 0' INT TERM

uv run python -m counterpoint.agents.data_steward &
uv run python -m counterpoint.agents.bull &
uv run python -m counterpoint.agents.chair &

wait
