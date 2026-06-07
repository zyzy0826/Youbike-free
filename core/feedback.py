"""AI 行程回饋：客觀事實收集 → 便宜 LLM（Gemini）語氣潤飾。

設計原則：
    - 「事實」由程式以路線規劃結果客觀計算（collect_facts），不經 LLM，杜絕捏造。
    - LLM 只負責「語氣潤飾」：把事實重寫成親切好讀的繁體中文，明確要求不得新增或
      竄改任何數字 / 站名。
    - 無金鑰或呼叫失敗時，回退到本地模板摘要（facts_to_text），功能不中斷。

需要網路與 GEMINI_API_KEY 才會走 LLM；否則自動回退模板。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import requests

from core.route_optimizer import RoutePlan

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_REQUEST_TIMEOUT = 20


class GeminiError(RuntimeError):
    """Gemini 呼叫失敗。"""


@dataclass
class RouteFacts:
    """一趟路線的客觀事實（供潤飾用，全部由程式計算）。"""
    origin_label: str
    destination_label: str
    has_tpass: bool
    swap_count: int
    total_ride_min: float
    walk_to_start_min: float
    walk_from_end_min: float
    total_with_walk_min: float
    segments: list[dict] = field(default_factory=list)
    tight_segments: list[dict] = field(default_factory=list)  # 免費餘裕偏少的路段
    google_over_segments: list[dict] = field(default_factory=list)  # 依 Google 超時的路段
    cooldown_swaps: list[dict] = field(default_factory=list)
    warning: str = ""
    # 即時車況（若有提供 availability）
    start_station: str = ""
    start_bikes: int | None = None
    end_station: str = ""
    end_docks: int | None = None
    availability_warnings: list[str] = field(default_factory=list)


def collect_facts(
    plan: RoutePlan,
    fmbc: dict[str, int],
    id_to_city: dict[str, str],
    origin_label: str = "起點",
    destination_label: str = "終點",
    has_tpass: bool = False,
    tight_margin_min: float = 5.0,
    availability: dict[str, tuple[int, int]] | None = None,
    google_times: dict[int, tuple[float, str]] | None = None,
) -> RouteFacts:
    """從 RoutePlan 計算客觀事實。免費規則以各段起站縣市為準。

    Args:
        availability: {station_id: (可借車輛數, 可還空位數)} 即時車況；提供時會把
            起點借車站、終點還車站、換車點的即時車況納入事實並產生缺車/滿位警示。
        google_times: {段次(1起): (Google 校正分鐘, 模式)}；提供時逐段併入 Google
            校正時間，並對「依 Google 超過免費上限」的路段產生警示。
    """
    default_limit = max(fmbc.values()) if fmbc else 30
    avail = availability or {}
    gtimes = google_times or {}
    segments: list[dict] = []
    tight: list[dict] = []
    google_over: list[dict] = []
    transfer_count = 0
    for i, seg in enumerate(plan.segments, 1):
        mode = getattr(seg, "mode", "ride")
        if mode != "ride":
            # node-split 冷卻模型的步行換車 / 等冷卻段
            transfer_count += 1
            segments.append({
                "index": i, "mode": mode,
                "from": seg.from_name, "to": seg.to_name,
                "minutes": round(seg.minutes, 1),
            })
            continue
        city = id_to_city.get(seg.from_station_id, "")
        limit = fmbc.get(city, default_limit)
        margin = limit - seg.minutes
        info = {
            "index": i,
            "mode": "ride",
            "from": seg.from_name,
            "to": seg.to_name,
            "city": city,
            "minutes": round(seg.minutes, 1),
            "free_limit": limit,
            "margin": round(margin, 1),
        }
        if i in gtimes:
            g_min, g_mode = gtimes[i]
            info["google_minutes"] = round(g_min, 1)
            info["google_mode"] = g_mode
            info["google_over"] = g_min > limit
            if g_min > limit:
                google_over.append(info)
        segments.append(info)
        if margin < tight_margin_min:
            tight.append(info)

    cooldown = []
    for adv in plan.swap_advice:
        bikes, docks = avail.get(adv.station_id, (None, None))
        cooldown.append({
            "station": adv.station_name,
            "has_alternative": bool(adv.alternatives),
            "nearest_alt": adv.alternatives[0][0] if adv.alternatives else None,
            "nearest_alt_walk_min": round(adv.alternatives[0][1], 1) if adv.alternatives else None,
            "current_bikes": bikes,
            "current_docks": docks,
        })

    # 即時車況：起點借車站需有車、終點還車站需有位
    start_station = end_station = ""
    start_bikes = end_docks = None
    avail_warnings: list[str] = []
    if plan.segments:
        start_id = plan.segments[0].from_station_id
        start_station = plan.segments[0].from_name
        end_id = plan.segments[-1].to_station_id
        end_station = plan.segments[-1].to_name
        if start_id in avail:
            start_bikes = avail[start_id][0]
            if start_bikes == 0:
                avail_warnings.append(
                    f"起點借車站「{start_station}」目前無車可借，出發前請確認或改鄰站借車。"
                )
        if end_id in avail:
            end_docks = avail[end_id][1]
            if end_docks == 0:
                avail_warnings.append(
                    f"終點還車站「{end_station}」目前無空位可還，抵達前請確認或改鄰站還車。"
                )

    total_with_walk = plan.total_minutes + plan.walk_to_start_min + plan.walk_from_end_min
    return RouteFacts(
        origin_label=origin_label,
        destination_label=destination_label,
        has_tpass=has_tpass,
        swap_count=plan.swap_count,
        total_ride_min=round(plan.total_minutes, 1),
        walk_to_start_min=round(plan.walk_to_start_min, 1),
        walk_from_end_min=round(plan.walk_from_end_min, 1),
        total_with_walk_min=round(total_with_walk, 1),
        segments=segments,
        tight_segments=tight,
        google_over_segments=google_over,
        cooldown_swaps=cooldown,
        warning=plan.message,
        start_station=start_station,
        start_bikes=start_bikes,
        end_station=end_station,
        end_docks=end_docks,
        availability_warnings=avail_warnings,
    )


def facts_to_text(facts: RouteFacts) -> str:
    """把事實轉成條列文字（同時作為無金鑰時的本地回饋與 LLM 的輸入）。"""
    lines = [
        f"路線：{facts.origin_label} → {facts.destination_label}",
        f"持有 TPASS 月票：{'是' if facts.has_tpass else '否'}",
        f"換車次數：{facts.swap_count} 次",
        f"總騎乘時間：{facts.total_ride_min} 分鐘",
        f"步行（起點→借車站 / 還車站→終點）：{facts.walk_to_start_min} / {facts.walk_from_end_min} 分鐘",
        f"含步行總時間：{facts.total_with_walk_min} 分鐘",
        "各段：",
    ]
    transfer_label = {"walk": "步行換車", "wait": "原站等冷卻"}
    for s in facts.segments:
        if s.get("mode", "ride") != "ride":
            label = transfer_label.get(s["mode"], s["mode"])
            lines.append(
                f"  第{s['index']}段（{label}）{s['from']}→{s['to']}：{s['minutes']} 分"
            )
            continue
        g = ""
        if "google_minutes" in s:
            g = f"，Google 校正 {s['google_minutes']} 分（{s['google_mode']}）"
        lines.append(
            f"  第{s['index']}段 {s['from']}→{s['to']}（{s['city']}）"
            f"：騎乘 {s['minutes']} 分，免費上限 {s['free_limit']} 分，餘裕 {s['margin']} 分{g}"
        )
    if facts.google_over_segments:
        names = "、".join(f"第{s['index']}段" for s in facts.google_over_segments)
        lines.append(
            f"依 Google 校正，{names}的實際時間已超過免費上限，該段可能產生費用，"
            "建議改走較短路段或加快。"
        )
    if facts.start_bikes is not None:
        lines.append(f"起點借車站「{facts.start_station}」目前可借車輛：{facts.start_bikes} 台")
    if facts.end_docks is not None:
        lines.append(f"終點還車站「{facts.end_station}」目前可還空位：{facts.end_docks} 位")
    if facts.tight_segments:
        names = "、".join(f"第{s['index']}段" for s in facts.tight_segments)
        lines.append(f"免費餘裕偏少（<5 分）的路段：{names}，建議加快或提前還車。")
    for w in facts.availability_warnings:
        lines.append(f"即時車況提醒：{w}")
    if facts.cooldown_swaps:
        for c in facts.cooldown_swaps:
            cond = ""
            if c.get("current_docks") is not None:
                cond = f"（該站目前可還 {c['current_docks']} 位、可借 {c['current_bikes']} 台）"
            if c["has_alternative"]:
                lines.append(
                    f"換車點 {c['station']}{cond} 有同站續借冷卻，建議改到步行約 "
                    f"{c['nearest_alt_walk_min']} 分的「{c['nearest_alt']}」借車。"
                )
            else:
                lines.append(
                    f"換車點 {c['station']}{cond} 附近無其他可借站，需於原站等候冷卻或改用雙卡。"
                )
    if facts.warning:
        lines.append(f"注意：{facts.warning}")
    return "\n".join(lines)


def _build_prompt(facts_text: str) -> str:
    return (
        "你是親切的 YouBike 路線小幫手。以下是一趟『全程免費』騎乘規劃的客觀事實，"
        "請用口語、溫暖的繁體中文，幫使用者整理成一段好讀的行程建議（約 120~200 字）。\n"
        "嚴格要求：只能根據提供的事實，不可新增、竄改或臆測任何數字、站名或結論；"
        "請特別提醒免費餘裕偏少的路段、換車點的冷卻與改借建議。不要使用條列符號，"
        "用流暢的段落即可。\n\n"
        f"【客觀事實】\n{facts_text}"
    )


def polish_with_gemini(
    facts_text: str, api_key: str, model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
) -> str:
    """呼叫 Gemini 將事實潤飾為親切的繁體中文建議。

    Raises:
        GeminiError: 未設金鑰、請求失敗或回傳格式不符。
    """
    if not api_key:
        raise GeminiError("未設定 GEMINI_API_KEY")

    url = _GEMINI_URL.format(model=model)
    payload = {
        "contents": [{"parts": [{"text": _build_prompt(facts_text)}]}],
        "generationConfig": {"temperature": temperature},
    }
    try:
        resp = requests.post(
            url, params={"key": api_key}, json=payload, timeout=_REQUEST_TIMEOUT
        )
    except requests.RequestException as e:
        raise GeminiError(f"Gemini 連線失敗：{e}") from e

    # 非 200 時讀取 Google 回傳的 error.message（如金鑰無效、模型不存在、API 未啟用），
    # 直接呈現確切原因，而非只給 HTTP 狀態碼。
    if resp.status_code != 200:
        detail = ""
        try:
            detail = resp.json().get("error", {}).get("message", "")
        except ValueError:
            detail = (resp.text or "")[:300]
        raise GeminiError(f"HTTP {resp.status_code}：{detail}".strip())

    try:
        data = resp.json()
    except ValueError as e:
        raise GeminiError(f"Gemini 回應非 JSON：{e}") from e

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        # 可能被安全機制擋下或回傳結構異常
        reason = data.get("promptFeedback", {}).get("blockReason", "")
        raise GeminiError(f"Gemini 回傳無有效內容 {reason}".strip()) from e


def generate_feedback(
    facts: RouteFacts, api_key: str | None, model: str = "gemini-2.5-flash",
) -> tuple[str, str, str]:
    """產生回饋。回傳 (文字, 來源, 錯誤訊息)。來源為 'gemini' 或 'template'。

    有金鑰且呼叫成功 → 使用 Gemini 潤飾；失敗則回退本地模板摘要並附上錯誤原因，
    讓 UI 能顯示「為何 Gemini 沒跑成功」（例如模型名稱錯誤、金鑰無效）。
    """
    facts_text = facts_to_text(facts)
    if api_key:
        try:
            return polish_with_gemini(facts_text, api_key, model), "gemini", ""
        except GeminiError as e:
            return facts_text, "template", str(e)
    return facts_text, "template", ""
