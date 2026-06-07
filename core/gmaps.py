"""以 Google Maps Distance Matrix API 取得較貼近真實道路的騎乘時間。

設計重點：
    - Google Directions/Distance Matrix 的 ``bicycling`` 模式並非所有國家都支援，
      台灣常回傳 ZERO_RESULTS。因此採三層回退：
        1. bicycling：直接取單車時間。
        2. driving：取真實道路距離，再以單車速度換算時間（汽車時間偏快，故用距離）。
        3. 皆失敗 → 擲 GMapsError，由呼叫端回退到 haversine 估算。
    - 僅對「已選定路線的少數路段」呼叫，避免在百萬邊的圖上濫用配額。

需要網路與有效的 GOOGLE_MAPS_API_KEY。
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

from config import DEFAULT_CYCLING_SPEED_KMH

_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
_REQUEST_TIMEOUT = 10


class GMapsError(RuntimeError):
    """Google Maps 查詢失敗（金鑰錯誤、配額用盡、查無路線等）。"""


@dataclass
class TravelTime:
    """單一路段的行駛時間結果。"""
    minutes: float
    distance_km: float
    mode: str  # "bicycling"（單車時間）| "driving_distance"（道路距離換算）


def _query(
    o_lat: float, o_lon: float, d_lat: float, d_lon: float,
    mode: str, api_key: str,
) -> dict:
    params = {
        "origins": f"{o_lat},{o_lon}",
        "destinations": f"{d_lat},{d_lon}",
        "mode": mode,
        "key": api_key,
    }
    try:
        resp = requests.get(_DISTANCE_MATRIX_URL, params=params, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise GMapsError(f"Google Maps 請求失敗：{e}") from e

    top = data.get("status")
    if top != "OK":
        msg = data.get("error_message", "")
        raise GMapsError(f"Google Maps 狀態 {top} {msg}".strip())
    return data


def _element(data: dict) -> dict | None:
    """取出 rows[0].elements[0]，若結構不符或非 OK 回傳 None。"""
    try:
        el = data["rows"][0]["elements"][0]
    except (KeyError, IndexError):
        return None
    if el.get("status") != "OK":
        return None
    return el


def get_travel_time(
    o_lat: float, o_lon: float, d_lat: float, d_lon: float,
    api_key: str,
    speed_kmh: float = DEFAULT_CYCLING_SPEED_KMH,
) -> TravelTime:
    """取得單一路段的騎乘時間，依 bicycling → driving 距離換算回退。

    Raises:
        GMapsError: 兩種模式皆無法取得結果。
    """
    if not api_key:
        raise GMapsError("未設定 GOOGLE_MAPS_API_KEY")

    # 1) bicycling：若台灣支援則直接採用單車時間
    bike = _element(_query(o_lat, o_lon, d_lat, d_lon, "bicycling", api_key))
    if bike is not None:
        return TravelTime(
            minutes=bike["duration"]["value"] / 60.0,
            distance_km=bike["distance"]["value"] / 1000.0,
            mode="bicycling",
        )

    # 2) driving：取真實道路距離，以單車速度換算（汽車時間偏快，不直接用）
    drive = _element(_query(o_lat, o_lon, d_lat, d_lon, "driving", api_key))
    if drive is not None:
        dist_km = drive["distance"]["value"] / 1000.0
        return TravelTime(
            minutes=(dist_km / speed_kmh) * 60.0,
            distance_km=dist_km,
            mode="driving_distance",
        )

    raise GMapsError("Google Maps 查無此路段的單車或開車路線")
