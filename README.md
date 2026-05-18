# 構成
* TBD (将来的に下記を記載)
  * 何をするアプリか
  * シーケンス図(marmaid) 
  * 実行
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