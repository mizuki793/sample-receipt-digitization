## 開発ガイド

本プロジェクトでは、コードの品質維持とバグの混入防止のため、コミット時に自動的にテスト（pytest）を実行するツール「pre-commit」を導入しています。
テストが通過しない限り、git commit が実行できない仕組みになっています。

### pre-commit のセットアップ手順

ローカル環境（ホストマシン）で以下の手順を実行し、コミットフックを有効化してください。

1. pre-commit ツールのインストール
    - Linux / macOS (Homebrew) の場合:
        > brew install pre-commit

    - Python (pip) を使用する場合:
        > pip install pre-commit

1. Git フックの有効化
    - プロジェクトのルートディレクトリ（.pre-commit-config.yaml がある場所）で以下のコマンドを実行します。
        > pre-commit install
    - 設定が完了すると、「pre-commit installed at .git/hooks/pre-commit」と表示されます。

### 日常の開発フロー

1. 通常通りファイルの修正を行い、ステージング領域に追加します（git add）。
2. コミットを実行します（git commit -m "メッセージ"）。
3. 自動的にバックグラウンドでコンテナ内の pytest が実行されます。
   - すべてのテストがパス（Passed）した場合のみ、コミットが成功します。
   - テストが失敗（Failed）した場合は、コミットが自動的にブロックされます。コードを修正し、テストが通る状態にしてから再度コミットしてください。

※ 注意: pre-commit を動作させるには、バックグラウンドで Docker コンテナ（docker compose up）が起動している必要があります。コンテナが停止している場合はテストが実行できず、コミットがエラーになります。

### 特殊な操作

ドキュメントの修正など、テストの実行が不要で強制的にコミットしたい場合は、末尾に「--no-verify」フラグを付与してコミットを強制実行できます。

$ git commit -m "docs: タイポの修正" --no-verify