"""各縣市 YouBike 免費騎乘規則與 API 端點設定"""

CITY_CONFIG = {
    "台北市": {
        "free_minutes": 30,
        "eligibility": "會員即享",
        "api_url": "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json",
        "living_circle": "北北桃",
        "note": "2024/2/28 起前 30 分鐘免費（市府補助 10 元）",
    },
    "新北市": {
        "free_minutes": 30,
        "eligibility": "會員即享",
        "api_url": "https://data.ntpc.gov.tw/api/datasets/010e5b15-3823-4b20-b401-b1cf000550c5/json?size=2000",
        "verify_ssl": False,  # NTPC 憑證缺 Subject Key Identifier，新版 Python ssl 驗證會失敗
        "living_circle": "北北桃",
        "note": "2025/3/1 起前 30 分鐘免費",
    },
    "桃園市": {
        "free_minutes": 60,
        "eligibility": "TPASS 月票",
        "api_url": "TODO_NEED_TO_FIND",
        "living_circle": "北北桃",
        "note": "TPASS 用戶前 60 分鐘免費",
    },
    "高雄市": {
        "free_minutes": 30,
        "eligibility": "TPASS / MeN Go",
        "api_url": "TODO_NEED_TO_FIND",
        "living_circle": "嘉南高屏",
        "note": "TPASS/MeNGo 用戶前 30 分鐘免費；轉乘大眾運輸 1hr 內借車亦免費",
    },
    "屏東縣": {
        "free_minutes": 30,
        "eligibility": "會員即享",
        "api_url": "TODO_NEED_TO_FIND",
        "living_circle": "嘉南高屏",
        "note": "會員第一個 30 分鐘由縣府補助",
    },
}

# 同一生活圈內跨縣市借還車免調度費
# 跨生活圈歸還需支付 600～1135 元調度費
LIVING_CIRCLES = {
    "北北桃": ["台北市", "新北市", "桃園市"],
    "嘉南高屏": ["嘉義市", "嘉義縣", "台南市", "高雄市", "屏東縣"],
}

# 跨生活圈調度費（NTD）—— 用於警告訊息
CROSS_CIRCLE_FEE_NTD = (600, 1135)


def city_to_circle(city: str) -> str | None:
    """回傳該縣市所屬生活圈名稱；找不到回傳 None。"""
    for circle, members in LIVING_CIRCLES.items():
        if city in members:
            return circle
    return None

# 騎乘參數預設值
DEFAULT_CYCLING_SPEED_KMH = 12      # 平均騎乘速度
ROUTE_DETOUR_FACTOR = 1.3           # 實際路徑 vs 直線距離修正係數
SAFETY_MARGIN_MINUTES = 3           # 安全餘裕（建議提前幾分鐘還車）
