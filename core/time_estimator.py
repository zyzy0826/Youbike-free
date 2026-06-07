"""騎乘時間估算模組。

基於 haversine 直線距離乘上路徑修正係數，再除以平均時速。
"""
from __future__ import annotations

from config import DEFAULT_CYCLING_SPEED_KMH, ROUTE_DETOUR_FACTOR


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """計算兩點間的 haversine 直線距離（公里）。"""
    raise NotImplementedError


def estimate_riding_time(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    speed_kmh: float = DEFAULT_CYCLING_SPEED_KMH,
    detour_factor: float = ROUTE_DETOUR_FACTOR,
) -> float:
    """估算兩站間騎乘時間（分鐘）。

    Args:
        lat1, lon1: 起點座標。
        lat2, lon2: 終點座標。
        speed_kmh: 平均騎乘時速。
        detour_factor: 實際路徑相對直線距離的修正係數。

    Returns:
        預估騎乘時間（分鐘）。
    """
    raise NotImplementedError


def estimate_walking_time(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    speed_kmh: float = 4.5,
) -> float:
    """估算步行時間（分鐘），用於起終點到最近站。"""
    raise NotImplementedError
