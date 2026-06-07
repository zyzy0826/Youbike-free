"""產出 Taipei→Tamsui 路線地圖 HTML，瀏覽器開啟肉眼驗證。"""
import sys
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
from visualization.map_renderer import draw_route, render_base_map  # noqa: E402

ORIGIN = (25.0478, 121.5170)       # 台北車站
DESTINATION = (25.1677, 121.4456)  # 淡水捷運站


def main() -> None:
    dfs = [
        normalize_stations(fetch_city_stations(c), c)
        for c in ("台北市", "新北市")
    ]
    df = filter_invalid_stations(merge_cities(dfs))
    g = build_station_graph(df, 30, 3, 12.0, 1.3)
    plan = plan_route(g, df, ORIGIN, DESTINATION, strategy="fewest_swaps")
    print(f"feasible={plan.feasible} swap={plan.swap_count} total={plan.total_minutes:.1f}分")

    center = ((ORIGIN[0] + DESTINATION[0]) / 2, (ORIGIN[1] + DESTINATION[1]) / 2)
    m = render_base_map(df, center=center, zoom_start=12)
    m = draw_route(m, plan, df, ORIGIN, DESTINATION)

    out = Path(__file__).resolve().parent.parent / "route_preview.html"
    m.save(str(out))
    print(f"已輸出: {out}")


if __name__ == "__main__":
    main()
