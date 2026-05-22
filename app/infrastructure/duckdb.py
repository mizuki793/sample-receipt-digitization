import os
import duckdb
from pathlib import Path
from app.config import settings

DUCKDB_PATH = settings.DUCKDB_PATH
def init_database():
    db_path = DUCKDB_PATH
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to DuckDB at: {db_path}")
    conn = duckdb.connect(db_path)
    
    try:
        # TBL作成
        conn.execute("""
                    CREATE TABLE IF NOT EXISTS ocr_few_shots (
                        job_id VARCHAR PRIMARY KEY,
                        store_name VARCHAR,
                        raw_ocr_text TEXT NOT NULL,
                        corrected_json TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
        print("Table 'ocr_few_shots' created successfully.")

        # 初期データ（Few-Shot用の実績データ）のインサート
        count = conn.execute("SELECT COUNT(*) FROM ocr_few_shots").fetchone()[0]
        
        if count == 0:
            samples = [
                (
                    "001",
                    "ファミマ",
                    "ファミリーマート 渋谷店\n5A ￥150\nGait ￥150", 
                    '{"store_name": "ファミリーマート 渋谷店", "items": [{"name": "卵", "price": 150}], "total": 150}'
                ),
                (
                    "002",
                    "セブン",
                    "セブン-イレブン 新宿店\nおにぎり 120\n5A 200\n合計 320", 
                    '{"store_name": "セブン-イレブン 新宿店", "items": [{"name": "おにぎり", "price": 120}, {"name": "卵", "price": 200}], "total": 320}'
                ),
            ]
            conn.executemany("""
                INSERT INTO ocr_few_shots (job_id, store_name, raw_ocr_text, corrected_json)
                VALUES (?, ?, ?, ?);
            """, samples)
            print(f"Successfully inserted {len(samples)} sample records.")
        
        else:
            print(f"Table already contains {count} records. Skipping data insertion.")   

    finally:
        conn.close()

if __name__ == "__main__":
    init_database()