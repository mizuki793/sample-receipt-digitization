import os
import streamlit as st
import httpx
import logging

# バックエンドAPIのURLを環境変数から取得（コンテナ間通信のドメインを指定）
BACKEND_URL = os.getenv("BACKEND_URL", "http://search-rag-service:8001/v1/chat/stream")

st.set_page_config(page_title="最安値お買い物チャットAI", layout="centered")
st.title("最安値お買い物チャットAI")

# 1. セッション状態（会話履歴）の初期化
# Streamlitの再描画（Rerun）による履歴消失や、APIの重複呼び出しを防ぎます
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. 過去のチャット履歴を画面に再描画
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 3. バックエンドからのストリーミング応答を受信・描画するヘルパー関数
def get_streaming_response(prompt: str):
    try:
        # httpxのストリームコンテキストを使用して非同期的にデータを受け取ります
        # フロントエンド側はシンプルな同期型のストリームパース処理で記述可能です
        with httpx.stream(
            "POST",
            BACKEND_URL, 
            json={"message": prompt},
            timeout=60.0
        ) as response:
            if response.status_code != 200:
                error_detail = response.read().decode("utf-8")
                # エラー解析用 
                logging.error(f"エラーが発生しました (Status Code: {response.status_code})\n詳細: {error_detail}")
                yield f"エラーが発生しました (Status Code: {response.status_code})"
                return

            # バックエンドから1行ずつデータが送られてくるのを監視
            for line in response.iter_lines():
                if line.startswith("data: "):
                    # 「data: 」の接頭辞を削り、実際のテキストを抽出
                    content = line[6:]
                    if content:
                        yield content
    except Exception as e:
        yield f"通信エラーが発生しました: {str(e)}"

# 4. ユーザーからの新規入力処理
if user_input := st.chat_input("卵が一番安いお店はどこ？"):
    # ユーザーの入力を画面に表示し、履歴に保存
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # AIの応答エリアを確保して、ストリーミング描画を実行
    with st.chat_message("assistant"):
        # st.write_stream にジェネレータを渡すことで、文字が自動でパラパラと流れるUIになります
        response_placeholder = st.write_stream(get_streaming_response(user_input))
        
    # 生成完了した最終的な文字列を履歴に追加
    st.session_state.messages.append({"role": "assistant", "content": response_placeholder})
