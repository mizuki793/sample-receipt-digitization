# 構成
* TBD (将来的に下記を記載)
  * 何をするアプリか
  * シーケンス図(marmaid) 

  ```mermaid
  sequenceDiagram
    autonumber
    actor User as ユーザー (ブラウザ/フロント)
    participant API as PC (FastAPI バックエンド)
    participant LLM as AI (OpenAI API)

    Note over User, API: Issue#1〜#3 の範囲
    User->>API: 1. レシートの生テキストを送信<br/>(POST /api/v1/receipts/analyses)
    
    Note over API: 2. Pydanticで入力チェック
    
    Note over API, LLM: Issue #4 の範囲
    API->>LLM: 3. あなたのプロンプト + 生テキストを投入<br/>(Structured OutputsでPydanticの型を指定)
    LLM-->>API: 4. 解析された構造化JSONデータを返却
    
    Note over API: Issue #5 の範囲
    API->>API: 5. プログラムによる合計金額の検証<br/>(商品の unit_price × quantity の合計 == total_amount ?)
    
    ALT 検証OKの場合
        API-->>User: 6. 100%安全な解析結果（JSON）を返却
    ELSE 検証NG（計算が合わない）の場合
        API->>LLM: 7. 【セルフリフレクション】「計算が合いません。再計算して」
        LLM-->>API: 8. 修正されたJSONを返却
        API-->>User: 9. 修正後の結果を返却（ダメならエラーハンドリング）
    END
  ```
  * 実行
  * dir構成
---
# メモ書き
## 仮想環境set
1. 仮想環境作成
> python -m venv sample-receipt
1. 仮想環境activate
> . sample-receipt/bin/activate

## app実行
1.　サーバー起動
> uvicorn main:app --reload

## todo
* method名,変数名の修正
* テストクラス作成
* venvではなくdockerの方が良いかもしれない
* [todo]軽量なlocal-llmを利用する方が良い気がする(local実行を前提に書いていること,画像に住所などが入っている関係であまり外部に学習されたくないため)
  * PCスペックが弱いのでクラウドAPIを利用する
  * 将来的な切り替えが実施できるコードにする->lite llmを導入したい
* [todo]AIにレビューさせたい