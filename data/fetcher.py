"""YouBike Open API 資料擷取模組。

負責呼叫各縣市公開 API，取得即時站點資料，並提供本地 JSON 快取以避免重複請求。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
import urllib3

from config import CITY_CONFIG

# 部分政府開放資料 API 的憑證有瑕疵（例如新北市 data.ntpc.gov.tw 缺 Subject Key
# Identifier），對應 city 會以 verify_ssl=False 連線。抑制相關警告以保持 CLI 乾淨。
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE_DIR = Path(__file__).parent / "cache"
DEFAULT_CACHE_TTL_SECONDS = 300  # 5 分鐘
REQUEST_TIMEOUT = 15


class FetchError(RuntimeError):
    """API 擷取失敗。"""


def fetch_city_stations(
    city: str,
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
    cache_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """擷取指定縣市的所有 YouBike 站點即時資料。

    Args:
        city: 縣市名稱（須存在於 CITY_CONFIG）。
        use_cache: 是否使用本地快取。
        cache_ttl: 快取有效秒數。
        cache_dir: 自訂快取目錄（測試用）。

    Returns:
        站點資料列表，每筆為原始 API 回傳的 dict。
    """
    if city not in CITY_CONFIG:
        raise ValueError(f"未知縣市: {city}")
    cfg = CITY_CONFIG[city]
    api_url = cfg["api_url"]
    if not api_url or api_url.startswith("TODO"):
        raise FetchError(f"{city} 的 API URL 尚未設定")
    verify_ssl = cfg.get("verify_ssl", True)

    base = cache_dir or CACHE_DIR

    if use_cache:
        cached = _load_cache(city, cache_ttl, base)
        if cached is not None:
            return cached

    try:
        resp = requests.get(api_url, timeout=REQUEST_TIMEOUT, verify=verify_ssl)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise FetchError(f"擷取 {city} 失敗: {e}") from e

    if not isinstance(data, list):
        raise FetchError(f"{city} API 回傳格式非 list: {type(data).__name__}")

    _save_cache(city, data, base)
    return data


def _cache_path(city: str, base: Path) -> Path:
    return base / f"{city}.json"


def _load_cache(city: str, ttl: int, base: Path) -> list[dict[str, Any]] | None:
    """讀取快取，若過期或不存在則回傳 None。"""
    path = _cache_path(city, base)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > ttl:
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(city: str, data: list[dict[str, Any]], base: Path) -> None:
    """將擷取結果寫入 JSON 快取檔。"""
    base.mkdir(parents=True, exist_ok=True)
    path = _cache_path(city, base)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def fetch_all_cities(
    cities: list[str],
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
) -> dict[str, list[dict[str, Any]]]:
    """批次擷取多個縣市的站點資料。擷取失敗的城市會被略過並印出警告。"""
    result: dict[str, list[dict[str, Any]]] = {}
    for city in cities:
        try:
            result[city] = fetch_city_stations(city, use_cache, cache_ttl)
        except (FetchError, ValueError) as e:
            print(f"[警告] 略過 {city}: {e}")
    return result
