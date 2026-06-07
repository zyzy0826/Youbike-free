"""騎乘時間估算模組。

基於 haversine 直線距離乘上路徑修正係數，再除以平均時速。
"""
from __future__ import annotations

import math

from config import DEFAULT_CYCLING_SPEED_KMH, ROUTE_DETOUR_FACTOR

_EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """計算兩點間的 haversine 直線距離（公里）。"""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def estimate_riding_time(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    speed_kmh: float = DEFAULT_CYCLING_SPEED_KMH,
    detour_factor: float = ROUTE_DETOUR_FACTOR,
) -> float:
    """估算兩站間騎乘時間（分鐘）。"""
    actual_km = haversine_km(lat1, lon1, lat2, lon2) * detour_factor
    return (actual_km / speed_kmh) * 60


def estimate_walking_time(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    speed_kmh: float = 4.5,
) -> float:
    """估算步行時間（分鐘）。步行的繞路修正係數較低（1.2）。"""
    actual_km = haversine_km(lat1, lon1, lat2, lon2) * 1.2
    return (actual_km / speed_kmh) * 60
