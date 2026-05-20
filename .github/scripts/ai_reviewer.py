import os
import subprocess
import sys
import json
import requests
from requests.exceptions import HTTPError
import time

# モデル定義
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def main():
    # 環境変数の受け取り
    api_key = os.environ.get("GOOGLE_API_KEY")
    base_sha = os.environ.get("BASE_SHA")
    head_sha = os.environ.get("HEAD_SHA")
    pr_number = os.environ.get("PR_NUMBER")

    # 1. あなたが定義したFastAPI専門家のシステムプロンプト
    system_prompt = """あなたは優秀なシニアバックエンドエンジニア（FastAPIの専門家）です。
Pull Requestのコード差分をレビューし、以下の観点でフィードバックをしてください。
1. FastAPIのベストプラクティス（async/awaitの適切な使用、Pydanticの型定義など）に沿っているか
2. メソッド名や変数名が直感的で、命名規則（Pythonの型、snake_caseなど）に則っているか
3. バグやセキュリティ上の脆弱性、不要なコードが含まれていないか
4. 指摘する際は、1つのIssue/PRとして独立して扱える「小さな範囲」に留めてください。
返答は必ず「日本語」で行い、具体的かつ建設的なアドバイスを心がけてください。

# 出力に関するルール
-「〇〇さん、PRありがとうございます」「〜を確認しました」といった、人間的な挨拶、お礼、前置き、およびPR全体の要約は出力しないでください。
- 指摘事項の末尾にも、「修正は以上です」「参考にしてください」などの締め括りの挨拶（後書き）は一切禁止します。コードブロックや箇条書きの終了とともに、出力を完全にストップしてください。
- レビューの要点（指摘事項）のみを、いきなり以下のMarkdownフォーマットに則って書き始めてください。
- 指摘事項が1つもない（完璧な）場合は、お礼などは書かずに「LGTM」とだけ出力してください。
# 出力フォーマット
- [ ] **[`対象ファイルパス`]** `指摘内容を1行で記述`
- **理由**: `技術的な懸念点（ベストプラクティスからの逸脱、バグ、脆弱性など）`
```python
# ここに修正コードを記述
```"""

    # 2. 安全にgit diffを取得
    try:
        diff_cmd = ["git", "diff", f"{base_sha}...{head_sha}"]
        diff_output = subprocess.check_output(diff_cmd, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to get git diff: {e}", file=sys.stderr)
        sys.exit(1)

    if not diff_output.strip():
        print("レビューする差分（diff）がありません。")
        sys.exit(1)

    # 3. Gemini API (Google AI Studio公式エンドポイント) を直接叩く
    url = f"{GEMINI_API_BASE_URL.format(model=GEMINI_MODEL)}?key={api_key}"
    headers = {"Content-Type": "application/json"}
  
    # プロンプトとコード差分を綺麗に結合
    full_prompt = f"{system_prompt}\n\n以下がレビュー対象のコード差分（diff）です：\n```diff\n{diff_output}\n```"
  
    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }]
    }

    print("Geminiにコードレビューをリクエスト中...")
    result_json = call_api_with_retry(url, payload, headers=headers)
  
    # レビュー結果の抽出
    try:
        review_comment = result_json['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError) as e:
        print(f"Error: APIからのレスポンスのパースに失敗しました。詳細: {e}", file=sys.stderr)
        print(json.dumps(result_json, indent=2))
        sys.exit(1)

    # 4. GitHub CLI (gh) を使ってPRにコメントを投稿
    # 巨大なテキストのエスケープ問題を避けるため、一度ファイルに書き出して --body-file で安全に投稿します
    output_file = "review_result.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(review_comment)

    print(f"PR #{pr_number} にレビューを投稿しています...")
    try:
        gh_cmd = ["gh", "pr", "comment", str(pr_number), "--body-file", output_file]
        subprocess.run(gh_cmd, check=True)
        print("レビューの投稿が完了しました！ ")
    except subprocess.CalledProcessError as e:
        print(f"GitHub CLIでのコメント投稿に失敗しました: {e}")

def call_api_with_retry(url, payload, headers, max_retries=3, backoff_factor=60):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=90)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            # 503 や 500 系列のエラーならリトライする
            if response.status_code in [500, 502, 503, 504] and attempt < max_retries - 1:
                sleep_time = backoff_factor ** attempt
                print(f"Gemini API 503検知。 {sleep_time}秒後にリトライします... (試行 {attempt + 1}/{max_retries})")
                time.sleep(sleep_time)
                continue
            raise e

if __name__ == "__main__":
    main()
