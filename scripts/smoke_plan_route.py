"""煙霧測試：台北車站 → 淡水站，規劃免費路線。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.fetcher import fetch_city_stations  # noqa: E402
from data.preprocessor import (  # noqa: E402
    filter_invalid_stations,
    merge_cities,
    normalize_stations,
)
from core.graph_builder import build_station_graph  # noqa: E402
from core.route_optimizer import plan_route  # noqa: E402

TAIPEI_MAIN_STATION = (25.0478, 121.5170)
TAMSUI_MRT = (25.1677, 121.4456)


def main() -> None:
    dfs = []
    for city in ("台北市", "新北市"):
        raw = fetch_city_stations(city)
        dfs.append(normalize_stations(raw, city))
        print(f"{city} 原始: {len(raw)} 站")
    df = filter_invalid_stations(merge_cities(dfs))
    print(f"合併後有效站點: {len(df)}")

    t0 = time.time()
    g = build_station_graph(df, 30, 3, 12.0, 1.3)
    print(f"建圖耗時: {time.time() - t0:.1f}s, 邊={g.number_of_edges()}")

    for strategy in ("fewest_swaps", "shortest_time"):
        print(f"\n--- 策略: {strategy} ---")
        t0 = time.time()
        plan = plan_route(g, df, TAIPEI_MAIN_STATION, TAMSUI_MRT, strategy=strategy)
        print(f"規劃耗時: {(time.time() - t0) * 1000:.1f}ms")
        if not plan.feasible:
            print(f"無解: {plan.message}")
            continue
        print(
            f"換車次數: {plan.swap_count}, 總騎乘: {plan.total_minutes:.1f} 分, "
            f"步行起 {plan.walk_to_start_min:.1f} 分 / 步行終 {plan.walk_from_end_min:.1f} 分"
        )
        for i, seg in enumerate(plan.segments, 1):
            print(f"  [{i}] {seg.from_name} → {seg.to_name} "
                  f"({seg.minutes:.1f} 分, {seg.distance_km:.2f} km)")


if __name__ == "__main__":
    main()
