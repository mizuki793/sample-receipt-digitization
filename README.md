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
    end
    participant LLM as OpenAI API

    %% ーーー 1. ジョブの受付フェーズ ーーー
    Note over Client, API: 【1. ジョブの受付フェーズ (Issue #1, #2)】
    Client->>API: POST /v1/receipt/execute (画像ファイル)
    activate API
    Note over API: 画像をコンテナ内の一時フォルダに保存<br/>UUIDから job_id を生成
    API->>Redis: ジョブ初期化保存 (status="PENDING", TTL=1時間)
    API->>Task: タスクを登録 (job_id, 画像パス)
    API-->>Client: 202 Accepted (job_id, status="PENDING")
    deactivate API
    Note over Client, API: ※ クライアント側は待たされずに即解放

    %% ーーー 2. バックグラウンド処理フェーズ ーーー
    Note over Task, LLM: 【2. バックグラウンド処理フェーズ (Issue #3 ~ #5)】
    activate Task
    Task->>Redis: ステータス更新 (status="PROCESSING")
    
    Note over Task: [Issue #4] コード内の擬似テキストで検証<br/>[Issue #5] 保存された本物画像を読み込み
    
    loop 整合性チェック不合格時の自動リトライ (最大3回) [Issue #5]
        Task->>LLM: 解析リクエスト (Structured Outputs)
        LLM-->>Task: レシートデータ (JSON)
        Note over Task: [Issue #3] 総額整合性チェック<br/>𝝨(各品目) == 請求総額
        alt 整合性OK
            Note over Task: ループを抜ける
        else 整合性NG (かつリトライ上限未満)
            Note over Task: プロンプトにエラー内容をフィードバックして再挑戦
        end
    end

    alt 解析・検証 成功
        Task->>Redis: 結果を格納 (status="SUCCESS", result=データ)
    else リトライ上限到達 / システムエラー
        Task->>Redis: エラーを記録 (status="FAILED", result=エラー内容)
    end
    deactivate Task

    %% ーーー 3. ステータス確認フェーズ ーーー
    Note over Client, Redis: 【3. ステータス確認フェーズ (Issue #2)】
    loop status が SUCCESS または FAILED になるまで定期実行（ポーリング）
        Client->>API: GET /v1/jobs/status/{job_id}
        activate API
        API->>Redis: job_id の状態を問い合わせ
        Redis-->>API: 現在のステータス & 結果 (なければ404)
        API-->>Client: 200 OK (status, result)
        deactivate API
    end
  ```
  * 実行
  * dir構成
---
# メモ書き
## 仮想環境set(dockerへ変更)
1. 仮想環境作成
> docker-compose up -d
1.　サーバー起動
> docker compose up --build

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
## 🏗️ 組み立て直した新・Issueロードマップ（全5タスク）

### 1️⃣ 【環境構築】Docker Composeによるマルチコンテナ環境（FastAPI + Redis）の構築

まずは「すべての土台」となるコンテナインフラをワンコマンドで立ち上がる状態にします。

* **目的**:
ホストマシンの環境（venvなど）に依存せず、`docker compose up` のみで開発環境（FastAPI + Redis）が完全に同期して起動するマルチコンテナ基盤を構築する。
* **Doneの定義**:
* [ ] リポジトリルートに `Dockerfile` と `docker-compose.yml` が用意されていること。
* [ ] ホスト側のソースコード変更がコンテナ内のUvicornにリアルタイム反映されるよう、`volumes`（マウント）が正しく設定されていること。
* [ ] アプリ起動時に、FastAPIからRedisへの接続（非同期クライアント `redis.asyncio` を使用）の疎通確認ログが出力されること。



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