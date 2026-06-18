"""Agent 看门狗:监控子进程输出,检测到 resync 死循环就重启它。

背景(CLAUDE.md 有记):Band SDK 偶发漏消息后走 /next resync 补,某些情况下(LangGraph
适配器上见过)会陷入"Catching up missed message <同一 id>"的无限循环——同一条消息被
反复返回却始终标记不成功。SDK 内部状态卡死,唯一可靠恢复是整进程重启(重连后经 /context
重新同步即正常)。本看门狗把"人工重启"自动化:同一 id 连续 catch-up 超阈值 → 杀掉重启。

用法:python -m counterpoint.supervise counterpoint.agents.bear
"""

import re
import subprocess
import sys
import time

# 同一条消息连续被 catch-up 这么多次,判定为 spin(正常补漏是不同 id,不会连续同 id)
SPIN_THRESHOLD = 30
RESTART_BACKOFF_S = 3

_CATCHUP_RE = re.compile(r"Catching up missed message (\S+) via /next resync")


class SpinDetector:
    """逐行喂日志,同一条消息连续 catch-up 达阈值时 feed() 返回 True。"""

    def __init__(self, threshold: int = SPIN_THRESHOLD):
        self.threshold = threshold
        self._last_id: str | None = None
        self._repeat = 0

    def feed(self, line: str) -> bool:
        m = _CATCHUP_RE.search(line)
        if not m:
            return False  # 非 catch-up 行不影响计数(spin 是连续同 id,中间无其他 catch-up)
        msg_id = m.group(1)
        self._repeat = self._repeat + 1 if msg_id == self._last_id else 1
        self._last_id = msg_id
        return self._repeat >= self.threshold


def _run_once(module: str) -> str:
    """跑一个 agent 子进程,边转发日志边盯 spin。

    返回 'spin'(检测到死循环,需重启)或 'exit'(子进程自己结束,不重启)。
    """
    proc = subprocess.Popen(
        [sys.executable, "-m", module],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    detector = SpinDetector()
    try:
        for line in proc.stdout:  # 逐行读子进程输出
            sys.stdout.write(line)  # 原样转发,日志照常可见
            sys.stdout.flush()
            if detector.feed(line):
                print(
                    f"[supervise] 检测到 resync 死循环,重启 {module}", flush=True
                )
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return "spin"
        proc.wait()
        return "exit"
    except KeyboardInterrupt:
        proc.terminate()
        raise


def main() -> None:
    if len(sys.argv) != 2:
        print("用法:python -m counterpoint.supervise <module>", file=sys.stderr)
        sys.exit(2)
    module = sys.argv[1]
    while True:
        outcome = _run_once(module)
        if outcome == "exit":
            break  # 子进程正常退出(如 Ctrl+C),不重启
        time.sleep(RESTART_BACKOFF_S)


if __name__ == "__main__":
    main()
