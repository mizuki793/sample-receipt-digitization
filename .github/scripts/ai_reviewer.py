import os
import subprocess
import json
import requests

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
    返答は必ず「日本語」で行い、具体的かつ建設的なアドバイスを心がけてください。"""

  # 2. 安全にgit diffを取得
  try:
      diff_cmd = f"git diff origin/{base_sha}...origin/{head_sha}"
      diff_output = subprocess.check_output(diff_cmd, shell=True, text=True)
  except subprocess.CalledProcessError as e:
      print(f"Failed to get git diff: {e}")
      return

  if not diff_output.strip():
      print("レビューする差分（diff）がありません。")
      return

  # 3. Gemini API (Google AI Studio公式エンドポイント) を直接叩く
  url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
  headers = {"Content-Type": "application/json"}
  
  # プロンプトとコード差分を綺麗に結合
  full_prompt = f"{system_prompt}\n\n以下がレビュー対象のコード差分（diff）です：\n```diff\n{diff_output}\n```"
  
  payload = {
      "contents": [{
          "parts": [{"text": full_prompt}]
      }]
  }

  print("Geminiにコードレビューをリクエスト中...")
  response = requests.post(url, headers=headers, json=payload)
  response.raise_for_status()
  
  # レビュー結果の抽出
  result_json = response.json()
  try:
      review_comment = result_json['candidates'][0]['content']['parts'][0]['text']
  except (KeyError, IndexError):
    print("APIからのレスポンスのパースに失敗しました。")
    print(json.dumps(result_json, indent=2))
    return

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

if __name__ == "__main__":
  main()