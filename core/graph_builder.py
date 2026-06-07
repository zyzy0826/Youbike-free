"""以 YouBike 站點為節點、騎乘時間為邊權重的圖建構模組。

只在「可用騎乘時間」半徑內連邊，避免完整圖 O(n²) 的儲存與計算成本。
"""
from __future__ import annotations

import numpy as np
import networkx as nx
import pandas as pd

from core.time_estimator import estimate_riding_time, haversine_km


def build_station_graph(
    stations: pd.DataFrame,
    free_minutes: int,
    safety_margin: int,
    speed_kmh: float,
    detour_factor: float,
) -> nx.DiGraph:
    """以站點 DataFrame 建立有向圖。

    Args:
        stations: 經過標準化與過濾的站點 DataFrame。
        free_minutes: 該城市免費騎乘上限（分鐘）。
        safety_margin: 安全餘裕（分鐘）。實際上限 = free_minutes - safety_margin。
        speed_kmh: 平均騎乘時速。
        detour_factor: 路徑修正係數。

    Returns:
        NetworkX 有向圖。
        節點屬性：name, lat, lon, available_bikes, available_docks, city。
        邊屬性：weight（騎乘時間，分鐘）、distance_km。
    """
    max_minutes = free_minutes - safety_margin
    max_km = max_minutes * speed_kmh / 60 / detour_factor

    g = nx.DiGraph()
    for _, row in stations.iterrows():
        g.add_node(
            row["station_id"],
            name=row["name"],
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            available_bikes=int(row["available_bikes"] or 0),
            available_docks=int(row["available_docks"] or 0),
            city=row["city"],
        )

    ids = stations["station_id"].to_numpy()
    lats = stations["lat"].to_numpy(dtype=float)
    lons = stations["lon"].to_numpy(dtype=float)
    n = len(ids)

    # 用經緯度粗略過濾再算 haversine：1 度緯度 ≈ 111km
    lat_window = max_km / 111.0

    for i in range(n):
        lat_i, lon_i = lats[i], lons[i]
        for j in _candidate_indices(i, lats, lons, lat_window):
            dist = haversine_km(lat_i, lon_i, lats[j], lons[j])
            if dist > max_km:
                continue
            minutes = estimate_riding_time(
                lat_i, lon_i, lats[j], lons[j], speed_kmh, detour_factor
            )
            if minutes <= max_minutes:
                g.add_edge(ids[i], ids[j], weight=minutes, distance_km=dist)
    return g


def _candidate_indices(
    i: int, lats: np.ndarray, lons: np.ndarray, lat_window: float
) -> np.ndarray:
    """粗略地用緯度視窗過濾候選鄰居，回傳 index 陣列（排除自己）。"""
    mask = np.abs(lats - lats[i]) <= lat_window
    mask[i] = False
    return np.where(mask)[0]
