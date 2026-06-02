import streamlit as st
import httpx
from config import settings

def render_chat_interface_page():
    st.title("最安値お買い物チャットAI")
    
    # 過去ログの再描画
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # チャットストリーミング内部ロジック
    def get_streaming_response(prompt: str):
        try:
            url = f"{settings.BACKEND_URL}/chat/stream"
            with httpx.stream("POST", url, json={"message": prompt}, timeout=60.0) as response:
                if response.status_code != 200:
                    yield f"エラーが発生しました (Status Code: {response.status_code})"
                    return
                
                for raw_line in response.iter_lines():
                    line = raw_line.strip()
                    if not line:
                        continue

                    if line.startswith("data: "):
                        content = line[5:].strip()

                        if content == "[DONE]":
                            break

                        if content:
                            yield content

        except Exception as e:
            yield f"通信エラーが発生しました: {str(e)}"

    # ユーザーからの新規入力処理
    if user_input := st.chat_input("牛乳が一番安いお店はどこ？"):
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            response_placeholder = st.write_stream(get_streaming_response(user_input))

        st.session_state.messages.append({"role": "assistant", "content": response_placeholder})
