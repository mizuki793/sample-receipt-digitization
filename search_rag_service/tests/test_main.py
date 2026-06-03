# from fastapi.testclient import TestClient
# from main import app
# from core.dependencies import get_vector_store, get_agent
# from search_rag_service.tests.test_conftest import FakeVectorStore

# class FakeAgent:
#     async def stream_agent_response(self, user_query: str):
#         yield f"data: fake response for {user_query}\n\n"
#         yield "data: [DONE]\n\n"


# def test_search_items_with_dependency_override():
#     fake_store = FakeVectorStore()
#     app.dependency_overrides[get_vector_store] = lambda request: fake_store

#     with TestClient(app) as client:
#         response = client.post("/v1/search", json={"query": "牛乳", "n_results": 2})
#         assert response.status_code == 200
#         assert response.json() == {
#             "query": "牛乳",
#             "matches": [
#                 {"item_name": "fake-result:牛乳", "distance": 0.1234},
#                 {"item_name": "fake-result:牛乳", "distance": 0.1234}
#             ]
#         }

#     app.dependency_overrides.clear()


# def test_create_embeddings_bulk_with_fake_vector_store():
#     fake_store = FakeVectorStore()
#     app.dependency_overrides[get_vector_store] = lambda request: fake_store

#     with TestClient(app) as client:
#         response = client.post(
#             "/v1/embeddings",
#             json={
#                 "job_id": "test-job",
#                 "store_name": "Test Shop",
#                 "items": [{"item_name": "milk", "unit_price": 150}],
#             },
#         )
#         assert response.status_code == 201
#         assert "Successfully registered" in response.json()["message"]
#         assert fake_store.stored[0]["job_id"] == "test-job"

#     app.dependency_overrides.clear()


# def test_chat_stream_with_fake_agent_override():
#     app.dependency_overrides[get_agent] = lambda request: FakeAgent()

#     with TestClient(app) as client:
#         response = client.post("/v1/chat/stream", json={"message": "hello"})
#         assert response.status_code == 200
#         assert response.text.strip().endswith("data: [DONE]")

#     app.dependency_overrides.clear()
