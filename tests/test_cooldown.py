"""測試 node-split 冷卻路徑模型。"""
from __future__ import annotations

import pandas as pd

from core.cooldown import build_cooldown_graph, plan_cooldown_route


def _make_df(rows):
    df = pd.DataFrame(rows)
    df["available_bikes"] = df["available_bikes"].astype("Int64")
    df["available_docks"] = df["available_docks"].astype("Int64")
    return df


DEG_PER_KM = 1 / 100.7

# 三站東西向：P0、P1（距 P0 約 3km）、P2（距 P0 約 6km）。
# P1 旁 60m 有 P1b（步行換車的替代借車站）。
LINE = _make_df([
    {"station_id": "P0", "name": "P0", "lat": 25.0, "lon": 121.5,
     "available_bikes": 5, "available_docks": 5, "city": "台北市"},
    {"station_id": "P1", "name": "P1", "lat": 25.0, "lon": 121.5 + 3 * DEG_PER_KM,
     "available_bikes": 5, "available_docks": 5, "city": "台北市"},
    {"station_id": "P1b", "name": "P1b", "lat": 25.0, "lon": 121.5 + 3 * DEG_PER_KM + 0.06 * DEG_PER_KM,
     "available_bikes": 5, "available_docks": 5, "city": "台北市"},
    {"station_id": "P2", "name": "P2", "lat": 25.0, "lon": 121.5 + 6 * DEG_PER_KM,
     "available_bikes": 5, "available_docks": 5, "city": "台北市"},
])


def _graph(**kw):
    return build_cooldown_graph(
        LINE, free_minutes=30, safety_margin=3,
        speed_kmh=12.0, detour_factor=1.3, **kw,
    )


def test_split_nodes_and_edge_modes():
    g = _graph()
    # 每站都有 in / out 兩節點
    for sid in ("P0", "P1", "P2", "P1b"):
        assert (sid, "in") in g.nodes
        assert (sid, "out") in g.nodes
    # wait 邊：同站 in -> out
    assert g.edges[("P0", "in"), ("P0", "out")]["mode"] == "wait"
    # ride 邊：out -> in
    assert g.edges[("P0", "out"), ("P1", "in")]["mode"] == "ride"
    # walk 邊：P1 in -> P1b out（約 60m）
    assert g.edges[("P1", "in"), ("P1b", "out")]["mode"] == "walk"


def test_shortest_time_prefers_walk_over_wait():
    # P0→P2 需換車一次。步行到 P1b（~0.8 分）應比原站等冷卻（12 分）省時。
    g = _graph()
    plan = plan_cooldown_route(
        g, LINE, (25.0, 121.5), (25.0, 121.5 + 6 * DEG_PER_KM),
        strategy="shortest_time",
    )
    assert plan.feasible
    modes = [s.mode for s in plan.segments]
    assert "ride" in modes
    # 轉乘採步行而非等待
    assert "walk" in modes
    assert "wait" not in modes
    # 換車一次：兩段騎乘
    assert plan.swap_count == 1
    assert sum(1 for s in plan.segments if s.mode == "ride") == 2
    # 轉乘時間 = 步行分鐘（>0 但遠小於 12 分冷卻）
    assert 0 < plan.transfer_minutes < 5


def test_wait_used_when_no_walk_neighbor():
    # 沒有鄰近替代站時，換車只能在原站等冷卻
    line = _make_df([
        {"station_id": "Q0", "name": "Q0", "lat": 25.0, "lon": 121.5,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
        {"station_id": "Q1", "name": "Q1", "lat": 25.0, "lon": 121.5 + 3 * DEG_PER_KM,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
        {"station_id": "Q2", "name": "Q2", "lat": 25.0, "lon": 121.5 + 6 * DEG_PER_KM,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
    ])
    g = build_cooldown_graph(
        line, free_minutes=30, safety_margin=3, speed_kmh=12.0, detour_factor=1.3,
    )
    plan = plan_cooldown_route(
        g, line, (25.0, 121.5), (25.0, 121.5 + 6 * DEG_PER_KM),
        strategy="shortest_time",
    )
    assert plan.feasible
    assert "wait" in [s.mode for s in plan.segments]
    assert plan.transfer_minutes >= 12.0  # 至少一次冷卻


def test_unreachable_returns_infeasible():
    far = _make_df([
        {"station_id": "X", "name": "X", "lat": 25.0, "lon": 121.5,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
        {"station_id": "Y", "name": "Y", "lat": 25.5, "lon": 122.0,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
    ])
    g = build_cooldown_graph(
        far, free_minutes=30, safety_margin=3, speed_kmh=12.0, detour_factor=1.3,
    )
    plan = plan_cooldown_route(g, far, (25.0, 121.5), (25.5, 122.0))
    assert not plan.feasible
