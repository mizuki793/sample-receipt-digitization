# レシートOCR + 最安値提案チャットボット — サンプルプロジェクト

- レシート画像を受け取りOCR＋LLMで構造化し、過去レシートデータを用いて最安値提案や会話形式の問い合わせに応答するプロトタイプです。
- ポートフォリオ,PoCを想定しており、ローカルで簡単に試せるDocker Compose構成を提供します。
  - 主な価値(目指す姿): 
    - 実運用に近い非同期ジョブ処理
    - レシート整合性チェック
    - [TBD]表記揺れを吸収した最安値検索（ベクトル検索＋DuckDB集計）
    - ストリーミングチャットの雛形を素早く立ち上げ

## 目次
- [プロジェクト概要](##プロジェクト概要)
- [動作デモ](##動作デモ)
- [機能一覧](##機能一覧)
- [アーキテクチャ（シーケンス図）](##アーキテクチャ概要)
- [技術スタック](##技術スタック)
- [ローカル起動（Docker Compose）](##ローカル起動手順（Docker Compose）)
- [ディレクトリ構成](##ディレクトリ構成)
- [補足](##補足)

---
## プロジェクト概要
このリポジトリは次の機能を統合します。

- レシート画像の受付と非同期OCR解析パイプライン（ジョブ管理、再試行、ステータス保存）
- LLMを用いたOCR結果の誤読補正・構造化出力（店舗名、日時、品目、価格など）
- 過去レシートデータの高速集計（DuckDB）による最安値検索
- ベクトル検索（Chroma）による表記揺れ吸収とRAGベースのチャット対話
- Streamlitフロントエンドでのストリーミング会話インターフェース

---
## 動作デモ
- OCR関連の挙動での読み込みが時間が関係上、動画を1.5倍速にしています



  <kbd>
    <video src="https://github.com/user-attachments/assets/6c56c533-fd23-4717-954f-8ae0be4dbbd6" 
    width="600px" controls muted></video>
  </kbd>


---
## 機能一覧

- `POST /v1/receipt/execute` — レシート画像を受け取りジョブ登録（非同期処理）
- `GET /v1/jobs/status/{job_id}` — ジョブの状態確認
- `POST /v1/chat/stream` — RAGエージェントによる会話（StreamingResponse）
- 管理用: ローカルDuckDBベースの集計、Chromaベースの類似検索、MongoDBでメタを管理

---
## アーキテクチャ概要

シンプルなシーケンス図（主要フロー）を示します。

  ```mermaid
  sequenceDiagram
    autonumber
    actor User as User (Browser / Client)
    box Docker Compose
      participant Front as chat_frontend (Streamlit)
      participant Search as search-rag-service (FastAPI)
      participant Receipt as receipt-fastapi-web (FastAPI)
      participant Mongo as MongoDB
      participant Duck as DuckDB (local)
      participant Chroma as Chroma (VectorDB)
    end
    participant LLM as LLM Provider

    Note over User, Front: 1) ユーザーが画像アップロード／問い合わせ
    User->>Front: 画像アップロード / 質問
    Front->>Receipt: POST /v1/receipt/execute (画像)
    Receipt->>Mongo: ジョブ登録 (job_id, metadata)
    Receipt->>Receipt: バックグラウンド処理開始 (整合性チェック/LLM呼び出し)
    Receipt->>LLM: OCR補正・構造化要求
    LLM-->>Receipt: 構造化JSON
    Receipt->>Duck: 正常データをHive形式で永続化
    Receipt->>Chroma: 商品名をEmbeddingで保存
    Receipt->>Mongo: 結果保存 / ステータス更新

    Note over User, Search: 2) 最安値検索・会話フロー
    User->>Front: 検索 or チャットリクエスト
    Front->>Search: /v1/receipts/search or /v1/chat/stream
    Search->>Chroma: 類似検索（表記揺れ吸収）
    Search->>Duck: 集計クエリで最安値算出
    Search->>LLM: コンテキスト + ユーザー質問 (必要時)
    LLM-->>Search: 応答（Streaming）
    Search-->>Front: StreamingResponse
    Front-->>User: 結果をストリーム表示
  ```

---
## 技術スタック

- Backend: FastAPI (`receipt-fastapi-web`, `search-rag-service`)
- Frontend: Streamlit (`chat_frontend`)
- Data: DuckDB (ローカルJSON集計), Chroma (vector store), MongoDB (ジョブメタ)
- Messaging/State: MongoDB used for job metadata
- LLM: Google Gemini / OpenAI 等（`.env`で切替可）
- Container: Docker / Docker Compose

---
## ローカル起動手順（Docker Compose）

1. リポジトリをクローン

```bash
git clone <repository-url>
cd sample-receipt-digitization
```

2. ルートにある `.env.example` をコピーして `.env` を作成し、必要に応じて値を入力してください。

```bash
cp .env.example .env
# 必要なら編集: vi .env
```

3. Docker Composeでビルド・起動

```bash
docker compose up --build
```

4. 起動後の主要エンドポイント
  - Frontend (Streamlit): 
    - http://localhost:8501

  - APIドキュメント（Swagger）
    - Receipt Service: http://localhost:8000/docs
    - Search RAG API : http://localhost:8001/docs   

  （上記はローカルで `docker compose up --build` 実行後に利用可能です）

  注意: MongoDBは `27017` で公開されています。初回起動にはイメージのダウンロードとビルドが入るため時間がかかります。


---
## ディレクトリ構成

- `chat_frontend/` — Streamlit UI と APIクライアント
- `receipt_service/` — レシート受付・OCR整形・DuckDB永続化（FastAPI）
- `search_rag_service/` — ベクトル検索＋RAGチャット（FastAPI）
- `data/` — サンプルデータ、DuckDBファイル、アーカイブ
- `docker-compose.yml` — 開発用構成

---
## 補足

- 初期状態で `.gitignore` に `.env` が登録されています。公開リポジトリでシークレットを共有しないでください。
- LLMプロバイダやS3ストレージを切り替える場合は `.env` の該当キーを編集してください。

---
