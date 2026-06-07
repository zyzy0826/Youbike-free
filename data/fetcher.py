"""YouBike Open API 資料擷取模組。

負責呼叫各縣市公開 API，取得即時站點資料，並提供本地 JSON 快取以避免重複請求。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).parent / "cache"
DEFAULT_CACHE_TTL_SECONDS = 300  # 5 分鐘


def fetch_city_stations(
    city: str,
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
) -> list[dict[str, Any]]:
    """擷取指定縣市的所有 YouBike 站點即時資料。

    Args:
        city: 縣市名稱（須存在於 CITY_CONFIG）。
        use_cache: 是否使用本地快取。
        cache_ttl: 快取有效秒數。

    Returns:
        站點資料列表，每筆為原始 API 回傳的 dict。
    """
    raise NotImplementedError


def _load_cache(city: str, ttl: int) -> list[dict[str, Any]] | None:
    """讀取快取，若過期或不存在則回傳 None。"""
    raise NotImplementedError


def _save_cache(city: str, data: list[dict[str, Any]]) -> None:
    """將擷取結果寫入 JSON 快取檔。"""
    raise NotImplementedError


def fetch_all_cities(cities: list[str]) -> dict[str, list[dict[str, Any]]]:
    """批次擷取多個縣市的站點資料。"""
    raise NotImplementedError
