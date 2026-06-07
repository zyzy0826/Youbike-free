"""測試 API 擷取與快取機制。"""
import pytest


def test_fetch_taipei_stations_returns_list():
    """台北 API 應回傳非空 station list。"""
    pytest.skip("Phase 1 待實作")


def test_cache_hit_within_ttl():
    """快取在 TTL 內應直接讀檔，不打 API。"""
    pytest.skip("Phase 1 待實作")


def test_cache_expired_refetches():
    """快取過期應重新呼叫 API。"""
    pytest.skip("Phase 1 待實作")
