"""帶免費時間約束的最短路徑演算法。

策略：
    - "fewest_swaps": BFS，邊權為 1，最小化換車次數。
    - "shortest_time": Dijkstra，邊權為騎乘時間，最小化總時間。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import networkx as nx
import pandas as pd


Strategy = Literal["fewest_swaps", "shortest_time"]


@dataclass
class RouteSegment:
    """單一騎乘段。"""
    from_station_id: str
    to_station_id: str
    from_name: str
    to_name: str
    minutes: float
    distance_km: float


@dataclass
class RoutePlan:
    """完整路線規劃結果。"""
    segments: list[RouteSegment]
    total_minutes: float
    swap_count: int
    walk_to_start_min: float
    walk_from_end_min: float
    strategy: Strategy
    feasible: bool
    message: str = ""


def find_nearest_station(
    lat: float,
    lon: float,
    stations: pd.DataFrame,
) -> tuple[str, float]:
    """找出距離指定座標最近的站點，回傳 (station_id, 距離公里)。"""
    raise NotImplementedError


def plan_route(
    graph: nx.DiGraph,
    stations: pd.DataFrame,
    origin: tuple[float, float],
    destination: tuple[float, float],
    strategy: Strategy = "fewest_swaps",
) -> RoutePlan:
    """規劃從 origin 到 destination 的免費騎乘路線。

    Args:
        graph: 已建好的站點圖。
        stations: 標準化站點 DataFrame。
        origin: (lat, lon) 起點座標。
        destination: (lat, lon) 終點座標。
        strategy: 路線策略。

    Returns:
        RoutePlan；若無解則 feasible=False 並附帶 message。
    """
    raise NotImplementedError
