"""設定模組：各縣市規則與騎乘參數。"""
from .city_rules import (
    CITY_CONFIG,
    LIVING_CIRCLES,
    CROSS_CIRCLE_FEE_NTD,
    DEFAULT_CYCLING_SPEED_KMH,
    ROUTE_DETOUR_FACTOR,
    SAFETY_MARGIN_MINUTES,
    city_to_circle,
)

__all__ = [
    "CITY_CONFIG",
    "LIVING_CIRCLES",
    "CROSS_CIRCLE_FEE_NTD",
    "DEFAULT_CYCLING_SPEED_KMH",
    "ROUTE_DETOUR_FACTOR",
    "SAFETY_MARGIN_MINUTES",
    "city_to_circle",
]
