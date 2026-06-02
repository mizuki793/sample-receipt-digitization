import streamlit as st
import pandas as pd
import time
from api_client import fix_job_api

def render_manual_correction_page():
    """
    【UI表示】メインエリアに全幅でレシート手動補正フォームを描画する関数
    """
    # セッションから現在編集中のジョブデータを安全に取得
    job = st.session_state.editing_job
    print(f"job:{job}")
    analysis = job.get("analysis_result", {})
    
    st.title("レシートデータの手動補正画面")
    st.info(f"対象ジョブID: {job.get('job_id')} | OCRが一部判定できなかった項目を確認・修正してください。")
    
    # 2カラムレイアウト（左にOCR原文、右に入力フォーム）
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.subheader("レシートの原文テキスト（OCR結果）")
        raw_ocr_text = job.get("raw_ocr_text", "テキストがありません")
        st.code(raw_ocr_text, language="text")
        
    with col_right:
        st.subheader("修正フォーム")

        # 基本情報の修正フォーム
        store_name = st.text_input("店舗名", value=analysis.get("store_name", ""))
        store_address = st.text_input("店舗住所", value=analysis.get("store_address", ""))
        transaction_date = st.text_input("取引日時", value=analysis.get("transaction_date", ""))
        total_amount = st.number_input("合計金額（税込）", value=int(analysis.get("total_amount", 0)), step=1)
        tax = st.number_input("内消費税", value=int(analysis.get("tax", 0)), step=1)        
 
        st.write("**品目リストの編集**（セルをダブルクリックして直接修正できます）")

        # 品目リストをDataFrameに変換して st.data_editor で表示
        items_list = analysis.get("items", [])
        df_items = pd.DataFrame(items_list)
        if df_items.empty:
            df_items = pd.DataFrame(columns=["item_name", "unit_price", "quantity", "category"])
            
        edited_df = st.data_editor(df_items, num_rows="dynamic", use_container_width=True, key="items_editor")
        
        # ボタン制御エリア
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("キャンセルして戻る", use_container_width=True):
                cancel_payload = {
                    "store_name": analysis.get("store_name", ""),
                    "store_address": analysis.get("store_address", ""),
                    "transaction_date": analysis.get("transaction_date", ""),
                    "items": items_list,  # 初期リスト
                    "total_amount": int(analysis.get("total_amount", 0)),
                    "tax": int(analysis.get("tax", 0)),
                    "needs_correction": True
                }
                with st.spinner("一時保存しています..."):
                    if fix_job_api(job.get("job_id"), cancel_payload):
                        if job.get("job_id") not in st.session_state.skipped_jobs:
                            st.session_state.skipped_jobs.append(job.get("job_id"))
                        st.session_state.editing_job = None
                        st.rerun()
                
        with btn_col2:
            if st.button("修正データを確定して登録", type="primary", use_container_width=True):
                # 画面の変更値をバックエンド送信用の構造へ再パッケージ
                corrected_payload = {
                    "raw_ocr_text": raw_ocr_text,
                    "fixed_data": {
                        "store_name": store_name,
                        "store_address": store_address,
                        "transaction_date": transaction_date,
                        "items": edited_df.to_dict(orient="records"),
                        "total_amount": total_amount,
                        "tax": tax,
                        "needs_correction": False
                    }
                }
                # api_client経由でバックエンドへ送信
                if fix_job_api(job.get("job_id"), corrected_payload):
                    st.success("データの補正とインデックス登録が完了しました（ロック解除済み）")
                    
                    # サイドバー側の追跡管理リスト（uploaded_jobs）からこのジョブを排除
                    if "uploaded_jobs" in st.session_state:
                        st.session_state.uploaded_jobs = [
                            j for j in st.session_state.uploaded_jobs if j["job_id"] != job.get("job_id")
                        ]
                        
                    time.sleep(1.5)
                    st.session_state.editing_job = None  # チャット画面フラグへ戻す
                    st.rerun()
                else:
                    st.error("バックエンドへのデータ保存に失敗しました。")
