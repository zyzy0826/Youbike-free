"""Streamlit 主程式：YouBike 最省錢騎乘攻略。

執行方式:
    streamlit run app.py
"""
from __future__ import annotations

import time

import networkx as nx
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from config import (
    DEFAULT_CYCLING_SPEED_KMH,
    ROUTE_DETOUR_FACTOR,
    SAFETY_MARGIN_MINUTES,
    active_cities,
    free_minutes_by_city,
)
from config import settings
from core.geocoder import GeocodeError, geocode_address
from core.gmaps import GMapsError, get_travel_time
from core.graph_builder import build_station_graph
from core.route_optimizer import (
    SAME_STATION_COOLDOWN_MIN,
    RoutePlan,
    plan_route,
)
from data.fetcher import FetchError, fetch_city_stations
from data.preprocessor import (
    filter_invalid_stations,
    merge_cities,
    normalize_stations,
)
from visualization.map_renderer import draw_route, render_base_map


# 目前聚焦北北桃生活圈（其餘縣市暫不在主流程支援）。
SUPPORTED_CITIES = active_cities()


# ---------- 資料載入（含 Streamlit 快取） ----------

@st.cache_data(ttl=86400, show_spinner=False)
def geocode_cached(address: str) -> tuple[float, float]:
    """以地址查經緯度，結果快取一天（減少 Nominatim 請求）。"""
    return geocode_address(address)


@st.cache_data(ttl=3600, show_spinner=False)
def gmaps_travel_cached(
    o_lat: float, o_lon: float, d_lat: float, d_lon: float
) -> tuple[float, float, str]:
    """以 Google Maps 取單段騎乘時間，結果快取一小時。回傳 (分鐘, 公里, 模式)。"""
    tt = get_travel_time(o_lat, o_lon, d_lat, d_lon, settings.google_maps_api_key())
    return tt.minutes, tt.distance_km, tt.mode


@st.cache_data(ttl=300, show_spinner="抓取 YouBike 站點資料中…")
def load_stations(cities: tuple[str, ...]) -> pd.DataFrame:
    dfs = []
    failures = []
    for city in cities:
        try:
            raw = fetch_city_stations(city)
            dfs.append(normalize_stations(raw, city))
        except (FetchError, ValueError) as e:
            failures.append((city, str(e)))
    if failures:
        for c, msg in failures:
            st.warning(f"擷取 {c} 失敗：{msg}")
    if not dfs:
        return pd.DataFrame()
    return filter_invalid_stations(merge_cities(dfs))


@st.cache_resource(show_spinner="建構站點圖中…")
def get_graph(
    cities: tuple[str, ...],
    has_tpass: bool,
    safety_margin: int,
    allow_cross_circle: bool,
    require_availability: bool,
) -> tuple[nx.DiGraph, pd.DataFrame]:
    df = load_stations(cities)
    if df.empty:
        return nx.DiGraph(), df
    fmbc = free_minutes_by_city(list(cities), has_tpass)
    g = build_station_graph(
        df,
        free_minutes=max(fmbc.values()) if fmbc else 30,
        safety_margin=safety_margin,
        speed_kmh=DEFAULT_CYCLING_SPEED_KMH,
        detour_factor=ROUTE_DETOUR_FACTOR,
        allow_cross_circle=allow_cross_circle,
        require_availability=require_availability,
        free_minutes_by_city=fmbc,
    )
    return g, df


# ---------- UI ----------

def render_sidebar() -> dict:
    st.sidebar.header("路線設定")
    cities = st.sidebar.multiselect(
        "資料來源城市（北北桃）", SUPPORTED_CITIES, default=SUPPORTED_CITIES,
        help="目前聚焦北北桃生活圈，可規劃台北↔新北↔桃園的跨縣市路線",
    )
    has_tpass = st.sidebar.toggle(
        "持有 TPASS 月票",
        value=False,
        help="影響免費騎乘上限：桃園一般 30 分、TPASS 60 分；台北/新北皆 30 分",
    )
    if cities:
        fmbc = free_minutes_by_city(list(cities), has_tpass)
        st.sidebar.caption(
            "各市免費上限：" + "、".join(f"{c} {m} 分" for c, m in fmbc.items())
        )
    safety_margin = st.sidebar.number_input(
        "安全餘裕（分鐘）", min_value=0, max_value=10,
        value=SAFETY_MARGIN_MINUTES,
        help="建議提前幾分鐘還車，避免估算誤差超時",
    )
    strategy = st.sidebar.radio(
        "路線策略",
        options=["fewest_swaps", "shortest_time"],
        format_func=lambda s: "最少換車" if s == "fewest_swaps" else "最短總時間",
    )
    allow_cross_circle = st.sidebar.checkbox(
        "允許跨生活圈（會收 600~1135 元調度費）",
        value=False,
    )
    require_availability = st.sidebar.checkbox(
        "只走有車可借 / 有位可還的站",
        value=True,
        help="依即時車輛數過濾：借不到車的站不當起點、還不了車的站不當終點",
    )

    st.sidebar.divider()
    st.sidebar.subheader("起點 / 終點")

    use_address = st.sidebar.toggle(
        "用地址 / 地標查詢", value=False,
        help="輸入地址或地標（如「台北車站」），自動轉成經緯度（需網路）",
    )

    o_addr = d_addr = ""
    if use_address:
        o_addr = st.sidebar.text_input("起點地址", value="台北車站")
        d_addr = st.sidebar.text_input("終點地址", value="淡水捷運站")
        o_lat, o_lon = 25.0478, 121.5170
        d_lat, d_lon = 25.1677, 121.4456
    else:
        st.sidebar.caption("直接輸入經緯度")
        o_lat = st.sidebar.number_input(
            "起點緯度", value=25.0478, format="%.5f", key="o_lat"
        )
        o_lon = st.sidebar.number_input(
            "起點經度", value=121.5170, format="%.5f", key="o_lon"
        )
        d_lat = st.sidebar.number_input(
            "終點緯度", value=25.1677, format="%.5f", key="d_lat"
        )
        d_lon = st.sidebar.number_input(
            "終點經度", value=121.4456, format="%.5f", key="d_lon"
        )
    submit = st.sidebar.button("規劃路線", type="primary", use_container_width=True)

    return {
        "cities": tuple(cities),
        "has_tpass": has_tpass,
        "safety_margin": int(safety_margin),
        "strategy": strategy,
        "allow_cross_circle": allow_cross_circle,
        "require_availability": require_availability,
        "use_address": use_address,
        "origin_address": o_addr,
        "destination_address": d_addr,
        "origin": (o_lat, o_lon),
        "destination": (d_lat, d_lon),
        "submit": submit,
    }


def render_summary(plan: RoutePlan) -> None:
    if not plan.feasible:
        st.error(f"❌ {plan.message}")
        return
    if plan.message:
        st.warning(plan.message)

    cols = st.columns(4)
    cols[0].metric("換車次數", plan.swap_count)
    cols[1].metric("總騎乘時間", f"{plan.total_minutes:.1f} 分")
    cols[2].metric("步行（起 / 終）",
                   f"{plan.walk_to_start_min:.1f} / {plan.walk_from_end_min:.1f} 分")
    total = plan.total_minutes + plan.walk_to_start_min + plan.walk_from_end_min
    cols[3].metric("總時間（含步行）", f"{total:.1f} 分")


def render_itinerary(
    plan: RoutePlan,
    fmbc: dict[str, int],
    id_to_city: dict[str, str],
) -> None:
    if not plan.feasible or not plan.segments:
        return
    rows = []
    for i, seg in enumerate(plan.segments, 1):
        # 免費規則以借車地（起站縣市）為準，逐段可能不同（如桃園 vs 台北）
        city = id_to_city.get(seg.from_station_id, "")
        limit = fmbc.get(city, max(fmbc.values()) if fmbc else 30)
        margin = limit - seg.minutes
        rows.append({
            "段": i,
            "起站": seg.from_name,
            "終站": seg.to_name,
            "起站縣市": city,
            "免費上限 (分)": limit,
            "騎乘時間 (分)": round(seg.minutes, 1),
            "距離 (km)": round(seg.distance_km, 2),
            "免費餘裕 (分)": round(margin, 1),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, use_container_width=True)


def render_cooldown_advice(plan: RoutePlan) -> None:
    """顯示同站續借冷卻提醒與鄰近改借建議。"""
    if not plan.swap_advice:
        return
    lo, hi = SAME_STATION_COOLDOWN_MIN
    st.subheader("🔁 換車點冷卻提醒")
    st.caption(
        f"在換車點還車後，於同一站再借同型車可能需等 {lo}~{hi} 分鐘冷卻。"
        "建議改到鄰近站借車，或改用雙卡輪替。"
    )
    for i, adv in enumerate(plan.swap_advice, 1):
        with st.expander(f"換車點 #{i}：{adv.station_name}", expanded=False):
            if not adv.alternatives:
                st.write("附近 300m 內查無其他有車可借的站，建議於原站等候冷卻時間。")
                continue
            alt_rows = [
                {
                    "改借站": name,
                    "步行 (分)": round(walk_min, 1),
                    "距離 (km)": round(dist, 2),
                    "可借車": bikes,
                }
                for name, walk_min, dist, bikes in adv.alternatives
            ]
            st.dataframe(
                pd.DataFrame(alt_rows), hide_index=True, use_container_width=True
            )


def render_google_refinement(
    plan: RoutePlan, stations: pd.DataFrame, fmbc: dict[str, int]
) -> None:
    """用 Google Maps 校正每段騎乘時間，並與直線估算比較、標示是否超出免費上限。"""
    if not settings.google_maps_api_key():
        st.info("（選用）在 .env 設定 GOOGLE_MAPS_API_KEY 後，可用 Google 校正真實道路時間。")
        return
    if not st.button("🛰️ 用 Google Maps 校正騎乘時間"):
        return

    coords = stations.set_index("station_id")[["lat", "lon", "city"]].to_dict("index")
    rows = []
    any_over = False
    with st.spinner("查詢 Google Maps 中…"):
        for i, seg in enumerate(plan.segments, 1):
            a = coords[seg.from_station_id]
            b = coords[seg.to_station_id]
            limit = fmbc.get(a["city"], max(fmbc.values()) if fmbc else 30)
            try:
                g_min, g_km, mode = gmaps_travel_cached(
                    a["lat"], a["lon"], b["lat"], b["lon"]
                )
                over = g_min > limit
                any_over = any_over or over
                rows.append({
                    "段": i, "起站": seg.from_name, "終站": seg.to_name,
                    "估算 (分)": round(seg.minutes, 1),
                    "Google (分)": round(g_min, 1),
                    "Google 模式": mode,
                    "免費上限 (分)": limit,
                    "超時": "⚠️" if over else "",
                })
            except GMapsError as e:
                rows.append({
                    "段": i, "起站": seg.from_name, "終站": seg.to_name,
                    "估算 (分)": round(seg.minutes, 1),
                    "Google (分)": "—", "Google 模式": f"失敗：{e}",
                    "免費上限 (分)": limit, "超時": "",
                })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    if any_over:
        st.warning("⚠️ 依 Google 校正，部分路段實際時間超過免費上限，該段可能產生費用。")
    else:
        st.success("✅ 依 Google 校正，各路段仍在免費上限內。")


# ---------- 主流程 ----------

def _resolve_addresses(
    origin_address: str, destination_address: str
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """將起終點地址轉成經緯度。任一失敗則顯示錯誤並回傳 None。"""
    try:
        origin = geocode_cached(origin_address)
        destination = geocode_cached(destination_address)
    except GeocodeError as e:
        st.error(f"❌ 地址解析失敗：{e}")
        return None
    st.caption(
        f"📍 起點 {origin_address} → {origin[0]:.5f}, {origin[1]:.5f}；"
        f"終點 {destination_address} → {destination[0]:.5f}, {destination[1]:.5f}"
    )
    return origin, destination


def main() -> None:
    st.set_page_config(page_title="YouBike 最省錢攻略", layout="wide")
    st.title("🚲 YouBike 最省錢騎乘攻略")
    st.caption("自動規劃中途換車路線，全程免費抵達目的地")

    inp = render_sidebar()

    if not inp["cities"]:
        st.info("請從側欄選擇至少一個城市。")
        return

    graph, stations = get_graph(
        inp["cities"],
        inp["has_tpass"],
        inp["safety_margin"],
        inp["allow_cross_circle"],
        inp["require_availability"],
    )
    if stations.empty:
        st.error("無法載入任何站點資料。")
        return

    st.caption(f"已載入 {len(stations)} 站、{graph.number_of_edges()} 條邊")

    origin = inp["origin"]
    destination = inp["destination"]
    if inp["use_address"]:
        resolved = _resolve_addresses(
            inp["origin_address"], inp["destination_address"]
        )
        if resolved is None:
            return
        origin, destination = resolved

    plan: RoutePlan | None = None
    if inp["submit"]:
        t0 = time.time()
        plan = plan_route(
            graph, stations,
            origin, destination,
            strategy=inp["strategy"],
        )
        st.caption(f"規劃耗時 {(time.time() - t0) * 1000:.0f} ms")

    # 地圖
    center = (
        (origin[0] + destination[0]) / 2,
        (origin[1] + destination[1]) / 2,
    )
    m = render_base_map(stations, center=center, zoom_start=12)
    if plan is not None:
        m = draw_route(m, plan, stations, origin, destination)

    map_col, info_col = st.columns([2, 1])
    with map_col:
        st_folium(m, width=None, height=620, returned_objects=[])
    with info_col:
        if plan is None:
            st.info("設定好起終點後，按側欄的「規劃路線」開始。")
        else:
            render_summary(plan)

    if plan is not None and plan.feasible:
        st.subheader("詳細行程")
        fmbc = free_minutes_by_city(list(inp["cities"]), inp["has_tpass"])
        id_to_city = dict(zip(stations["station_id"], stations["city"]))
        render_itinerary(plan, fmbc, id_to_city)
        render_google_refinement(plan, stations, fmbc)
        render_cooldown_advice(plan)


if __name__ == "__main__":
    main()
