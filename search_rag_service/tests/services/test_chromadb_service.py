import pytest
from unittest.mock import MagicMock, patch

from services.chromadb_service import (
    ChromaVectorStore, 
    GeminiEmbeddingFunction,
    create_chroma_vector_store
)

class FakeEmbedding:
    def __init__(self, values):
        self.values = values


class FakeEmbedResponse:
    def __init__(self, embeddings):
        self.embeddings = embeddings


class FakeCollection:
    def __init__(self):
        self.add_calls = []

    def add(self, documents, metadatas, ids):
        self.add_calls.append({
            "documents": documents,
            "metadatas": metadatas,
            "ids": ids,
        })

    def query(self, query_texts, n_results):
        return {
            "documents": [["dummy-result"] * n_results],
            "distances": [[0.1] * n_results],
        }


class FakeChromaClient:
    def __init__(self):
        self.collections = {}
        self.persist_called = False
        self.close_called = False

    def get_or_create_collection(self, name, embedding_function):
        collection = FakeCollection()
        self.collections[name] = {
            "collection": collection,
            "embedding_function": embedding_function,
        }
        return collection

    def persist(self):
        self.persist_called = True

    def close(self):
        self.close_called = True


class FakeGenaiClient:
    def __init__(self, response):
        self.models = MagicMock(embed_content=MagicMock(return_value=response))


def test_embedding_function_uses_genai_client():
    fake_response = FakeEmbedResponse([FakeEmbedding([0.1, 0.2, 0.3])])
    fake_genai_client = FakeGenaiClient(fake_response)

    with patch("infrastructure.gemini_embedding.genai.Client", return_value=fake_genai_client) as mocked_client:
        embedding_fn = GeminiEmbeddingFunction(api_key="dummy-key", model_name="dummy-model")

        document_embeddings = embedding_fn.embed_documents(["テスト商品説明"])
        assert isinstance(document_embeddings, list)
        assert len(document_embeddings) == 1
        assert isinstance(document_embeddings[0], list)
        assert document_embeddings[0] == [0.1, 0.2, 0.3]

        query_embedding = embedding_fn.embed_query("テストクエリ")
        assert isinstance(query_embedding, list)
        assert len(query_embedding) == 3
        assert query_embedding == [0.1, 0.2, 0.3]

        mocked_client.assert_called_once_with(api_key="dummy-key")
        fake_genai_client.models.embed_content.assert_any_call(
            model="dummy-model",
            contents=["テスト商品説明"],
        )
        fake_genai_client.models.embed_content.assert_any_call(
            model="dummy-model",
            contents=["テストクエリ"],
        )


def test_create_chroma_vector_store_and_store_bulk_items(monkeypatch):
    fake_client = FakeChromaClient()
    fake_response = FakeEmbedResponse([FakeEmbedding([0.1, 0.2, 0.3])])
    fake_genai_client = FakeGenaiClient(fake_response)

    monkeypatch.setattr("infrastructure.chroma_vector_store.chromadb.PersistentClient", lambda path: fake_client)
    monkeypatch.setattr("infrastructure.gemini_embedding.genai.Client", lambda api_key: fake_genai_client)

    class DummySettings:
        CHROMA_DATA_DIR = "/tmp/chroma"
        GEMINI_API_KEY = "dummy-key"
        EMBEDDING_MODEL_NAME = "dummy-model"
        CHROMA_COLLECTION_NAME = "test_collection"

    monkeypatch.setattr("infrastructure.chroma_vector_store.settings", DummySettings)

    vector_store = create_chroma_vector_store()
    assert isinstance(vector_store, ChromaVectorStore)

    items = [
        {"item_name": "牛乳", "unit_price": 150, "category": "食品"},
        {"item_name": "パン", "unit_price": 120},
    ]

    registered_count = vector_store.store_bulk_items(
        job_id="test-job",
        store_name="テスト店舗",
        items=items,
    )

    assert registered_count == 5
    fake_collection = fake_client.collections[DummySettings.CHROMA_COLLECTION_NAME]["collection"]
    assert len(fake_collection.add_calls) == 5
    assert fake_collection.add_calls[0]["ids"] == ["test-job_item0_pat0"]
    assert fake_collection.add_calls[-1]["ids"] == ["test-job_item1_pat1"]

    # Collection returned by create_chroma_vector_store must be the same object used by the service.
    assert vector_store.collection is fake_collection
