def test_create_embeddings_bulk_endpoint(test_client):
    response = test_client.post(
        "/v1/embeddings",
        json={
            "job_id": "job-1",
            "store_name": "Test Shop",
            "items": [{"item_name": "牛乳", "unit_price": 150}],
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "success"


def test_search_endpoint_returns_query_and_matches(test_client):
    response = test_client.post(
        "/v1/search",
        json={"query": "牛乳", "n_results": 2},
    )

    assert response.status_code == 200
    assert response.json()["query"] == "牛乳"
    assert len(response.json()["matches"]) == 2


def test_chat_stream_endpoint_returns_done_marker(test_client):
    response = test_client.post(
        "/v1/chat/stream",
        json={"message": "hello"},
    )

    assert response.status_code == 200
    assert "data: [DONE]" in response.text


def test_chat_stream_endpoint_rejects_empty_message(test_client):
    response = test_client.post(
        "/v1/chat/stream",
        json={"message": " "},
    )

    assert response.status_code == 400
    assert "Message cannot be empty" in response.json()["detail"]
