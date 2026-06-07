# 部署到 Streamlit Community Cloud

## 前置

- 專案已推到 GitHub（public 或將 Streamlit 帳號授權存取 private repo）
- 主程式：`app.py`
- 相依：`requirements.txt`（已含 streamlit、folium、pandas、numpy…）
- 設定：`.streamlit/config.toml`（主題與伺服器設定，會自動套用）

本專案不需系統套件，因此**沒有** `packages.txt`；相依皆為純 Python wheel。

## 步驟

1. 到 <https://share.streamlit.io> 用 GitHub 登入。
2. **Create app → Deploy a public app from a repo**。
3. 填寫：
   - Repository：`<你的帳號>/Youbike-free`
   - Branch：`main`（或你要部署的分支）
   - Main file path：`app.py`
   - Python version：3.10 以上（建議 3.11）
4. 展開 **Advanced settings → Secrets**，貼上金鑰（TOML 格式）：

   ```toml
   GOOGLE_MAPS_API_KEY = "你的金鑰"
   GEMINI_API_KEY = "你的金鑰"
   GEMINI_MODEL = "gemini-2.5-flash"
   ```

   > 不填也能部署：App 仍可規劃路線，只是時間用直線估算、AI 建議改本地摘要。

5. **Deploy**。首次安裝相依約 1~3 分鐘。

## 金鑰如何被讀取

App 啟動時 `_bridge_secrets_to_env()` 會把 `st.secrets` 的值寫入環境變數，
`config/settings.py` 再從環境變數讀取。因此「Streamlit Secrets」與本機「.env」
兩種方式都能用，程式碼不必改。

## 本機預覽（與雲端一致）

```bash
pip install -r requirements.txt
cp .env.example .env        # 然後填入金鑰（本機用 .env 即可）
streamlit run app.py
```

> 本機只需根目錄的 `.env`；`.streamlit/secrets.toml` 是給雲端用的，本機不必建。
> 若仍想在本機用 secrets 方式測試，可自行建立 `.streamlit/secrets.toml`（已被 gitignore）。

## 注意事項

- 新北市 API 憑證有瑕疵，程式以 `verify_ssl=False` 連線，雲端可正常運作。
- 站點資料與地圖會用到 `@st.cache_data` / `@st.cache_resource`，雲端重啟後
  首次載入較慢屬正常。
- 若部署後改了 Secrets，需在 App 選單按 **Reboot** 才會生效。
