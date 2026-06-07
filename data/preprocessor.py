"""資料清洗與欄位標準化模組。

各縣市 API 回傳欄位名稱不一致（例如 sno/StationID、sna/StationName），
本模組將其統一為標準欄位，並過濾異常站點。

標準欄位:
    station_id, name, lat, lon, total, available_bikes, available_docks,
    city, updated_at
"""
from __future__ import annotations

from typing import Any

import pandas as pd


STANDARD_COLUMNS = [
    "station_id",
    "name",
    "lat",
    "lon",
    "total",
    "available_bikes",
    "available_docks",
    "city",
    "updated_at",
]


def normalize_stations(raw: list[dict[str, Any]], city: str) -> pd.DataFrame:
    """將原始 API 資料正規化為標準 DataFrame。

    Args:
        raw: API 原始回傳的 station list。
        city: 縣市名稱（會寫入 city 欄位）。

    Returns:
        包含 STANDARD_COLUMNS 欄位的 DataFrame。
    """
    raise NotImplementedError


def filter_invalid_stations(df: pd.DataFrame) -> pd.DataFrame:
    """過濾異常站點：座標為 0、空名稱、總車位為 0 等。"""
    raise NotImplementedError


def merge_cities(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """合併多縣市資料為單一 DataFrame。"""
    raise NotImplementedError
