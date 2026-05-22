import duckdb
from fastapi.concurrency import run_in_threadpool
from app.config import settings

class OcrFewShotRepository:
    # 読み込み先のパスをconfigや環境変数から取得
    DB_PATH = settings.DUCKDB_PATH

    @classmethod
    def _search_sync(cls, raw_text: str, limit: int = 2) -> list[dict]:
        """
        DuckDBに接続して文字列類似度（Levenshtein距離）が近いレコードを検索する同期メソッド
        """
        # 読み取り専用（read_only=True）で接続することで、並行参照時の安全性を高めます
        conn = duckdb.connect(cls.DB_PATH, read_only=True)
        try:
            # levenshtein関数で、今回の入力テキストと過去の生テキストの「編集距離」を計算
            # 距離が小さい（＝似ている）順にソートして上限数まで取得
            query = """
                SELECT raw_ocr_text, corrected_json 
                FROM ocr_few_shots
                ORDER BY levenshtein(raw_ocr_text, ?) ASC
                LIMIT ?
            """
            cursor = conn.execute(query, [raw_text, limit])
            results = cursor.fetchall()
            
            # プロンプトアセンブラで扱いやすいように辞書型のリストに変換
            return [
                {"raw_ocr_text": row[0], "corrected_json": row[1]} 
                for row in results
            ]
        finally:
            conn.close()

    @classmethod
    async def find_similar_shots(cls, raw_text: str, limit: int = 2) -> list[dict]:
        """
        FastAPIのイベントループをブロックしないための非同期ラッパーメソッド
        """
        return await run_in_threadpool(cls._search_sync, raw_text, limit)
