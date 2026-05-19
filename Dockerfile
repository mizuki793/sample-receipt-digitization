FROM python:3.11-slim

# コンテナ内の作業ディレクトリを設定
WORKDIR /app

# 環境変数の設定（Pythonのバッファリングを無効化し、ログをリアルタイムで出力）
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 依存ライブラリのインストール
# ※ requirements.txt が空でもエラーにならないように記述
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# ポート8000を開放
EXPOSE 8000

# UvicornでFastAPIを起動（0.0.0.0で全インターフェースをリッスン、hot reload有効化）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
