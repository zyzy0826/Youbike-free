<!-- 徽章來源參考寫法：https://github.com/Envoy-VC/awesome-badges#github-stats -->

![](https://img.shields.io/github/stars/zyzy0826/Youbike-free.svg)｜![](https://img.shields.io/github/forks/zyzy0826/Youbike-free.svg)｜![](https://img.shields.io/github/issues-pr/zyzy0826/Youbike-free.svg)｜![](https://img.shields.io/github/issues/zyzy0826/Youbike-free.svg)

# YouBike 最省錢騎乘攻略

<!-- 請換成你的專案封面圖／實際畫面截圖 -->
![專案封面圖](https://fakeimg.pl/800x400/?text=YouBike%20Free%20Route&font=noto)

> 在地圖上選定出發點與終點，系統自動規劃**全程免費**的 YouBike 騎乘路線。核心策略：利用各縣市的免費騎乘時間（台北／新北 30 分鐘、桃園一般 30 分鐘、持 TPASS 月票 60 分鐘），透過中途換車，讓每一段騎乘時間都控制在免費上限內。

- [線上觀看連結](https://share.streamlit.io/)（部署後請替換成你的 `https://<名稱>.streamlit.app`，步驟見 [DEPLOY.md](DEPLOY.md)）

## 功能

> 本工具無需註冊／登入，開啟即用。Google Maps 校正與 AI 建議為選用功能，未設定金鑰時仍可正常規劃路線。

- [x] 自動規劃全程免費的 YouBike 換車路線（聚焦北北桃生活圈）
- [x] 兩種規劃策略：最少換車（BFS）／最短總時間（Dijkstra）
- [x] 兩 case 免費時長：依「起站縣市 + 是否持 TPASS」逐段判斷免費上限
- [x] 即時車況過濾：避開無車可借／無位可還的站
- [x] 同站續借冷卻提醒，並提供 node-split「步行換鄰站借車」模型
- [x] 地址／地標查詢（如「淡水捷運站」自動轉經緯度）
- [x] Folium 互動地圖：站點車況顏色、換車點、每段時間
- [x] Google Maps 道路時間校正，並自動避開實測超時的路段
- [x] AI 行程建議：客觀事實收集 → Gemini 語氣潤飾（無金鑰自動回退本地摘要）
- [x] 生活圈邊界保護：避免跨生活圈被收 600~1135 元調度費

## 畫面

> 可提供 1~3 張圖片，讓觀看者透過 README 了解整體畫面（請替換成實際截圖）。

![主畫面與路線地圖](https://fakeimg.pl/640x360/?text=Map%20%26%20Route&font=noto)
![詳細行程與免費餘裕](https://fakeimg.pl/640x360/?text=Itinerary&font=noto)
![AI 行程建議](https://fakeimg.pl/640x360/?text=AI%20Feedback&font=noto)

## 安裝

> 請務必依據你的環境調整內容。

以下將引導你如何安裝此專案到你的電腦上。Python 版本建議為：`3.11` 以上。

### 取得專案

```bash
git clone git@github.com:zyzy0826/Youbike-free.git
```

### 移動到專案內

```bash
cd Youbike-free
```

### 安裝套件

```bash
pip install -r requirements.txt
```

### 環境變數設定

請在終端機輸入 `cp .env.example .env` 來複製範本，並依需求填入金鑰。
Google Maps 校正與 AI 建議為**選用**功能，不填也能執行（時間用估算、AI 改本地摘要）。

### 運行專案

```bash
streamlit run app.py
```

### 開啟專案

執行後終端機會顯示網址，於瀏覽器開啟即可看到畫面（預設）：

```bash
http://localhost:8501/
```

> 提醒：修改 `.env` 後需重新啟動 `streamlit run app.py` 才會生效。

## 環境變數說明

```env
GOOGLE_MAPS_API_KEY=   # Google Maps Platform 金鑰（用於道路時間校正，需啟用 Distance Matrix API）
GEMINI_API_KEY=        # Google Gemini 金鑰（AI 行程建議；申請：https://aistudio.google.com/app/apikey）
GEMINI_MODEL=gemini-2.5-flash   # 便宜快速且仍在服務中的模型（1.5/2.0 已退役）
```

## 資料夾說明

- `app.py` - Streamlit 入口（UI、流程編排）
- `config/` - 各縣市免費規則、生活圈定義、`.env` 與金鑰設定
  - `city_rules.py` - 免費規則（兩 case）、API 端點、生活圈
  - `settings.py` - 零相依 `.env` 載入與金鑰存取
- `data/` - 資料擷取與清洗
  - `fetcher.py` - YouBike 開放資料擷取（含 JSON 快取、巢狀格式容錯）
  - `preprocessor.py` - 欄位正規化與異常站過濾
- `core/` - 演算法核心
  - `time_estimator.py` - haversine 距離與騎乘／步行時間估算
  - `graph_builder.py` - 站點圖建構（逐段依借車地縣市套用免費上限）
  - `route_optimizer.py` - BFS／Dijkstra 路徑與冷卻改借建議
  - `cooldown.py` - node-split 冷卻模型（borrow/return 節點 + walk/wait 邊）
  - `geocoder.py` - 地址 → 經緯度（Nominatim，站點優先）
  - `gmaps.py` - Google Maps 道路時間校正（含 driving 距離回退）
  - `feedback.py` - AI 回饋：事實收集 + Gemini 語氣潤飾
- `visualization/` - Folium 地圖渲染（`map_renderer.py`）
- `scripts/` - CLI 煙霧測試與資料檢視腳本
- `tests/` - pytest 單元測試
- `.streamlit/config.toml` - Streamlit 主題與伺服器設定

## 專案技術

- Python 3.11+
- Streamlit 1.43+
- streamlit-folium 0.18+
- Folium 0.15+
- NetworkX 3.0+
- pandas 2.0+ / numpy 1.24+
- geopy 2.4+
- requests 2.31+

## 第三方服務

- 台北市／新北市／桃園市 YouBike 開放資料 API
- OpenStreetMap Nominatim（地址地理編碼）
- Google Maps Platform（Distance Matrix，道路時間校正）
- Google Gemini（AI 行程建議）

## 測試

本專案以 pytest 進行單元測試（API、地理編碼、Google／Gemini 皆以 mock 離線測試）：

```bash
python -m pytest -q
```

> 目前 89 passed。另可跑煙霧測試：`python scripts/smoke_plan_route.py`、`python scripts/smoke_render_map.py`。

## 部署

本專案可一鍵部署到 Streamlit Community Cloud（免費）。完整步驟與 Secrets 設定請見 [DEPLOY.md](DEPLOY.md)：金鑰透過 Streamlit Secrets 提供，啟動時會自動橋接到環境變數。

## 聯絡作者

你可以透過以下方式與我聯絡

- [GitHub](https://github.com/zyzy0826)
<!-- 可自行增補：部落格 / Facebook / Instagram / Email 等 -->
