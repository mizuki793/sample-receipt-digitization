import duckdb
from pathlib import Path

def verify_duckdb_json_query():
    # 検索対象のHiveディレクトリのベースパス（環境に合わせて調整してください）
    # リモートコンテナ内なら "/app/data/archive/**/*.json" など
    base_path = Path("/app/data/archive") 
    search_pattern = str(base_path / "**" / "*.json")
    
    print(f"スキャン対象パス: {search_pattern}")

    con = duckdb.connect(database=":memory:")

    # 2. JSONファイル群に直接SQLを投げる
    # ※ itemsはオブジェクトの「配列（List）」になっているため、UNNEST関数で1行ずつ展開します。
    query = f"""
            WITH flattened_items AS (
                SELECT 
                    job_id,
                    corrected_json.store_name AS store_name,
                    UNNEST(corrected_json.items) AS item
                FROM read_json_auto('{search_pattern}', hive_partitioning=1)
            )
            SELECT 
                item.item_name AS 商品名,
                MIN(item.unit_price) AS 最安値,
                ANY_VALUE(store_name) AS 最安店舗,
                COUNT(*) AS 総検知数
            FROM flattened_items
            WHERE item.item_name = '卵'
            GROUP BY item.item_name;
        """
    
    try:
        print("🚀 DuckDB クエリ実行中...")
        # クエリを実行して結果を表示
        
        print("\n📊 --- 集計結果 (Pandas DataFrame) ---")
        con.sql(query).show()

        print("-------------------------------------\n")
        
    except Exception as e:
        print(f" エラーが発生しました: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    verify_duckdb_json_query()