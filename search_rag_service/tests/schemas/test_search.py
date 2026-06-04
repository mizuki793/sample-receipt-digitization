import pytest
from pydantic import ValidationError

from schemas.search import BulkEmbedRequest, DiscoveredItem, SearchQueryRequest


def test_bulk_embed_request_accepts_valid_items():
    payload = BulkEmbedRequest(
        job_id="job-1",
        store_name="Test Store",
        items=[DiscoveredItem(item_name="牛乳", unit_price=150)],
    )

    assert payload.job_id == "job-1"
    assert payload.items[0].item_name == "牛乳"


def test_search_query_request_uses_default_n_results():
    payload = SearchQueryRequest(query="牛乳")

    assert payload.n_results == 3


def test_search_query_request_rejects_empty_query():
    with pytest.raises(ValidationError):
        SearchQueryRequest(query="")
