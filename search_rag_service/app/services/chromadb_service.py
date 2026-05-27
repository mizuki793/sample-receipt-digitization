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
        
        # コレクションを取得または作成（埋め込み関数をGeminiに差し替え）
        self.collection = self.chroma_client.get_or_create_collection(
            name="receipt_items",
            embedding_function=self.embedding_fn
        )
        
        # キャッシュ辞書
        self._embedding_cache = {}

    def store_item(self, item_name: str, job_id: str):
        """商品名をGeminiでベクトル化してChromaに永続化保存する"""
        self.collection.add(
            documents=[item_name],
            metadatas=[{"job_id": job_id}],
            ids=[item_name]
        )

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
