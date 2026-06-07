# YouBike 最省錢攻略 - TODO

## Phase 1: 環境建置與資料取得
- [x] 建立專案結構與虛擬環境
- [x] 撰寫 requirements.txt
- [x] 串接台北市 YouBike API，確認回傳格式
- [x] 串接新北市 YouBike API
- [x] 建立 JSON 快取機制（檔案快取 + TTL 過期）
- [x] 撰寫 fetcher.py 單元測試
- [ ] 在有網路的環境跑一次真實 API 煙霧測試（沙箱無網路）

## Phase 2: 資料清洗與圖建構
- [x] 統一各縣市 API 回傳欄位名稱
- [x] 過濾異常站點（座標為 0、無名稱）
- [x] 實作 haversine 距離計算
- [x] 實作騎乘時間估算函數
- [x] 用 NetworkX 建立站點圖
- [x] 只連接「可用騎乘時間」半徑內的站點對（緯度視窗預過濾優化）
- [x] 撰寫 graph_builder 單元測試
- [x] 用真實台北資料跑一次建圖（1740 站、95 萬邊，6.5s）

## Phase 3: 路徑演算法實作
- [x] 實作最近站點搜尋（暴力搜尋；KD-Tree 留待 Phase 6）
- [x] 實作 BFS 最短路徑（最少換車次數）
- [x] 實作 Dijkstra 最短路徑（最短總時間）
- [x] 處理無解情況並回傳友善訊息
- [x] 驗證：台北車站→淡水 的路線是否合理（fewest_swaps 3 換車/99.3 分，shortest_time 4 換車/97.2 分）
- [x] 撰寫 route_optimizer 單元測試

## Phase 4: 地圖視覺化
- [x] 用 Folium 繪製所有站點（顏色依車輛狀態）
- [x] 繪製推薦路線 PolyLine
- [x] 標記換車站點（含 popup 資訊）
- [x] 標記起終點
- [x] 每段路線標示預估時間
- [x] 撰寫 map_renderer 單元測試

## Phase 5: Streamlit 互動介面
- [x] 建立基本頁面佈局（sidebar + 主區域）
- [x] 實作城市選擇下拉選單（multiselect）
- [x] 實作起終點輸入（先支援經緯度數值輸入；地址 geocoding 留待加強）
- [x] 實作路線策略切換
- [x] 整合 streamlit-folium 顯示地圖
- [x] 顯示路線摘要卡片（4 個 metric）
- [x] 顯示詳細行程表（含每段免費餘裕）
- [x] @st.cache_data / cache_resource 加速重複規劃
- [x] 地址 → 經緯度 geocoding（geopy Nominatim，含節流 + 快取；UI 可切換地址/經緯度輸入）

## Phase 6: 進階功能（加分項）
- [x] 即時車輛數判斷（避免推薦無車/滿位的站）— graph build 依即時車輛數過濾邊，UI 可切換
- [ ] 多縣市支援（桃園、高雄）
- [ ] 跨縣市路線規劃（跨越不同免費時間規則）
- [ ] 同站續借冷卻時間處理（實測約需等待 10–15 分鐘才能再借同一站）
  - [ ] 演算法：加入「步行至鄰近站借車」邊（步行 2–3 分鐘、200–300m 內）
  - [ ] UI 提示：偵測到同站續借時顯示警示（建議改鄰站借車或使用雙卡替換）
  - [ ] 對應 GitHub issue：同站換車冷卻時間（10–15 分鐘）
- [ ] 效能優化：KD-Tree 加速最近站搜尋
- [ ] 部署到 Streamlit Cloud
