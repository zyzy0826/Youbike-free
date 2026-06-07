"""測試 AI 回饋：事實收集、模板回退、Gemini 潤飾（mock）。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.feedback import (
    GeminiError,
    collect_facts,
    facts_to_text,
    generate_feedback,
    polish_with_gemini,
)
from core.route_optimizer import RoutePlan, RouteSegment, SwapAdvice


def _plan():
    segs = [
        RouteSegment("台北市_1", "台北市_2", "A站", "B站", 25.0, 5.0),
        RouteSegment("桃園市_3", "桃園市_4", "C站", "D站", 40.0, 8.0),
    ]
    return RoutePlan(
        segments=segs, total_minutes=65.0, swap_count=1,
        walk_to_start_min=3.0, walk_from_end_min=4.0,
        strategy="fewest_swaps", feasible=True, message="",
        swap_advice=[SwapAdvice("台北市_2", "B站", [("鄰站", 2.5, 0.2, 6)])],
    )


_FMBC = {"台北市": 30, "桃園市": 60}
_ID2CITY = {"台北市_1": "台北市", "台北市_2": "台北市",
            "桃園市_3": "桃園市", "桃園市_4": "桃園市"}


def test_collect_facts_computes_margins_and_tight():
    facts = collect_facts(_plan(), _FMBC, _ID2CITY, has_tpass=True)
    assert facts.swap_count == 1
    # 第1段 台北 30 - 25 = 5 餘裕；第2段 桃園 60 - 40 = 20 餘裕
    assert facts.segments[0]["margin"] == 5.0
    assert facts.segments[1]["margin"] == 20.0
    # tight_margin 預設 <5：第1段 5.0 不算 tight（嚴格小於）
    assert facts.tight_segments == []
    # 冷卻換車點被收錄
    assert facts.cooldown_swaps[0]["station"] == "B站"
    assert facts.cooldown_swaps[0]["has_alternative"] is True


def test_collect_facts_flags_tight_segment():
    p = _plan()
    p.segments[0].minutes = 27.0  # 台北 30 - 27 = 3 < 5 → tight
    facts = collect_facts(p, _FMBC, _ID2CITY)
    assert len(facts.tight_segments) == 1
    assert facts.tight_segments[0]["index"] == 1


def test_facts_to_text_contains_key_numbers():
    text = facts_to_text(collect_facts(_plan(), _FMBC, _ID2CITY))
    assert "換車次數：1 次" in text
    assert "A站→B站" in text
    assert "鄰站" in text  # 冷卻改借建議


def test_collect_facts_includes_realtime_availability():
    # 起點站 0 車、終點站 0 位 → 應產生車況警示
    avail = {
        "台北市_1": (0, 5),   # 起點借車站：0 車可借
        "台北市_2": (3, 2),   # 換車點
        "桃園市_4": (4, 0),   # 終點還車站：0 位可還
    }
    facts = collect_facts(_plan(), _FMBC, _ID2CITY, availability=avail)
    assert facts.start_bikes == 0
    assert facts.end_docks == 0
    assert len(facts.availability_warnings) == 2
    # 換車點即時車況併入冷卻事實
    assert facts.cooldown_swaps[0]["current_docks"] == 2
    assert facts.cooldown_swaps[0]["current_bikes"] == 3
    text = facts_to_text(facts)
    assert "目前無車可借" in text
    assert "目前無空位可還" in text


def test_collect_facts_without_availability_has_no_warnings():
    facts = collect_facts(_plan(), _FMBC, _ID2CITY)
    assert facts.start_bikes is None
    assert facts.end_docks is None
    assert facts.availability_warnings == []


def test_collect_facts_handles_cooldown_walk_wait_segments():
    # node-split 模式：ride → walk → ride 的混合段
    segs = [
        RouteSegment("台北市_1", "台北市_2", "A站", "B站", 25.0, 5.0, mode="ride"),
        RouteSegment("台北市_2", "台北市_5", "B站", "B鄰站", 2.5, 0.2, mode="walk"),
        RouteSegment("台北市_5", "台北市_4", "B鄰站", "D站", 20.0, 4.0, mode="ride"),
    ]
    plan = RoutePlan(
        segments=segs, total_minutes=45.0, swap_count=1,
        walk_to_start_min=3.0, walk_from_end_min=4.0,
        strategy="shortest_time", feasible=True, transfer_minutes=2.5,
    )
    fmbc = {"台北市": 30}
    id2city = {"台北市_1": "台北市", "台北市_2": "台北市",
               "台北市_5": "台北市", "台北市_4": "台北市"}
    facts = collect_facts(plan, fmbc, id2city)
    # 兩段 ride 各有 margin，walk 段不算 free_limit
    ride_infos = [s for s in facts.segments if s.get("mode") == "ride"]
    walk_infos = [s for s in facts.segments if s.get("mode") == "walk"]
    assert len(ride_infos) == 2 and len(walk_infos) == 1
    text = facts_to_text(facts)
    assert "步行換車" in text  # 轉乘段被描述


def test_collect_facts_with_google_times_flags_over_limit():
    # 第1段台北上限30：Google 校正 35 分 → 超時；第2段桃園上限60：Google 50 分 → 未超
    gtimes = {1: (35.0, "driving_distance"), 2: (50.0, "bicycling")}
    facts = collect_facts(_plan(), _FMBC, _ID2CITY, google_times=gtimes)
    assert facts.segments[0]["google_minutes"] == 35.0
    assert facts.segments[0]["google_over"] is True
    assert facts.segments[1]["google_over"] is False
    assert len(facts.google_over_segments) == 1
    text = facts_to_text(facts)
    assert "Google 校正 35.0 分" in text
    assert "超過免費上限" in text


def test_generate_feedback_without_key_uses_template():
    text, source, error = generate_feedback(
        collect_facts(_plan(), _FMBC, _ID2CITY), api_key=None
    )
    assert source == "template"
    assert error == ""
    assert "路線：" in text


def test_polish_with_gemini_parses_response():
    payload = {
        "candidates": [{"content": {"parts": [{"text": "  親切建議內容  "}]}}]
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value=payload)
    with patch("core.feedback.requests.post", return_value=resp):
        out = polish_with_gemini("facts", api_key="k")
    assert out == "親切建議內容"


def test_polish_http_error_surfaces_google_message():
    # 模擬 Google 回傳 403 + error.message（如 API 未啟用 / 金鑰無效）
    resp = MagicMock()
    resp.status_code = 403
    resp.json = MagicMock(return_value={
        "error": {"message": "Generative Language API has not been used in project 123..."}
    })
    with patch("core.feedback.requests.post", return_value=resp):
        with pytest.raises(GeminiError, match="has not been used"):
            polish_with_gemini("facts", api_key="k")


def test_generate_feedback_falls_back_on_gemini_error():
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value={"promptFeedback": {"blockReason": "SAFETY"}})
    with patch("core.feedback.requests.post", return_value=resp):
        text, source, error = generate_feedback(
            collect_facts(_plan(), _FMBC, _ID2CITY), api_key="k"
        )
    # Gemini 回傳無有效內容 → 回退模板，且帶回錯誤原因
    assert source == "template"
    assert error  # 非空，含失敗原因
    assert "路線：" in text


def test_polish_missing_key_raises():
    with pytest.raises(GeminiError, match="GEMINI_API_KEY"):
        polish_with_gemini("facts", api_key="")
