import os
import chromadb
from chromadb.api.types import Documents, Embeddings
from google import genai 

class GeminiEmbeddingFunction:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        
    def __call__(self, input: Documents) -> Embeddings:
        """ChromaDBがベクトル化を実行する際に内部で呼び出すメインロジック"""
        # @TODO:他のAIでも利用可能な書き方を実施すべき
        response = self.client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=input
        )
        return [embedding.values for embedding in response.embeddings]
    
    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        """複数ドキュメントの一括ベクトル化要求に対応するメソッド"""
        return self.__call__(documents)
    
    def embed_query(self, input: str) -> list[float]:
        """ChromaDBの検索時に内部で呼び出される単一クエリ用のベクトル化メソッド"""
        response = self.client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=input
        )
        # 単一文字列の返却値から最初のベクトル配列を抽出して返します
        return [response.embeddings[0].values]
    
    def name(self) -> str:
        """
        ChromaDB 0.5.x の内部バリデーションを完全に通過させるためのプロパティ
        メソッドではなくプロパティにすることで、属性アクセスの不整合を完全に防ぎます
        """
        return "GeminiEmbeddingFunction"

class ChromaDBService:
    def __init__(self):
        # ChromaDBのローカル永続化設定
        data_dir = os.getenv("CHROMA_DATA_DIR", "./chroma_data")
        self.chroma_client = chromadb.PersistentClient(path=data_dir)
        
        # OpenAIの代わりにGoogleのGemini Embedding関数を紐付け
        self.embedding_fn = GeminiEmbeddingFunction(
            api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # コレクションを取得または作成
        self.collection = self.chroma_client.get_or_create_collection(
            name="receipt_items",
            embedding_function=self.embedding_fn
        )
        
        # キャッシュ辞書
        self._embedding_cache = {}

    def store_bulk_items(self, job_id: str, store_name: str, items: list) -> int:
        """
        確定データから商品ごとの複数表現テキストを生成し、一括でChromaDBに登録する
        :param job_id: レシートごとのユニークID
        :param shop_name: 店舗名
        :param items: 商品情報の辞書リスト（item_name, price, category を含む）
        :return: 登録された総ベクトル数
        """
        registered_count = 0

        for item_idx, item in enumerate(items):
            item_name = item.get("item_name")
            unit_price = item.get("unit_price")
            category = item.get("category")

            text_patterns = []

            # 【パターン1：基本形】価格比較用の標準テキスト
            base_text = f"店舗: {store_name} | 商品: {item_name} | 価格: {unit_price}円"
            text_patterns.append(base_text)

            # 【パターン2：検索ヒット率向上用】表記揺れ・類義語対応のテキスト
            search_enhancement_text = f"購入店舗: {store_name} の商品「{item_name}」"
            text_patterns.append(search_enhancement_text)

            # 【パターン3：カテゴリ情報】付与されていれば独立してベクトル化
            if category:
                category_text = f"商品ジャンル: {category} | 具体的な商品名: {item_name}"
                text_patterns.append(category_text)

            for pattern_idx, text in enumerate(text_patterns):
                unique_id = f"{job_id}_item{item_idx}_pat{pattern_idx}"

                self.collection.add(
                    documents=[text],
                    metadatas=[{"job_id": job_id}],
                    ids=[unique_id]
                )
                registered_count += 1

        return registered_count       

    def search_similar_items(self, query_text: str, n_results: int = 3):
        """Geminiのベクトル空間上で意味の近い商品を検索する"""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        matched_items = []
        if results and results["documents"] and results["distances"]:
            for doc, distance in zip(results["documents"][0], results["distances"][0]):
                matched_items.append({"item_name": doc, "distance": float(distance)})
        return matched_items
