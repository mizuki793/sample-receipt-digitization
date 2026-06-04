from unittest.mock import MagicMock, patch

from infrastructure.gemini_embedding import GeminiEmbeddingFunction


class FakeEmbedding:
    def __init__(self, values):
        self.values = values


class FakeEmbedResponse:
    def __init__(self, embeddings):
        self.embeddings = embeddings


def test_gemini_embedding_function_returns_embeddings():
    fake_response = FakeEmbedResponse([FakeEmbedding([0.1, 0.2, 0.3])])
    fake_client = MagicMock()
    fake_client.models.embed_content.return_value = fake_response

    with patch("infrastructure.gemini_embedding.genai.Client", return_value=fake_client):
        embedding_fn = GeminiEmbeddingFunction(api_key="dummy-key", model_name="dummy-model")

        document_embeddings = embedding_fn.embed_documents(["hello world"])
        assert isinstance(document_embeddings, list)
        assert len(document_embeddings) == 1
        assert document_embeddings[0] == [0.1, 0.2, 0.3]

        query_embedding = embedding_fn.embed_query("hello")
        assert query_embedding == [0.1, 0.2, 0.3]

        query_embedding_with_input = embedding_fn.embed_query(input="hello")
        assert query_embedding_with_input == [0.1, 0.2, 0.3]

        fake_client.models.embed_content.assert_any_call(
            model="dummy-model",
            contents=["hello world"],
        )
        fake_client.models.embed_content.assert_any_call(
            model="dummy-model",
            contents=["hello"],
        )
