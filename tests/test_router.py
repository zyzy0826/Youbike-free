"""測試路徑演算法（含邊界情況）。"""
from __future__ import annotations

import pandas as pd

import pytest

from core.graph_builder import build_station_graph
from core.route_optimizer import find_nearest_station, plan_route
from core.time_estimator import haversine_km


def _make_stations(rows):
    df = pd.DataFrame(rows)
    df["available_bikes"] = df["available_bikes"].astype("Int64")
    df["available_docks"] = df["available_docks"].astype("Int64")
    return df


# 一條東西向直線上的 4 站，間距各約 1km
# 1 度經度在緯度 25 約 100.7km；1km ≈ 0.00993 度
DEG_PER_KM = 1 / 100.7

STATIONS = _make_stations([
    {"station_id": "A", "name": "A", "lat": 25.0, "lon": 121.5,
     "available_bikes": 5, "available_docks": 5, "city": "台北市"},
    {"station_id": "B", "name": "B", "lat": 25.0, "lon": 121.5 + DEG_PER_KM,
     "available_bikes": 5, "available_docks": 5, "city": "台北市"},
    {"station_id": "C", "name": "C", "lat": 25.0, "lon": 121.5 + 2 * DEG_PER_KM,
     "available_bikes": 5, "available_docks": 5, "city": "台北市"},
    {"station_id": "D", "name": "D", "lat": 25.0, "lon": 121.5 + 3 * DEG_PER_KM,
     "available_bikes": 5, "available_docks": 5, "city": "台北市"},
])


def _build():
    return build_station_graph(
        STATIONS, free_minutes=30, safety_margin=3,
        speed_kmh=12.0, detour_factor=1.3,
    )


def test_find_nearest_station():
    sid, dist = find_nearest_station(25.0, 121.5 + DEG_PER_KM * 0.1, STATIONS)
    assert sid == "A"
    assert dist < 0.2


def test_find_nearest_station_matches_scalar_haversine():
    # 向量化結果應與逐站 scalar haversine 一致
    qlat, qlon = 25.0, 121.5 + DEG_PER_KM * 2.4  # 介於 C、D 之間，偏 C
    sid, dist = find_nearest_station(qlat, qlon, STATIONS)
    expected = min(
        ((r.station_id, haversine_km(qlat, qlon, r.lat, r.lon))
         for r in STATIONS.itertuples()),
        key=lambda t: t[1],
    )
    assert sid == expected[0]
    assert dist == pytest.approx(expected[1])


def test_direct_route_when_within_free_time():
    g = _build()
    plan = plan_route(g, STATIONS, (25.0, 121.5), (25.0, 121.5 + DEG_PER_KM))
    assert plan.feasible
    assert len(plan.segments) == 1
    assert plan.segments[0].from_station_id == "A"
    assert plan.segments[0].to_station_id == "B"
    assert plan.swap_count == 0


def test_route_to_far_station():
    g = _build()
    # A → D 約 3km × 1.3 / 12 * 60 ≈ 19.5 分 < 27 分上限 → 直達
    plan = plan_route(g, STATIONS, (25.0, 121.5), (25.0, 121.5 + 3 * DEG_PER_KM))
    assert plan.feasible
    assert plan.segments[-1].to_station_id == "D"


def test_fewest_swaps_strategy():
    g = _build()
    plan = plan_route(
        g, STATIONS, (25.0, 121.5), (25.0, 121.5 + 3 * DEG_PER_KM),
        strategy="fewest_swaps",
    )
    assert plan.feasible
    assert plan.strategy == "fewest_swaps"
    assert plan.swap_count == 0


def test_origin_too_far_from_any_station():
    g = _build()
    plan = plan_route(g, STATIONS, (25.02, 121.5), (25.0, 121.5))
    assert not plan.feasible
    assert "起點" in plan.message


def test_cross_circle_edges_blocked_by_default():
    # 一站在台北市（北北桃），一站在高雄市（嘉南高屏），距離雖近但不該連邊
    cross = _make_stations([
        {"station_id": "TP", "name": "TP", "lat": 25.0, "lon": 121.5,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
        {"station_id": "KH", "name": "KH", "lat": 25.0, "lon": 121.5005,
         "available_bikes": 5, "available_docks": 5, "city": "高雄市"},
    ])
    g = build_station_graph(cross, 30, 3, 12.0, 1.3)
    assert not g.has_edge("TP", "KH")
    assert not g.has_edge("KH", "TP")


def test_cross_circle_edges_allowed_with_flag():
    cross = _make_stations([
        {"station_id": "TP", "name": "TP", "lat": 25.0, "lon": 121.5,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
        {"station_id": "KH", "name": "KH", "lat": 25.0, "lon": 121.5005,
         "available_bikes": 5, "available_docks": 5, "city": "高雄市"},
    ])
    g = build_station_graph(cross, 30, 3, 12.0, 1.3, allow_cross_circle=True)
    assert g.has_edge("TP", "KH")
    plan = plan_route(g, cross, (25.0, 121.5), (25.0, 121.5005))
    assert plan.feasible
    assert "調度費" in plan.message


def test_no_path_returns_friendly_message():
    isolated = _make_stations([
        {"station_id": "X", "name": "X", "lat": 25.0, "lon": 121.5,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
        {"station_id": "Y", "name": "Y", "lat": 25.5, "lon": 122.0,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
    ])
    g = build_station_graph(
        isolated, free_minutes=30, safety_margin=3,
        speed_kmh=12.0, detour_factor=1.3,
    )
    plan = plan_route(g, isolated, (25.0, 121.5), (25.5, 122.0))
    assert not plan.feasible
