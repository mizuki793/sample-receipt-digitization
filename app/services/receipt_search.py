import duckdb
import logging
from pathlib import Path
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings
from app.schemas.search import SearchStatsResponse, StoreStat, TimeZoneStat

class ReceiptSearchService:
    @classmethod
    async def search_item_stats(cls, query_word: str) -> SearchStatsResponse:
        """
        DuckDBを使用して、JSONファイル群から部分一致で最安値・店舗別統計・時間帯統計を抽出する
        """
        # 同期処理であるDuckDBのクエリ実行をスレッドプールに逃がして非同期化
        return await run_in_threadpool(cls._execute_duckdb_query, query_word)

    @classmethod
    def _execute_duckdb_query(cls, query_word: str) -> SearchStatsResponse:
        search_pattern = Path(settings.LOCAL_DATA_SET_BASE_DIR) / "archive" / "**" / "*.json"
        
        con = duckdb.connect(database=":memory:")
        
        try:
            # 1. 共通のデータ展開処理（WITH句）
            # transaction_date から購入時間（Hour）を抽出しておきます
            setup_query = f"""
                CREATE OR REPLACE TEMP TABLE flattened_receipts AS
                SELECT 
                    corrected_json.store_name AS store_name,
                    epoch(CAST(corrected_json.transaction_date AS TIMESTAMP)) AS ts,
                    hour(CAST(corrected_json.transaction_date AS TIMESTAMP)) AS item_hour,
                    UNNEST(corrected_json.items) AS item
                FROM read_json_auto('{search_pattern}', hive_partitioning=1)
                WHERE corrected_json.needs_correction IS NOT NULL;
            """
            con.execute(setup_query)
            
            # 2. 店舗別の最安値・平均価格・検知数の集集計 (部分一致 LIKE)
            # SQLインジェクションを防ぐため、安全にプレースホルダを使用
            store_query = f"""
                SELECT 
                    store_name,
                    CAST(MIN(item.unit_price) AS INTEGER) AS min_price,
                    CAST(ROUND(AVG(item.unit_price)) AS INTEGER) AS avg_price,
                    CAST(COUNT(*) AS INTEGER) AS total_count
                FROM flattened_receipts
                WHERE item.item_name LIKE ?
                GROUP BY store_name
                ORDER BY min_price ASC;
            """
            store_rows = con.execute(store_query, [f"%{query_word}%"]).fetchall()
            
            # 3. 購入時間帯の偏りの集計
            time_query = f"""
                SELECT 
                    LPAD(CAST(item_hour AS VARCHAR), 2, '0') || ':' || 
                    LPAD(CAST((item_minute // 30) * 30 AS VARCHAR), 2, '0') || '-' ||
                    LPAD(CAST(CASE WHEN item_minute < 30 THEN item_hour ELSE item_hour + 1 END AS VARCHAR), 2, '0') || ':' ||
                    CASE WHEN item_minute < 30 THEN '30' ELSE '00' END AS time_zone,                    
                    CAST(COUNT(*) AS INTEGER) AS count
                FROM (
                    SELECT 
                        hour(CAST(corrected_json.transaction_date AS TIMESTAMP)) AS item_hour,
                        minute(CAST(corrected_json.transaction_date AS TIMESTAMP)) AS item_minute,
                        UNNEST(corrected_json.items) AS item
                    FROM read_json_auto('{search_pattern}', hive_partitioning=1)
                    WHERE corrected_json.needs_correction IS NOT NULL
                )
                WHERE item.item_name LIKE ?
                GROUP BY time_zone
                ORDER BY 
                    count DESC, time_zone ASC;
            """
            time_rows = con.execute(time_query, [f"%{query_word}%"]).fetchall()
            
            # 4. Pydanticモデルへマッピング
            store_stats = [
                StoreStat(store_name=r[0], min_price=r[1], avg_price=r[2], total_count=r[3])
                for r in store_rows
            ]
            time_zone_stats = [
                TimeZoneStat(time_zone=r[0], count=r[1])
                for r in time_rows
            ]
            
            return SearchStatsResponse(
                query=query_word,
                store_stats=store_stats,
                time_zone_stats=time_zone_stats
            )
        except duckdb.IOException as e:
            
            logging.error(f"DuckDB スキャン対象にファイルが存在しません: {e}")
            return SearchStatsResponse(
                query=query_word,
                store_stats=[],
                time_zone_stats=[]
            )    
        finally:
            con.close()
