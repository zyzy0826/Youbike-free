"""測試 Streamlit secrets → 環境變數的橋接（無 secrets 時不應崩潰）。"""
from __future__ import annotations

import os

import app


def test_bridge_secrets_no_crash_without_secrets_file(monkeypatch):
    # 測試環境沒有 .streamlit/secrets.toml，存取 st.secrets 會丟例外，
    # _bridge_secrets_to_env 應安靜略過、不影響既有環境變數。
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    app._bridge_secrets_to_env()  # 不應拋出
    # 沒 secrets → 不會憑空冒出金鑰
    assert os.environ.get("GEMINI_API_KEY") in (None, "")


def test_bridge_does_not_override_existing_env(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "preset-model")

    class _FakeSecrets:
        def __getitem__(self, k):
            return {"GEMINI_MODEL": "from-secrets"}[k]

    monkeypatch.setattr(app.st, "secrets", _FakeSecrets())
    app._bridge_secrets_to_env()
    # 既有環境變數優先（setdefault 不覆寫）
    assert os.environ["GEMINI_MODEL"] == "preset-model"


def test_bridge_sets_value_from_secrets(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    class _FakeSecrets:
        def __getitem__(self, k):
            return {"GOOGLE_MAPS_API_KEY": "gm-key"}[k]  # 其他 key → KeyError

    monkeypatch.setattr(app.st, "secrets", _FakeSecrets())
    try:
        app._bridge_secrets_to_env()
        assert os.environ["GOOGLE_MAPS_API_KEY"] == "gm-key"
    finally:
        os.environ.pop("GOOGLE_MAPS_API_KEY", None)  # 清理，避免污染其他測試
