"""測試地理編碼模組（以 mock 取代真實 Nominatim 請求，離線可跑）。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core import geocoder
from core.geocoder import GeocodeError, geocode_address


@pytest.fixture(autouse=True)
def _reset_state():
    """每個測試前清空模組級快取與節流計時，避免互相污染。"""
    geocoder._cache.clear()
    geocoder._last_request_ts = 0.0
    geocoder._geocoder = None
    yield


def _fake_location(lat, lon, raw=None, address="某地"):
    loc = MagicMock()
    loc.latitude = lat
    loc.longitude = lon
    loc.address = address
    loc.raw = raw if raw is not None else {}
    return loc


def test_geocode_success():
    fake = MagicMock()
    # geocode 以 exactly_one=False 取多筆，回傳 list
    fake.geocode.return_value = [_fake_location(25.0478, 121.5170)]
    with patch.object(geocoder, "_get_geocoder", return_value=fake):
        lat, lon = geocode_address("台北車站")
    assert lat == pytest.approx(25.0478)
    assert lon == pytest.approx(121.5170)


def test_geocode_verbose_returns_matched_name():
    from core.geocoder import geocode_address_verbose

    loc = _fake_location(25.0, 121.5, address="淡水捷運站, 新北市, 台灣")
    fake = MagicMock()
    fake.geocode.return_value = [loc]
    with patch.object(geocoder, "_get_geocoder", return_value=fake):
        lat, lon, name = geocode_address_verbose("淡水捷運站")
    assert (lat, lon) == (25.0, 121.5)
    assert "淡水" in name


def test_geocode_prefers_station_node_over_route_line():
    # 模擬「淡水捷運站」回傳：①整條淡水信義線(route, 大安區) ②淡水站(railway station node)
    line = _fake_location(
        25.0266, 121.5436,  # 大安區一帶
        raw={"class": "route", "type": "subway", "osm_type": "relation",
             "importance": 0.6},
        address="淡水信義線, 大安區, 台北市",
    )
    station = _fake_location(
        25.1677, 121.4456,  # 淡水
        raw={"class": "railway", "type": "station", "osm_type": "node",
             "importance": 0.4},
        address="淡水站, 淡水區, 新北市",
    )
    fake = MagicMock()
    fake.geocode.return_value = [line, station]  # 路線排在前面（importance 較高）
    from core.geocoder import geocode_address_verbose
    with patch.object(geocoder, "_get_geocoder", return_value=fake):
        lat, lon, name = geocode_address_verbose("淡水捷運站")
    # 應挑到「淡水站」而非整條線
    assert (lat, lon) == pytest.approx((25.1677, 121.4456))
    assert "淡水站" in name


def test_geocode_empty_address_raises():
    with pytest.raises(GeocodeError):
        geocode_address("   ")


def test_geocode_not_found_raises():
    fake = MagicMock()
    fake.geocode.return_value = None
    with patch.object(geocoder, "_get_geocoder", return_value=fake):
        with pytest.raises(GeocodeError, match="查無此地址"):
            geocode_address("不存在的地方xyzzy")


def test_geocode_uses_cache_and_calls_service_once():
    fake = MagicMock()
    fake.geocode.return_value = [_fake_location(25.0, 121.5)]
    with patch.object(geocoder, "_get_geocoder", return_value=fake):
        first = geocode_address("台北車站")
        second = geocode_address("台北車站")
    assert first == second
    # 第二次應命中快取，不再呼叫服務
    assert fake.geocode.call_count == 1


def test_geocode_service_error_wrapped():
    from geopy.exc import GeocoderTimedOut

    fake = MagicMock()
    fake.geocode.side_effect = GeocoderTimedOut("timeout")
    with patch.object(geocoder, "_get_geocoder", return_value=fake):
        with pytest.raises(GeocodeError, match="服務錯誤"):
            geocode_address("台北車站")
