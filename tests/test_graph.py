"""測試 haversine、騎乘時間估算、與圖建構。"""
from __future__ import annotations

import pandas as pd
import pytest

from core.time_estimator import haversine_km, estimate_riding_time
from core.graph_builder import build_station_graph


def test_haversine_same_point_zero():
    assert haversine_km(25.0, 121.5, 25.0, 121.5) == pytest.approx(0)


def test_haversine_known_distance():
    # 台北車站 (25.0478, 121.5170) 到 板橋車站 (25.0136, 121.4637) 約 6.0~6.5 km
    d = haversine_km(25.0478, 121.5170, 25.0136, 121.4637)
    assert 5.5 < d < 6.8


def test_estimate_riding_time_basic():
    # 同點 → 0
    assert estimate_riding_time(25.0, 121.5, 25.0, 121.5) == pytest.approx(0)
    # 1km 直線、12km/h、factor 1.3 → 1.3km / 12 * 60 = 6.5 分鐘
    # 構造一對緯度相距 ~1km 的點：1 度緯度 ≈ 111km
    minutes = estimate_riding_time(25.0, 121.5, 25.0 + 1 / 111.0, 121.5)
    assert 6.0 < minutes < 7.0


def _make_df(rows):
    df = pd.DataFrame(rows)
    df["available_bikes"] = df["available_bikes"].astype("Int64")
    df["available_docks"] = df["available_docks"].astype("Int64")
    return df


def test_graph_nodes_and_edges_within_radius():
    # 三個站，A-B 約 0.5km（應連邊），A-C 約 10km（不應連邊）
    stations = _make_df([
        {"station_id": "A", "name": "A", "lat": 25.000, "lon": 121.500,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
        {"station_id": "B", "name": "B", "lat": 25.0045, "lon": 121.500,
         "available_bikes": 3, "available_docks": 7, "city": "台北市"},
        {"station_id": "C", "name": "C", "lat": 25.090, "lon": 121.500,
         "available_bikes": 1, "available_docks": 9, "city": "台北市"},
    ])
    g = build_station_graph(
        stations, free_minutes=30, safety_margin=3,
        speed_kmh=12.0, detour_factor=1.3,
    )
    assert set(g.nodes) == {"A", "B", "C"}
    # A-B 應雙向連邊
    assert g.has_edge("A", "B") and g.has_edge("B", "A")
    # A-C 距離 ~10km，騎乘時間 ~65 分鐘 >> 27 分鐘上限 → 不連
    assert not g.has_edge("A", "C")
    # 所有邊權重不超過 free_minutes - safety_margin
    for _, _, data in g.edges(data=True):
        assert data["weight"] <= 27


def test_graph_node_attributes_preserved():
    stations = _make_df([
        {"station_id": "X", "name": "測試站", "lat": 25.0, "lon": 121.5,
         "available_bikes": 10, "available_docks": 5, "city": "台北市"},
    ])
    g = build_station_graph(
        stations, free_minutes=30, safety_margin=3,
        speed_kmh=12.0, detour_factor=1.3,
    )
    n = g.nodes["X"]
    assert n["name"] == "測試站"
    assert n["available_bikes"] == 10
    assert n["available_docks"] == 5
    assert n["city"] == "台北市"
