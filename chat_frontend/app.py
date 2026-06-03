import os
import httpx
import streamlit as st
import httpx
import logging
from src.components.sidebar import render_sidebar_uploader
from src.components.correction_page import render_manual_correction_page
from src.components.chat_page import render_chat_interface_page

# アプリケーション全体の設定
logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="最安値お買い物チャットAI", layout="centered")

# グローバルなセッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

if "editing_job" not in st.session_state:
    st.session_state.editing_job = None

#TODO:修正をスキップした場合の状態保持(sessionに状態を保持したくないため、#68で修正予定)
if "skipped_jobs" not in st.session_state:
    st.session_state.skipped_jobs = []

# 共通コンポーネント（サイドバー）の描画
render_sidebar_uploader()

# メインエリアのルーティング制御（目次）
if st.session_state.editing_job is not None:
    render_manual_correction_page()
else:
    render_chat_interface_page()
