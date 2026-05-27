import textwrap

class ReceiptPromptAssembler:
    @classmethod
    def _get_example_section(cls, few_shots: list[dict] = None) -> str:
        example_section = "\n    # 抽出例(Few-shot Example)\n"
        
        if few_shots:
            # DuckDBから過去実績が取れてきた場合は、それを優先してプロンプトに埋め込む
            for i, shot in enumerate(few_shots, 1):
                example_section += f"    ## 例{i}: 過去の修正実績（類似ケース）\n"
                example_section += f"      ### テキスト入力\n"
                example_section += f"        ```text\n{shot['raw_ocr_text']}\n         ```\n"
                example_section += f"      ### 出力期待値\n"
                example_section += f"        ```json\n{shot['corrected_json']}\n        ```\n"
        else:
        # DuckDBが空、またはヒットしなかった場合のフォールバック（既存の固定例1）
                        # 固定例のインデントを修正
            fixed_example = """\
            ## 例1: 固定の修正実績（基本ケース）
              ### テキスト入力
                ```text
                ファミリーマート⚪︎⚪︎店
                東京都江東区夢の島2-1-2
                領収書
                2026年5月18日(月) 12:09
                ※アサヒミツヤウルトラストロングレモン ¥96
                ※ニッコウアブラアゲ5マイ        ¥105
                合計               ¥201
                ```
              ### 出力期待値
                ```json
                {
                  "store_name": "ファミリーマート⚪︎⚪︎店",
                  "transaction_date": "2026-05-18T12:09:00",
                  "items": [
                      {"item_name": "アサヒミツヤウルトラストロングレモン", "quantity": 1, "unit_price": 96, "category": "飲料・お酒"},
                      {"item_name": "ニッコウアブラアゲ5マイ", "quantity": 1, "unit_price": 105, "category": "日配品（乳製品・豆腐・卵・パンなど）"}
                  ],
                  "total_amount": 201
                }
                ```
            """
            example_section += textwrap.dedent(fixed_example)
        return example_section

    @classmethod
    def build_few_shot_receipt_prompt(cls, text: str, few_shots: list[dict] = None) -> str:
        base_prompt = f"""
        # 命令
        - あなたは、OCRされた日本の紙レシートを解析し指定されたJSON形式に変換する専門家です。以下のルールに従って与えられたテキストから情報を抽出してください。
        # ルール
        - 特に購入商品の名称である"item_name"、商品の価格"unit_price"、店名"store_name"を取得したいと考えています。これらの誤字脱字を一般的な商品名に補正してください。
        - 下記を検討し、投入してください
          - 値の適切性
          - 項目の適切性
        - 各商品について、日本の一般的なスーパーの売場に基づいた"category"を以下の選択肢から厳密に分類してください：
          - ['生鮮（肉）', '生鮮（魚）', '生鮮（野菜・果物）', '惣菜・お弁当', '日配品（乳製品・豆腐・卵・パンなど）', '加工食品（調味料・レトルト・缶詰など）', 'お菓子', '飲料・お酒', '日用品・雑貨', 'その他']
        - 日付(transaction_date)は'YYYY-MM-DDTHH:MM:SS'形式に正規化してください。時分秒が不明、あるいはレシートから取得できない場合は、一律で時分秒を'00:00:00'として埋めてください（例:2026-05-19T00:00:00）。
        - 金額に関するフィールド(unit_price, amount, subtotal, tax, total_amount)は全て整数にしてください。
        - "items"のリストには、購入した商品のみを含めてください。小計や税、合計金額などは含めないでください。
        - 数量が明記されていない商品の"quantity"は、1としてください。
        - テキストから抽出できない項目は、"null"としてください。
        - 誤読補正例を3回以上確認した上で項目にあった出力してください。
        # 誤読補正例
        - 「\」→ 「¥」
        - 「\\」→ 「¥」
        - 「l」や「|」 ➔ 「1」
        - 「O（オー）」 ➔ 「0（ゼロ）」
        - 金額の手前に存在する文字列は単語として成立する文字列として読み替えられないかを検討する
        """

        # 2. 抽出例（Few-shot）セクションの動的組み立て
        example_section = cls._get_example_section(few_shots)
        # 3. 今回の入力テキストを結合
        input_section = f"""
        # 入力
        {text}
        """

        return base_prompt + example_section + input_section
