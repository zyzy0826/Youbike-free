"""以 YouBike 站點為節點、騎乘時間為邊權重的圖建構模組。

只在「可用騎乘時間」半徑內連邊，避免完整圖 O(n²) 的儲存與計算成本。
"""
from __future__ import annotations

import networkx as nx
import pandas as pd


def build_station_graph(
    stations: pd.DataFrame,
    free_minutes: int,
    safety_margin: int,
    speed_kmh: float,
    detour_factor: float,
) -> nx.DiGraph:
    """以站點 DataFrame 建立有向圖。

    Args:
        stations: 經過標準化的站點 DataFrame。
        free_minutes: 該城市免費騎乘上限（分鐘）。
        safety_margin: 安全餘裕（分鐘）。實際上限 = free_minutes - safety_margin。
        speed_kmh: 平均騎乘時速。
        detour_factor: 路徑修正係數。

    Returns:
        NetworkX 有向圖。
        - 節點屬性：name, lat, lon, available_bikes, available_docks, city。
        - 邊屬性：weight（騎乘時間，分鐘）、distance_km。
    """
    raise NotImplementedError


def _candidate_neighbors(
    station_idx: int,
    stations: pd.DataFrame,
    max_radius_km: float,
) -> list[int]:
    """回傳指定站點在半徑內的候選鄰居 index 列表。"""
    raise NotImplementedError
