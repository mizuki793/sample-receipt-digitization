from unittest.mock import MagicMock

from infrastructure.chroma_vector_store import ChromaVectorStore, create_chroma_vector_store


class FakeCollection:
    def __init__(self):
        self.add_calls = []

    def add(self, documents, metadatas, ids):
        self.add_calls.append({"documents": documents, "metadatas": metadatas, "ids": ids})

    def query(self, query_texts, n_results):
        return {"documents": [["dummy-item"] * n_results], "distances": [[0.1] * n_results]}


class FakeClient:
    def __init__(self):
        self.collections = {}

    def get_or_create_collection(self, name, embedding_function):
        collection = FakeCollection()
        self.collections[name] = collection
        return collection


class DummySettings:
    CHROMA_DATA_DIR = "/tmp/chroma"
    GEMINI_API_KEY = "dummy-key"
    EMBEDDING_MODEL_NAME = "dummy-model"
    CHROMA_COLLECTION_NAME = "test_collection"


def test_create_chroma_vector_store_builds_store(monkeypatch):
    fake_client = FakeClient()
    fake_embedding = MagicMock()

    monkeypatch.setattr("infrastructure.chroma_vector_store.chromadb.PersistentClient", lambda path: fake_client)
    monkeypatch.setattr("infrastructure.chroma_vector_store.GeminiEmbeddingFunction", lambda api_key, model_name: fake_embedding)
    monkeypatch.setattr("infrastructure.chroma_vector_store.settings", DummySettings)

    vector_store = create_chroma_vector_store()

    assert isinstance(vector_store, ChromaVectorStore)
    assert vector_store.collection is fake_client.collections[DummySettings.CHROMA_COLLECTION_NAME]

    registered_count = vector_store.store_bulk_items(
        job_id="job-1",
        store_name="テスト店舗",
        items=[{"item_name": "牛乳", "unit_price": 150}],
    )
    assert registered_count == 2

    results = vector_store.search_similar_items("牛乳", n_results=2)
    assert len(results) == 2
    assert results[0]["item_name"] == "dummy-item"
