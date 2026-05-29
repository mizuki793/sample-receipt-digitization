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

    print(f"PR #{pr_number} の情報を取得中...")
    try:
        pr_view_cmd = ["gh", "pr", "view", str(pr_number), "--json", "title,body,closingIssuesReferences"]
        pr_data = json.loads(subprocess.check_output(pr_view_cmd, text=True))
        
        pr_title = pr_data.get("title", "")
        pr_body = pr_data.get("body", "")
        issues = pr_data.get("closingIssuesReferences", [])

        issue_context = ""
        if issues:
            for issue_info in issues:
                issue_num = issue_info.get("number")
                print(f"関連するIssue #{issue_num} の本文を取得中...")
                issue_view_cmd = ["gh", "issue", "view", str(issue_num), "--json", "body"]
                issue_data = json.loads(subprocess.check_output(issue_view_cmd, text=True))
                issue_context += f"\n【Issue #{issue_num} の本文】:\n{issue_data.get('body', '')}\n"
        
        else:
            issue_context = "\n（このPRに直接紐づくGitHubのClosing Issueはありませんでした）\n"
        
        pr_context = f"【PRタイトル】: {pr_title}\n【PR本文】:\n{pr_body}\n{issue_context}"
    except Exception as e:
        print(f"Warning: PRの本文取得に失敗しました。仕様チェックはスキップします: {e}", file=sys.stderr)
        pr_context = "PR本文の取得に失敗したため、利用できません。"

    # 1. あなたが定義したFastAPI専門家のシステムプロンプト
    system_prompt = """あなたは優秀なシニアバックエンドエンジニア（FastAPIの専門家）です。
提示された「PR本文・対象Issue内容」を深く理解した上で、提出されたコード差分（diff）がその目的や「Doneの定義」を正しく満たしているかを検証し、レビューをしてください。

以下の観点でフィードバックを行ってください：
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
    full_prompt = f"""{system_prompt}
### レビュー対象の前提情報（Issue / PR の内容）
{pr_context}

### レビュー対象のコード差分（diff）
```diff
{diff_output}
```"""
  
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

def call_api_with_retry(url, payload, headers, max_retries=3, backoff_factor=5):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=90)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else 500
            # 429, 503 や 500 系列のエラーならリトライする status_codeがない場合は500とする
            if status_code in [500, 502, 503, 504, 429] and attempt < max_retries - 1:
                sleep_time = backoff_factor ** attempt
                print(f"Gemini API 503検知。 {sleep_time}秒後にリトライします... (試行 {attempt + 1}/{max_retries})")
                time.sleep(sleep_time)
                continue
            raise e

if __name__ == "__main__":
    main()
