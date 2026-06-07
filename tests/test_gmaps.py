"""測試 Google Maps 行駛時間（mock requests，離線可跑）。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.gmaps import GMapsError, get_travel_time


def _resp(payload):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json = MagicMock(return_value=payload)
    return r


def _ok(mode_distance_m, duration_s):
    return {
        "status": "OK",
        "rows": [{"elements": [{
            "status": "OK",
            "distance": {"value": mode_distance_m},
            "duration": {"value": duration_s},
        }]}],
    }


def _zero():
    return {"status": "OK", "rows": [{"elements": [{"status": "ZERO_RESULTS"}]}]}


def test_bicycling_used_when_available():
    with patch("core.gmaps.requests.get", return_value=_resp(_ok(3000, 900))):
        tt = get_travel_time(25.0, 121.5, 25.02, 121.5, api_key="k")
    assert tt.mode == "bicycling"
    assert tt.minutes == pytest.approx(15.0)  # 900s / 60
    assert tt.distance_km == pytest.approx(3.0)


def test_falls_back_to_driving_distance():
    # 第一次 bicycling ZERO_RESULTS，第二次 driving 回 6km
    responses = [_resp(_zero()), _resp(_ok(6000, 600))]
    with patch("core.gmaps.requests.get", side_effect=responses):
        tt = get_travel_time(25.0, 121.5, 25.05, 121.5, api_key="k", speed_kmh=12.0)
    assert tt.mode == "driving_distance"
    assert tt.distance_km == pytest.approx(6.0)
    # 6km / 12kmh * 60 = 30 分（用距離換算，不用汽車的 600s）
    assert tt.minutes == pytest.approx(30.0)


def test_both_modes_fail_raises():
    with patch("core.gmaps.requests.get", side_effect=[_resp(_zero()), _resp(_zero())]):
        with pytest.raises(GMapsError):
            get_travel_time(25.0, 121.5, 25.05, 121.5, api_key="k")


def test_missing_api_key_raises():
    with pytest.raises(GMapsError, match="GOOGLE_MAPS_API_KEY"):
        get_travel_time(25.0, 121.5, 25.05, 121.5, api_key="")


def test_top_level_error_status_raises():
    payload = {"status": "REQUEST_DENIED", "error_message": "bad key"}
    with patch("core.gmaps.requests.get", return_value=_resp(payload)):
        with pytest.raises(GMapsError, match="REQUEST_DENIED"):
            get_travel_time(25.0, 121.5, 25.05, 121.5, api_key="k")
