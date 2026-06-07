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

from core.time_estimator import estimate_walking_time, haversine_km


Strategy = Literal["fewest_swaps", "shortest_time"]

MAX_WALK_KM = 1.0  # 起終點到最近站可接受的最大步行距離


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
    lat: float, lon: float, stations: pd.DataFrame
) -> tuple[str, float]:
    """找出距離指定座標最近的站點，回傳 (station_id, 距離公里)。"""
    if stations.empty:
        raise ValueError("stations DataFrame 為空")
    lats = stations["lat"].to_numpy(dtype=float)
    lons = stations["lon"].to_numpy(dtype=float)
    dists = [haversine_km(lat, lon, la, lo) for la, lo in zip(lats, lons)]
    idx = min(range(len(dists)), key=dists.__getitem__)
    return str(stations.iloc[idx]["station_id"]), dists[idx]


def _build_segments(
    graph: nx.DiGraph, node_path: list[str]
) -> tuple[list[RouteSegment], float]:
    """從節點路徑建構 RouteSegment 列表並計算總時間。"""
    segments: list[RouteSegment] = []
    total = 0.0
    for u, v in zip(node_path[:-1], node_path[1:]):
        data = graph.edges[u, v]
        segments.append(
            RouteSegment(
                from_station_id=u,
                to_station_id=v,
                from_name=graph.nodes[u]["name"],
                to_name=graph.nodes[v]["name"],
                minutes=data["weight"],
                distance_km=data["distance_km"],
            )
        )
        total += data["weight"]
    return segments, total


def plan_route(
    graph: nx.DiGraph,
    stations: pd.DataFrame,
    origin: tuple[float, float],
    destination: tuple[float, float],
    strategy: Strategy = "fewest_swaps",
) -> RoutePlan:
    """規劃從 origin 到 destination 的免費騎乘路線。"""
    o_lat, o_lon = origin
    d_lat, d_lon = destination

    start_id, start_dist = find_nearest_station(o_lat, o_lon, stations)
    end_id, end_dist = find_nearest_station(d_lat, d_lon, stations)
    walk_to_start = estimate_walking_time(
        o_lat, o_lon,
        graph.nodes[start_id]["lat"], graph.nodes[start_id]["lon"],
    )
    walk_from_end = estimate_walking_time(
        graph.nodes[end_id]["lat"], graph.nodes[end_id]["lon"],
        d_lat, d_lon,
    )

    def _fail(msg: str) -> RoutePlan:
        return RoutePlan(
            segments=[], total_minutes=0.0, swap_count=0,
            walk_to_start_min=walk_to_start, walk_from_end_min=walk_from_end,
            strategy=strategy, feasible=False, message=msg,
        )

    if start_dist > MAX_WALK_KM:
        return _fail(f"起點附近 {MAX_WALK_KM}km 內無 YouBike 站（最近 {start_dist:.2f}km）")
    if end_dist > MAX_WALK_KM:
        return _fail(f"終點附近 {MAX_WALK_KM}km 內無 YouBike 站（最近 {end_dist:.2f}km）")

    if start_id == end_id:
        return RoutePlan(
            segments=[], total_minutes=0.0, swap_count=0,
            walk_to_start_min=walk_to_start, walk_from_end_min=walk_from_end,
            strategy=strategy, feasible=True,
            message="起終點最近站為同一站，直接步行即可",
        )

    try:
        if strategy == "fewest_swaps":
            node_path = nx.shortest_path(graph, start_id, end_id)
        elif strategy == "shortest_time":
            node_path = nx.shortest_path(graph, start_id, end_id, weight="weight")
        else:
            raise ValueError(f"未知策略: {strategy}")
    except nx.NetworkXNoPath:
        return _fail("找不到可行的免費路線（站點之間距離過遠），建議直接付費騎乘")
    except nx.NodeNotFound as e:
        return _fail(f"圖中找不到節點: {e}")

    segments, total = _build_segments(graph, node_path)
    return RoutePlan(
        segments=segments,
        total_minutes=total,
        swap_count=max(0, len(segments) - 1),
        walk_to_start_min=walk_to_start,
        walk_from_end_min=walk_from_end,
        strategy=strategy,
        feasible=True,
    )
