import streamlit as st
import time
import asyncio
from api_client import upload_receipt_api, check_job_status_with_polling, lock_job_api, fetch_job_detail_api

def _upload_and_poll_receipt(file) -> tuple[str, str | None]:
    """
    1枚のレシートをアップロードし、最終結果（success / needs_correction / failed / locked）が
    確定するか、最大タイムアウトに達するまで、ポーリングでバックエンドに問い合わせ続けます。
    """
    res_json = upload_receipt_api(file)
    if not res_json:
        return "failed", None
    job_id = res_json.get("job_id")
    if not job_id:
        return "failed", None
    TIMEOUT_LIMIT = 120.0  # 全体の最大待機時間（秒）
    POLLING_INTERVAL = 10.0  # 問い合わせの間隔（秒）
    start_time = time.time()

    while True:
        status = asyncio.run(check_job_status_with_polling(job_id))

        if status in ["success", "needs_correction", "failed", "locked"]:
            return status, job_id
            
        elapsed_time = time.time() - start_time
        if elapsed_time >= TIMEOUT_LIMIT:
            return "timeout", job_id
            
        time.sleep(POLLING_INTERVAL)

def _render_analysis_results(correction_files: list, failed_files: list):
    extended_correction_files = list(correction_files)
    if "skipped_jobs" in st.session_state:
        for skipped_job_id in st.session_state.skipped_jobs:
            # 重複表示を防ぐ
            if not any(f["job_id"] == skipped_job_id for f in extended_correction_files):
                extended_correction_files.append({
                    "filename": f"保留中のレシート ({skipped_job_id[:8]}...)", 
                    "job_id": skipped_job_id
                })

    # 表示制御
    if extended_correction_files:
        with st.sidebar.expander("要手動修正（店舗名・金額が不鮮明など）", expanded=True):
            for job in extended_correction_files:
                col1, col2 = st.columns([3, 2])
                with col1:
                    st.write(f" {job['filename']}")
                with col2:
                    if st.button("修正する", key=f"btn_{job['job_id']}", use_container_width=True):
                        # 最初にバックエンドへロックを要求
                        status_code = lock_job_api(job["job_id"])  
                        if status_code == 200:
                            detail_data = fetch_job_detail_api(job["job_id"])
                            if detail_data:
                                st.session_state.editing_job = detail_data
                                st.rerun()
                        elif status_code == 409:
                            st.sidebar.error("他のユーザーが編集画面を開いています。")
                        else:
                            st.sidebar.error("システムエラーにより、編集ロックに失敗しました。")

    if failed_files:
        with st.sidebar.expander("システムエラー・解析失敗"):
            for f_name in failed_files:
                st.write(f"- {f_name}")

def _process_batch_analysis(uploaded_files: list):
    total_files = len(uploaded_files)
    progress_bar = st.sidebar.progress(0.0)
    status_text = st.sidebar.empty()

    success_count = 0
    correction_needed_files = []
    failed_files = []

    for index, file in enumerate(uploaded_files):
        status_text.text(f"処理中 ({index + 1}/{total_files}): {file.name}")
        result_status, job_id = _upload_and_poll_receipt(file)
        
        if result_status == "success":
            success_count += 1
        elif result_status == "needs_correction" and job_id:
            correction_needed_files.append({"filename": file.name, "job_id": job_id})
        else:
            failed_files.append(file.name)
        
        progress_bar.progress((index + 1) / total_files)

        if index < total_files - 1:
            time.sleep(1.5)
    
    status_text.empty()
    progress_bar.empty()

    if success_count == total_files:
        st.sidebar.success(f"全 {total_files} 件の解析・登録が正常に完了しました！")
    else:
        st.sidebar.warning(f"処理完了: {success_count} 件成功")

    if correction_needed_files:
        if "batch_correction_files" not in st.session_state:
            st.session_state.batch_correction_files = []
        st.session_state.batch_correction_files.extend(correction_needed_files)
    
    if failed_files:
        if "batch_failed_files" not in st.session_state:
            st.session_state.batch_failed_files = []
        st.session_state.batch_failed_files.extend(failed_files)

def render_sidebar_uploader():
    st.sidebar.title("レシート一括管理")
    st.sidebar.write("複数枚のレシートを一括で解析・インデックス登録します。")

    uploaded_files = st.sidebar.file_uploader(
        "レシート画像を選択（最大10枚）",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="receipt_uploader"
    )

    if uploaded_files:
        if len(uploaded_files) > 10:
            st.sidebar.error("一度に応募できるレシートは10枚までです。")
            return
        if st.sidebar.button("一括解析スタート", use_container_width=True):
            _process_batch_analysis(uploaded_files)
    
    current_correction = st.session_state.get("batch_correction_files", [])
    current_failed = st.session_state.get("batch_failed_files", [])
    
    _render_analysis_results(current_correction, current_failed)
