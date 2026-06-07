"""測試 .env 載入與設定取值。"""
from __future__ import annotations

from pathlib import Path

import pytest

from config import settings


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    p = tmp_path / ".env"
    p.write_text(
        "# 這是註解\n"
        "\n"
        'GEMINI_API_KEY="abc123"\n'
        "GOOGLE_MAPS_API_KEY=gmkey\n"
        "EMPTY_VAL=\n"
        "WITH_EQUALS=a=b=c\n",
        encoding="utf-8",
    )
    return p


def test_load_env_parses_values(env_file, monkeypatch):
    for k in ("GEMINI_API_KEY", "GOOGLE_MAPS_API_KEY", "EMPTY_VAL", "WITH_EQUALS"):
        monkeypatch.delenv(k, raising=False)
    settings.load_env(env_file, override=True)
    import os
    assert os.environ["GEMINI_API_KEY"] == "abc123"  # 去除引號
    assert os.environ["GOOGLE_MAPS_API_KEY"] == "gmkey"
    # 值內含 = 應完整保留
    assert os.environ["WITH_EQUALS"] == "a=b=c"


def test_existing_env_takes_priority_without_override(env_file, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "preset")
    settings.load_env(env_file, override=False)
    import os
    assert os.environ["GEMINI_API_KEY"] == "preset"


def test_get_treats_empty_as_unset(monkeypatch):
    monkeypatch.setenv("SOME_KEY", "")
    settings._loaded = True  # 略過自動載入
    assert settings.get("SOME_KEY", "fallback") == "fallback"


def test_gemini_model_default(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    settings._loaded = True
    assert settings.gemini_model() == "gemini-2.0-flash"


def test_load_env_missing_file_is_noop(tmp_path):
    settings.load_env(tmp_path / "nope.env", override=True)
    assert settings._loaded is True
