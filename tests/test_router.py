"""測試路徑演算法（含邊界情況）。"""
import pytest


def test_direct_route_when_within_free_time():
    """起終點站間騎乘時間 < 免費上限時，應為單段路線。"""
    pytest.skip("Phase 3 待實作")


def test_multi_swap_route():
    """較長路程應規劃多次換車。"""
    pytest.skip("Phase 3 待實作")


def test_no_feasible_route_returns_message():
    """孤立站點應回傳 feasible=False。"""
    pytest.skip("Phase 3 待實作")


def test_fewest_swaps_vs_shortest_time():
    """兩種策略可能產生不同結果。"""
    pytest.skip("Phase 3 待實作")
