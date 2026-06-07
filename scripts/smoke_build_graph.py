"""煙霧測試：抓台北資料 → 正規化 → 過濾 → 建圖，量測耗時。"""
import time

from data.fetcher import fetch_city_stations
from data.preprocessor import filter_invalid_stations, normalize_stations
from core.graph_builder import build_station_graph


def main() -> None:
    raw = fetch_city_stations("台北市")
    df = filter_invalid_stations(normalize_stations(raw, "台北市"))
    print(f"有效站點: {len(df)}")

    t0 = time.time()
    g = build_station_graph(
        df, free_minutes=30, safety_margin=3, speed_kmh=12.0, detour_factor=1.3
    )
    print(
        f"建圖耗時: {time.time() - t0:.1f}s, "
        f"節點={g.number_of_nodes()}, 邊={g.number_of_edges()}"
    )


if __name__ == "__main__":
    main()
