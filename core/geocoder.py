"""地址 → 經緯度地理編碼模組。

使用 geopy 的 Nominatim（OpenStreetMap）服務。Nominatim 有使用條款限制
（每秒至多 1 次請求、需提供 user agent），故本模組內建簡易節流與行程內快取。

注意：此模組需要網路連線；沙箱環境下會擲出 GeocodeError。
"""
from __future__ import annotations

import threading
import time

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

# Nominatim 要求每個應用程式提供可識別的 user agent。
_USER_AGENT = "youbike-free-route-planner"
# Nominatim 使用條款：每秒最多 1 次請求。
_MIN_INTERVAL_SECONDS = 1.0
_REQUEST_TIMEOUT = 10

# 偏好台灣結果，避免同名地點落到國外。
_DEFAULT_COUNTRY_CODES = "tw"


class GeocodeError(RuntimeError):
    """地理編碼失敗（查無結果、逾時或服務錯誤）。"""


_lock = threading.Lock()
_last_request_ts = 0.0
_cache: dict[str, tuple[float, float]] = {}
_geocoder: Nominatim | None = None


def _get_geocoder() -> Nominatim:
    global _geocoder
    if _geocoder is None:
        _geocoder = Nominatim(user_agent=_USER_AGENT, timeout=_REQUEST_TIMEOUT)
    return _geocoder


def _throttle() -> None:
    """確保兩次請求間隔不小於 Nominatim 要求的最小間隔。"""
    global _last_request_ts
    elapsed = time.time() - _last_request_ts
    if elapsed < _MIN_INTERVAL_SECONDS:
        time.sleep(_MIN_INTERVAL_SECONDS - elapsed)
    _last_request_ts = time.time()


def _location_score(loc) -> float:
    """為候選地點評分：偏好「車站/景點等實際地點」，貶抑「路線/邊界等關係」。

    解決 Nominatim 對「X捷運站」常回傳整條捷運線（route relation）的問題。
    """
    raw = getattr(loc, "raw", None)
    if not isinstance(raw, dict):
        return 0.0
    cls = str(raw.get("class", ""))
    typ = str(raw.get("type", ""))
    osm_type = str(raw.get("osm_type", ""))
    score = 0.0
    if cls in ("railway", "public_transport") and typ in (
        "station", "stop", "halt", "stop_position", "subway_entrance"
    ):
        score += 6
    if osm_type == "node":      # 點（車站/地標）通常正是使用者要的
        score += 2
    if cls == "place":          # 行政區 / 地名
        score += 1
    if cls == "route":          # 公車/捷運「路線」，幾乎不會是使用者要的點
        score -= 6
    if osm_type == "relation" and cls in ("route", "boundary"):
        score -= 3
    try:                        # importance 作為次要 tie-break
        score += float(raw.get("importance", 0) or 0)
    except (TypeError, ValueError):
        pass
    return score


def geocode_address(
    address: str,
    country_codes: str | None = _DEFAULT_COUNTRY_CODES,
) -> tuple[float, float]:
    """將地址轉換為 (緯度, 經度)。"""
    lat, lon, _ = geocode_address_verbose(address, country_codes)
    return lat, lon


def geocode_address_verbose(
    address: str,
    country_codes: str | None = _DEFAULT_COUNTRY_CODES,
) -> tuple[float, float, str]:
    """將地址轉換為 (緯度, 經度, 匹配到的完整名稱)。

    回傳第三個值為 Nominatim 實際匹配到的地點全名，可用於讓使用者確認是否解析正確
    （例如輸入「淡水捷運站」卻被匹配到別處時，全名會一眼看出）。

    Args:
        address: 欲查詢的地址或地標名稱（如「台北車站」）。
        country_codes: 限定國家（ISO 3166-1 alpha-2，逗號分隔）。傳 None 不限定。

    Returns:
        (lat, lon) tuple。

    Raises:
        GeocodeError: 地址為空、查無結果、逾時或服務錯誤。
    """
    query = address.strip()
    if not query:
        raise GeocodeError("地址不可為空")

    cache_key = f"{country_codes}|{query}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    geocoder = _get_geocoder()
    with _lock:
        _throttle()
        try:
            # 取多筆候選再挑最合適者：避免「淡水捷運站」被配到「淡水信義線」整條路線
            # （路線是 relation，質心常落在大安區）。
            kwargs: dict = {"exactly_one": False, "limit": 10, "addressdetails": True}
            if country_codes:
                kwargs["country_codes"] = country_codes
            candidates = geocoder.geocode(query, **kwargs)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            raise GeocodeError(f"地理編碼服務錯誤：{e}") from e

    if not candidates:
        raise GeocodeError(f"查無此地址：{query}")

    best = max(candidates, key=_location_score)
    display = getattr(best, "address", None) or query
    result = (best.latitude, best.longitude, str(display))
    _cache[cache_key] = result
    return result
