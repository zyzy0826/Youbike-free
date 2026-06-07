"""Folium 地圖渲染：站點標記、路線繪製、換車點標示。"""
from __future__ import annotations

import folium
import pandas as pd

from core.route_optimizer import RoutePlan

LOW_THRESHOLD = 3


def _station_color(available_bikes: int, available_docks: int) -> str:
    """依車輛 / 空位數回傳 marker 顏色。"""
    if available_bikes == 0 or available_docks == 0:
        return "red"
    if available_bikes < LOW_THRESHOLD or available_docks < LOW_THRESHOLD:
        return "orange"
    return "green"


def render_base_map(
    stations: pd.DataFrame,
    center: tuple[float, float] | None = None,
    zoom_start: int = 13,
) -> folium.Map:
    """建立含所有站點 CircleMarker 的底圖。"""
    if center is None:
        center = (float(stations["lat"].mean()), float(stations["lon"].mean()))
    m = folium.Map(location=center, zoom_start=zoom_start, tiles="OpenStreetMap")
    fg = folium.FeatureGroup(name="站點")
    for _, row in stations.iterrows():
        bikes = int(row["available_bikes"] or 0)
        docks = int(row["available_docks"] or 0)
        color = _station_color(bikes, docks)
        folium.CircleMarker(
            location=(row["lat"], row["lon"]),
            radius=4,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(
                f"<b>{row['name']}</b><br>"
                f"可借: {bikes} / 可還: {docks}<br>"
                f"{row['city']}",
                max_width=250,
            ),
        ).add_to(fg)
    fg.add_to(m)
    return m


def draw_route(
    m: folium.Map,
    plan: RoutePlan,
    stations: pd.DataFrame,
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> folium.Map:
    """在地圖上繪製推薦路線、換車站、起終點。"""
    folium.Marker(
        location=origin,
        popup="起點",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
    ).add_to(m)
    folium.Marker(
        location=destination,
        popup="終點",
        icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
    ).add_to(m)

    if not plan.feasible or not plan.segments:
        return m

    coords_by_id = stations.set_index("station_id")[["lat", "lon"]].to_dict("index")
    polyline: list[tuple[float, float]] = []

    for i, seg in enumerate(plan.segments):
        a = coords_by_id[seg.from_station_id]
        b = coords_by_id[seg.to_station_id]
        if not polyline:
            polyline.append((a["lat"], a["lon"]))
        polyline.append((b["lat"], b["lon"]))

        # 中點標示騎乘時間
        mid_lat = (a["lat"] + b["lat"]) / 2
        mid_lon = (a["lon"] + b["lon"]) / 2
        folium.Marker(
            location=(mid_lat, mid_lon),
            icon=folium.DivIcon(
                icon_size=(80, 20),
                icon_anchor=(40, 10),
                html=(
                    f'<div style="font-size:11px;font-weight:bold;color:#1f4e8c;'
                    f'background:rgba(255,255,255,0.85);border-radius:4px;'
                    f'padding:1px 4px;text-align:center;">'
                    f'{seg.minutes:.0f} 分</div>'
                ),
            ),
        ).add_to(m)

        # 換車站（中間站）以星號 marker 標示
        if i < len(plan.segments) - 1:
            folium.Marker(
                location=(b["lat"], b["lon"]),
                popup=folium.Popup(
                    f"<b>換車點 #{i + 1}</b><br>{seg.to_name}<br>"
                    f"上一段: {seg.minutes:.1f} 分 / {seg.distance_km:.2f} km",
                    max_width=250,
                ),
                icon=folium.Icon(color="blue", icon="exchange", prefix="fa"),
            ).add_to(m)

    folium.PolyLine(
        locations=polyline,
        color="#1f4e8c",
        weight=5,
        opacity=0.75,
    ).add_to(m)

    return m
