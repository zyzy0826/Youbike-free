"""Streamlit 主程式：YouBike 最省錢騎乘攻略。

執行方式:
    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from config import CITY_CONFIG


def render_sidebar() -> dict:
    """側欄：城市、起終點、策略選擇。回傳使用者輸入字典。"""
    raise NotImplementedError


def render_main(user_input: dict) -> None:
    """主區域：地圖、路線摘要卡、行程表。"""
    raise NotImplementedError


def main() -> None:
    st.set_page_config(page_title="YouBike 最省錢攻略", layout="wide")
    st.title("YouBike 最省錢騎乘攻略")
    st.caption("自動規劃中途換車路線，全程免費抵達目的地")
    # user_input = render_sidebar()
    # render_main(user_input)
    st.info("專案骨架已建立，待依 TODO.md 逐步實作。")
    st.write("支援城市：", list(CITY_CONFIG.keys()))


if __name__ == "__main__":
    main()
