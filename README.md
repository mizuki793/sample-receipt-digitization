# 構成
* TBD (将来的に下記を記載)
  * 何をするアプリか
  * シーケンス図(marmaid) 

  ```mermaid
  sequenceDiagram
    autonumber
    actor Client as クライアント (フロント)
    box Docker Compose環境
        participant API as FastAPIコンテナ (Web)
        participant Redis as Redisコンテナ (KVS)
        participant Task as Background Task (非同期)
        participant Storage as ローカルストレージ (Hive JSON)
        participant VectorDB as Chromaコンテナ (Vector)
    end
    participant LLM as OpenAI API

    %% 1. レシート処理：ジョブの受付
    Note over Client, API: 【1. レシート処理：ジョブの受付】
    Client->>API: POST /v1/receipt/execute (画像ファイル)
    activate API
    Note over API: 画像を一時フォルダに保存<br/>UUIDから job_id を生成
    API->>Redis: ジョブ初期化保存 (status="PENDING")
    API->>Task: タスクを登録 (job_id, 画像パス)
    API-->>Client: 202 Accepted (job_id, status="PENDING")
    deactivate API

    %% 2. レシート処理：非同期バックグラウンド解析＆永続化
    Note over Task, VectorDB: 【2. レシート処理：バックグラウンド解析＆データ蓄積】
    activate Task
    Task->>Redis: ステータス更新 (status="PROCESSING")
    
    loop 整合性チェック不合格時の自動リトライ (最大3回)
        Task->>LLM: 解析リクエスト (Structured Outputs)
        LLM-->>Task: レシートデータ (JSON: 店舗名、日時、品目、価格)
        Note over Task: 総額整合性チェック<br/>𝝨(各品目価格) == 請求総額
    end

    alt 解析・検証 成功
        %% Hive形式保存
        Task->>Storage: Hive形式でJSONファイルを永続化<br/>(year=YYYY/month=MM/day=DD/job_id.json)
        
        %% Vector DBへの同期（表記揺れ吸収用）
        Note over Task: 商品名をOpenAI Embeddingでベクトル化
        Task->>VectorDB: 商品名ベクトル ＆ メタデータ(価格・店舗)を保存
        
        Task->>Redis: 結果を格納 (status="SUCCESS")
    else リトライ上限到達 / システムエラー
        Task->>Redis: エラーを記録 (status="FAILED")
    end
    deactivate Task

    %% 3. 通常の最安値検索 (POST)
    Note over Client, Storage: 【3. 通常の最安値検索 (Pydanticガード ＋ DuckDB)】
    Client->>API: POST /v1/receipts/search (BODY: 検索商品名)
    activate API
    Note over API: Pydanticによる長文・不正文字列のバリデーション
    API->>API: DuckDBをインメモリ起動
    API->>Storage: Hive内の全JSONに対してSQLを実行<br/>(店舗別・時間帯別の最安値を高速集計)
    Storage-->>API: 集計結果データ
    API-->>Client: 200 OK (店舗別最安値・統計情報)
    deactivate API

    %% 4. AIチャット対話＆最安値RAGエージェント (Streaming)
    Note over Client, LLM: 【4. 自律型AIエージェント対話 (RAG ＋ StreamingResponse)】
    Client->>API: POST /v1/chat/stream (BODY: ユーザーの質問)
    activate API
    
    Note over API: LangGraphエージェントが思考を開始
    
    alt 【思考】ユーザーが「特定商品の表記揺れを含む最安値」を求めた場合
        API->>VectorDB: 商品名ベクトルで類似検索 (表記揺れを吸収)
        VectorDB-->>API: 該当する過去のレシートコンテキストを返却
    else 【思考】ユーザーが「今月の合計額などの集計計算」を求めた場合
        API->>Storage: DuckDBツールを起動してJSON群からSQL集計
        Storage-->>API: 計算結果を返却
    end

    %% Streamingの実行
    API->>LLM: 抽出されたコンテキスト ＋ ユーザーの質問 (stream=True)
    activate LLM
    loop トークンが終了するまで
        LLM-->>API: 逐次テキストトークンを返却
        API-->>Client: StreamingResponse (Server-Sent Eventsで1文字ずつ返却)
    end
    deactivate LLM
    deactivate API
  ```
  * 実行
  * dir構成
  * 構成(メモ書き)
    ```
      【receipt-service】(FastAPI)
      ├── 役割: OCR解析、金額検証、手動補正ループ
      └── DB: DuckDB (ローカルレイク)
            │
            │ (パース成功時にHTTPで通知)
            ▼
    【search-rag-service】(FastAPI / 新コンテナ)
      ├── 役割: 商品名のEmbedding（ベクトル化）、曖昧チャット、レコメンド最安値検索
      └── DB: Chroma (Vector DB)
    ```
---
# メモ書き
## 仮想環境set(dockerへ変更)
- 仮想環境作成
  > docker-compose up -d  
- サーバー起動
  > docker compose up
  - cf.仮想環境削除
    > docker-compose down
  - cf.キャッシュなしbuild(web or redis)
    > docker compose build --no-cache {service名}

- swaggerで確認
  > http://localhost:8000/docs へアクセス

- redis関連(redis格納確認)
  > redis-cli
  > keys *
  > get {id}

- test関連
  > pytest -v {test_ファイルpath or dir}  
  - example  
    > pytest -v app/tests/services/
    test_receipt_service.py

    > pytest -v app/tests
    - PCの都合でこれでしか動かなかった
      > python -m pytest -v app/tests/services/test_receipt_service.py
## todo
* method名,変数名の修正
* テストクラス作成
* [todo]venvではなくdockerの方が良いかもしれない
* 軽量なlocal-llmを利用する方が良い気がする(local実行を前提に書いていること,画像に住所などが入っている関係であまり外部に学習されたくないため)
  * PCスペックが弱いのでクラウドAPIを利用する
  * 将来的な切り替えが実施できるコードにする->lite llmを導入したい
* [done]AIにレビューさせたい

## issue-memo
* 2026/05/19
```
### 2️⃣ 【器づくり】Redisを用いた非同期ジョブ受付とステータス確認APIの実装

外部API（OpenAI）を繋ぐ前に、Redisを使って非同期で状態（ステータス）が変わるWebAPIとしての基本サイクルを完成させます。

* **目的**:
重い処理を同期で待たせないための非同期ジョブ実行基盤を、FastAPIの `BackgroundTasks` と Redis を組み合わせて実装する。
* **Doneの定義**:
* [ ] `POST /v1/receipt/execute` が作成され、画像ファイルを受け取り、UUIDベースの `job_id` を発行して即座に `202 Accepted` を返すこと。
* [ ] ジョブ受付時、Redisに `{ "status": "PENDING", "result": null }` を保存し、同時に有効期限（TTL: 1時間など）を設定すること。
* [ ] バックグラウンドタスク内で `asyncio.sleep(5)` を走らせ、5秒後に自動でRedis上のステータスが `SUCCESS`（ダミーの固定JSON）に更新されること。
* [ ] `GET /v1/jobs/status/{job_id}` で、Redisから現在のステータスと結果をノンブロッキングで取得して返せること。



### 3️⃣ 【ロジック】プログラム側での総額整合性チェック関数の実装

AI呼び出しをモックテキストで検証する前段階として、データの正しさを判定する「純粋なPythonロジック」を独立して実装します。

* **目的**:
パースされたレシートデータを受け取り、品目合計と請求総額の計算が一致しているかを検証するコアロジックを実装する。
* **Doneの定義**:
* [ ] $\sum (\text{各品目の金額}) == \text{請求総額}$ を判定する独立した検証関数（またはPydanticのモデルバリデータ）が実装されていること。
* [ ] あえて計算が合わない偽のモックデータを流した際、非同期タスク側でエラーを検知し、Redis上のステータスを `"FAILED"`（エラー理由付き）に安全に書き換えられること。



### 4️⃣ 【AI接続・テキスト】固定テキストを用いたOpenAI誤読補正と日時正規化の実装

ここで初めて外部APIを接続します。画像の複雑さを排除するため、まずは「テキスト」を入力としてプロンプトと構造化出力の精度を100%に追い込みます。

* **目的**:
非同期タスクの内部ロジックを修正し、コード内に用意したOCRの擬似生テキスト（誤字を含んだレシートテキスト）をOpenAI APIに投入して、誤読を補正した状態でPydanticスキーマにマッピングする。
* **Doneの定義**:
* [ ] `AsyncOpenAI` クライアントを用いて、イベントループをブロックせずに非同期でAPIを呼び出せていること。
* [ ] `response_format`（Structured Outputs）を利用し、LLMからの出力を直接 `ReceiptModel` として安全にパースできていること。
* [ ] 日時の正規化ルールを実装し、時分秒が不明な場合はPydanticのバリデータ等で自動的に `00:00:00` を補完してRedisに保存できること。
* [ ] プロンプトに、日本のレシート特有の誤読補正（「l」➔「1」など）の指示が含まれていること。



### 5️⃣ 【AI接続・画像＆ループ】本物画像への切り替えと、整合性エラー時の自動リトライ制御

最後にすべてのパズルを組み合わせます。「本物の画像送信」への対応と、Issue 3️⃣・4️⃣を組み合わせた「失敗時のリトライループ」を完成させます。

* **目的**:
ジョブ受付時に保存した本物のレシート画像（マルチモーダル）をOpenAIに送るよう拡張し、同時に総額整合性チェックに落ちた場合の自動リトライ制御を実装する。
* **Doneの定義**:
* [ ] コンテナ内のローカルに保存された本物の画像ファイルをOpenAI API（マルチモーダル）に投入して解析できること。
* [ ] 総額整合性チェック（Issue 3️⃣）に失敗した場合、最大3回までプロンプトを「ここが計算が合わないので修正して」と動的に調整して再リクエストするループが非同期タスク内に実装されていること。
* [ ] 最大リトライ回数を超えても計算が合わない場合は、Redisのステータスを `"FAILED"`（`"Total amount mismatch after 3 retries"`）として安全に処理を終了できること。
```