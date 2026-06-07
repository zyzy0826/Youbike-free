"""檢視新北市 API 的欄位結構與正規化結果。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.fetcher import fetch_city_stations  # noqa: E402
from data.preprocessor import filter_invalid_stations, normalize_stations  # noqa: E402


def main() -> None:
    raw = fetch_city_stations("新北市")
    print(f"原始: {len(raw)} 站")
    print("第一筆 keys:", list(raw[0].keys()))
    print("第一筆 sample:", raw[0])

    df = normalize_stations(raw, "新北市")
    print("\n正規化後第一筆:")
    print(df.iloc[0].to_dict())
    print("\n各欄位 NaN/None 數量:")
    print(df.isna().sum())
    print(f"\nactive=True 數: {df['active'].sum()}")
    print(f"total > 0 數: {(df['total'].fillna(0) > 0).sum()}")
    print(f"lat 非 0 數: {(df['lat'].fillna(0) != 0).sum()}")

    clean = filter_invalid_stations(df)
    print(f"\n過濾後: {len(clean)} 站")


if __name__ == "__main__":
    main()
