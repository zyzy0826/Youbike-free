"""Folium 地圖渲染：站點標記、路線繪製、換車點標示。"""
from __future__ import annotations

import folium
import pandas as pd

from core.route_optimizer import RoutePlan


def render_base_map(
    stations: pd.DataFrame,
    center: tuple[float, float] | None = None,
    zoom_start: int = 13,
) -> folium.Map:
    """建立含所有站點 CircleMarker 的底圖。

    站點顏色：
        綠色 = 有車且有位
        橘色 = 車輛或空位 < 3
        紅色 = 無車或滿位
    """
    raise NotImplementedError


def draw_route(
    m: folium.Map,
    plan: RoutePlan,
    stations: pd.DataFrame,
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> folium.Map:
    """在地圖上繪製推薦路線、換車站、起終點。"""
    raise NotImplementedError


def _station_color(available_bikes: int, available_docks: int) -> str:
    """依車輛/空位數回傳 marker 顏色。"""
    raise NotImplementedError
