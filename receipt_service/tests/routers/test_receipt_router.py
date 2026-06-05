from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


def test_health_endpoint_returns_ok():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("routers.receipt_router.init_receipt_pipeline", new_callable=AsyncMock)
@patch("routers.receipt_router.analysis_task", new_callable=AsyncMock)
def test_receipt_upload_endpoint_accepts_valid_image(mock_analysis_task, mock_init_pipeline):
    mock_init_pipeline.return_value = "/tmp/fake.jpg"
    mock_analysis_task.return_value = None

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/receipt/upload",
            files={"file": ("receipt.jpg", BytesIO(b"fakeimage"), "image/jpeg")},
        )

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)
    assert len(data["job_id"]) > 0


def test_receipt_upload_endpoint_rejects_invalid_file():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/receipt/upload",
            files={"file": ("receipt.txt", BytesIO(b"notanimage"), "text/plain")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only JPG or JPEG, PNG files are allowed."


@patch("routers.receipt_router.view_job_ids_by_status", new_callable=AsyncMock)
def test_get_job_ids_by_status_returns_list(mock_view_job_ids):
    mock_view_job_ids.return_value = ["job-a", "job-b"]

    with TestClient(app) as client:
        response = client.get("/api/v1/receipt/jobs/processing")

    assert response.status_code == 200
    assert response.json() == ["job-a", "job-b"]


@patch("routers.receipt_router.view_receipt_status", new_callable=AsyncMock)
def test_get_job_detail_returns_job_data(mock_view_receipt_status):
    mock_view_receipt_status.return_value = {"job_id": "job-a", "status": "processing"}

    with TestClient(app) as client:
        response = client.get("/api/v1/receipt/jobs/detail/job-a")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-a"


@patch("routers.receipt_router.view_receipt_status", new_callable=AsyncMock)
def test_get_job_detail_returns_404_for_missing_job(mock_view_receipt_status):
    mock_view_receipt_status.return_value = None

    with TestClient(app) as client:
        response = client.get("/api/v1/receipt/jobs/detail/missing")

    assert response.status_code == 404
    assert "見つかりませんでした" in response.json()["detail"]


@patch("routers.receipt_router.lock_receipt_job", new_callable=AsyncMock)
def test_lock_job_status_success(mock_lock_job):
    mock_lock_job.return_value = {"job_id": "job-a", "status": "locked"}

    with TestClient(app) as client:
        response = client.post("/api/v1/receipt/jobs/job-a/lock")

    assert response.status_code == 200
    assert response.json()["status"] == "locked"


@patch("routers.receipt_router.lock_receipt_job", new_callable=AsyncMock)
def test_lock_job_status_returns_404_for_missing_job(mock_lock_job):
    mock_lock_job.return_value = None

    with TestClient(app) as client:
        response = client.post("/api/v1/receipt/jobs/job-a/lock")

    assert response.status_code == 404


@patch("routers.receipt_router.fix_receipt_job_data", new_callable=AsyncMock)
def test_update_job_detail_success(mock_fix_job):
    mock_fix_job.return_value = {"job_id": "job-a", "status": "success", "message": "レシートデータが正常に修正されました。"}

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/receipt/jobs/job-a/fix",
            json={"raw_ocr_text": "raw text", "fixed_data": {"store_name": "shop", "transaction_date": "2026-05-20T12:00:00", "items": [], "total_amount": 0, "tax": 0, "needs_correction": False}},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


@patch("routers.receipt_router.fix_receipt_job_data", new_callable=AsyncMock)
def test_update_job_detail_returns_404_for_missing_job(mock_fix_job):
    mock_fix_job.return_value = None

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/receipt/jobs/job-a/fix",
            json={"raw_ocr_text": "raw text", "fixed_data": {"store_name": "shop", "transaction_date": "2026-05-20T12:00:00", "items": [], "total_amount": 0, "tax": 0, "needs_correction": False}},
        )

    assert response.status_code == 404


@patch("routers.receipt_router.fix_receipt_job_data", new_callable=AsyncMock)
def test_update_job_detail_returns_400_for_non_editable_job(mock_fix_job):
    mock_fix_job.return_value = {"job_id": "job-a", "status": "processing", "message": "処理フラグがされていないjob_idのため編集不可: job-a"}

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/receipt/jobs/job-a/fix",
            json={"raw_ocr_text": "raw text", "fixed_data": {"store_name": "shop", "transaction_date": "2026-05-20T12:00:00", "items": [], "total_amount": 0, "tax": 0, "needs_correction": False}},
        )

    assert response.status_code == 400


@patch("routers.receipt_router.ReceiptSearchService.search_item_stats", new_callable=AsyncMock)
def test_search_receipt_stats_endpoint(mock_search_stats):
    mock_search_stats.return_value = {"query": "牛乳", "store_stats": [], "time_zone_stats": []}

    with TestClient(app) as client:
        response = client.post("/api/v1/receipts/search", json={"query": "牛乳"})

    assert response.status_code == 200
    assert response.json()["query"] == "牛乳"
