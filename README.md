# YouBike 最省錢騎乘攻略

在地圖上選定出發點與終點，系統自動規劃**全程免費**的 YouBike 騎乘路線。
核心策略：利用各縣市的免費騎乘時間（台北/新北 30 分鐘、桃園 60 分鐘），
透過中途換車，讓每一段騎乘時間都控制在免費上限內。

## 解決什麼問題

YouBike 對較長距離的單趟騎乘會開始收費。但只要在免費時間結束前到達某站
還車、再立即借另一輛車繼續騎，就可以全程不花錢。本工具自動找出**最佳的
換車站序列**，讓你不用自己掐表算路線。

## 功能特性

- **多縣市資料整合**：即時抓取台北、新北 YouBike 開放資料（含 JSON 快取）
- **兩種規劃策略**
  - `fewest_swaps`：最少換車次數（BFS）
  - `shortest_time`：最短總騎乘時間（Dijkstra）
- **生活圈邊界保護**：預設不規劃跨生活圈路線，避免被收 600~1135 元調度費
- **互動式地圖**（Phase 5）：Streamlit + Folium 視覺化，站點顏色顯示車況、
  路線標示換車點與每段預估時間

## 技術架構

```
config/         各縣市免費規則、API 端點、生活圈定義
data/           API 擷取 + 欄位正規化（多 schema 容錯）
core/           站點圖建構 + BFS / Dijkstra 路徑演算法
visualization/  Folium 地圖渲染
tests/          pytest 單元測試（目前 29 passed）
app.py          Streamlit 入口（Phase 5）
```

**演算法本質**：帶約束的圖論最短路徑問題。節點 = YouBike 站點，
邊 = 兩站間的騎乘時間估算（haversine × 1.3 路徑修正 ÷ 12 km/h），
約束 = 每段邊權重 ≤ 免費上限 − 安全餘裕。

## 安裝

```bash
pip install -r requirements.txt
```

需求：Python 3.10+

## 執行

互動介面（Phase 5 開發中）：

```bash
streamlit run app.py
```

CLI 煙霧測試（驗證資料管線與路徑演算法）：

```bash
python scripts/smoke_plan_route.py    # 台北車站 → 淡水捷運站
python scripts/smoke_render_map.py    # 產出 route_preview.html
```

## 開發進度

詳細待辦事項見 [TODO.md](TODO.md)。

- [x] Phase 1：資料擷取 + 快取
- [x] Phase 2：欄位正規化 + 圖建構
- [x] Phase 3：路徑演算法（BFS / Dijkstra）
- [x] Phase 4：Folium 地圖視覺化
- [ ] Phase 5：Streamlit 互動介面
- [ ] Phase 6：進階優化（KD-Tree、桃園/高雄、跨縣市規劃）

## 真實案例

台北車站 → 淡水捷運站（北北桃生活圈、約 19 km）：

| 策略 | 換車次數 | 總騎乘時間 |
|---|---|---|
| 最少換車 | 3 次 | 99.3 分 |
| 最短時間 | 4 次 | 97.2 分 |

每段皆控制在 27 分鐘內（30 分鐘免費 − 3 分鐘安全餘裕），全程免費。
