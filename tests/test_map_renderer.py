"""測試地圖渲染：顏色判斷、底圖建立、路線繪製不出錯。"""
from __future__ import annotations

import pandas as pd

from core.route_optimizer import RoutePlan, RouteSegment
from visualization.map_renderer import _station_color, draw_route, render_base_map


def test_station_color_thresholds():
    assert _station_color(0, 5) == "red"
    assert _station_color(5, 0) == "red"
    assert _station_color(2, 5) == "orange"
    assert _station_color(5, 2) == "orange"
    assert _station_color(5, 5) == "green"
    assert _station_color(100, 100) == "green"


def _sample_stations():
    df = pd.DataFrame([
        {"station_id": "A", "name": "A", "lat": 25.0, "lon": 121.5,
         "available_bikes": 5, "available_docks": 5, "city": "台北市"},
        {"station_id": "B", "name": "B", "lat": 25.01, "lon": 121.51,
         "available_bikes": 0, "available_docks": 10, "city": "台北市"},
    ])
    df["available_bikes"] = df["available_bikes"].astype("Int64")
    df["available_docks"] = df["available_docks"].astype("Int64")
    return df


def test_render_base_map_returns_folium_map():
    import folium
    m = render_base_map(_sample_stations())
    assert isinstance(m, folium.Map)
    # 渲染為 HTML 應成功且包含站名
    html = m._repr_html_()
    assert "A" in html


def test_draw_route_with_feasible_plan():
    import folium
    stations = _sample_stations()
    plan = RoutePlan(
        segments=[
            RouteSegment("A", "B", "A", "B", minutes=10.0, distance_km=1.5),
        ],
        total_minutes=10.0,
        swap_count=0,
        walk_to_start_min=2.0,
        walk_from_end_min=2.0,
        strategy="fewest_swaps",
        feasible=True,
    )
    m = render_base_map(stations)
    out = draw_route(m, plan, stations, (25.0, 121.5), (25.01, 121.51))
    assert isinstance(out, folium.Map)
    html = out._repr_html_()
    assert "起點" in html and "終點" in html


def test_draw_route_with_infeasible_plan_still_marks_endpoints():
    stations = _sample_stations()
    plan = RoutePlan(
        segments=[], total_minutes=0, swap_count=0,
        walk_to_start_min=0, walk_from_end_min=0,
        strategy="fewest_swaps", feasible=False, message="無路",
    )
    m = render_base_map(stations)
    out = draw_route(m, plan, stations, (25.0, 121.5), (25.01, 121.51))
    html = out._repr_html_()
    assert "起點" in html and "終點" in html
