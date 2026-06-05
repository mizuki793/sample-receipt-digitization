import chromadb
from core.config import settings
from services.vector_store import BaseVectorStore
from infrastructure.gemini_embedding import GeminiEmbeddingFunction


class ChromaVectorStore(BaseVectorStore):
    def __init__(self, chroma_client, collection):
        self.chroma_client = chroma_client
        self.collection = collection
        self._embedding_cache = {}

    def store_bulk_items(self, job_id: str, store_name: str, items: list[dict]) -> int:
        registered_count = 0

        for item_idx, item in enumerate(items):
            item_name = item.get("item_name")
            unit_price = item.get("unit_price")
            category = item.get("category")

            text_patterns = []
            base_text = f"店舗: {store_name} | 商品: {item_name} | 価格: {unit_price}円"
            text_patterns.append(base_text)

            search_enhancement_text = f"購入店舗: {store_name} の商品「{item_name}」"
            text_patterns.append(search_enhancement_text)

            if category:
                category_text = f"商品ジャンル: {category} | 具体的な商品名: {item_name}"
                text_patterns.append(category_text)

            for pattern_idx, text in enumerate(text_patterns):
                unique_id = f"{job_id}_item{item_idx}_pat{pattern_idx}"
                self.collection.add(
                    documents=[text],
                    metadatas=[{"job_id": job_id}],
                    ids=[unique_id],
                )
                registered_count += 1

        return registered_count

    def search_similar_items(self, query_text: str, n_results: int = 3) -> list[dict]:
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )

        matched_items = []
        if results and results.get("documents") and results.get("distances"):
            for doc, distance in zip(results["documents"][0], results["distances"][0]):
                matched_items.append({"item_name": doc, "distance": float(distance)})
        return matched_items

    def close(self) -> None:
        if hasattr(self.chroma_client, "persist"):
            self.chroma_client.persist()
        if hasattr(self.chroma_client, "close"):
            self.chroma_client.close()


def create_chroma_vector_store() -> BaseVectorStore:
    chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DATA_DIR)
    embedding_fn = GeminiEmbeddingFunction(
        api_key=settings.GEMINI_API_KEY,
        model_name=settings.EMBEDDING_MODEL_NAME,
    )
    collection = chroma_client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,
        embedding_function=embedding_fn,
    )
    return ChromaVectorStore(chroma_client=chroma_client, collection=collection)
