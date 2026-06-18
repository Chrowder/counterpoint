"""supervise.py 的 spin 检测逻辑测试。"""

from counterpoint.supervise import SpinDetector

CATCHUP = "INFO:band.runtime.execution:ExecutionContext abc: Catching up missed message {id} via /next resync"


def test_detects_same_id_spin():
    d = SpinDetector(threshold=5)
    fires = [d.feed(CATCHUP.format(id="msg-1")) for _ in range(5)]
    assert fires[:4] == [False, False, False, False]
    assert fires[4] is True  # 第 5 次同 id 触发


def test_distinct_ids_do_not_trigger():
    """正常补漏是不同 id,连续多少条都不该触发。"""
    d = SpinDetector(threshold=3)
    assert not any(d.feed(CATCHUP.format(id=f"msg-{i}")) for i in range(20))


def test_unrelated_lines_ignored_and_reset_counts_by_id():
    d = SpinDetector(threshold=3)
    d.feed(CATCHUP.format(id="x"))
    d.feed("INFO:httpx:HTTP Request: GET /messages/next 204")  # 无关行,不计数
    d.feed(CATCHUP.format(id="x"))
    assert d.feed(CATCHUP.format(id="x")) is True  # x 累计 3 次触发


def test_id_change_resets_counter():
    d = SpinDetector(threshold=3)
    d.feed(CATCHUP.format(id="a"))
    d.feed(CATCHUP.format(id="a"))
    d.feed(CATCHUP.format(id="b"))  # 换 id,计数归 1
    assert d.feed(CATCHUP.format(id="b")) is False  # b 才第 2 次
