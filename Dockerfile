FROM python:3.11-slim

# コンテナ内の作業ディレクトリを設定
WORKDIR /app

# 環境変数の設定（Pythonのバッファリングを無効化し、ログをリアルタイムで出力）
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# OpenCVや画像処理に必要なLinuxライブラリをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-jpn \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libx11-xcb1 \
    libxcb-render0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 依存ライブラリのインストール
# ※ requirements.txt が空でもエラーにならないように記述
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのソースコードをコピー
COPY ./app/ .

# ポート8000を開放
EXPOSE 8000

# UvicornでFastAPIを起動（0.0.0.0で全インターフェースをリッスン、hot reload有効化）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
