import json
import pytest
from unittest.mock import AsyncMock, patch
from schemas.job import JobStatus
from services.receipt_job_service import ReceiptJobService


@pytest.mark.asyncio
async def test_fetch_job_status_processing():
    job_id = "test-job-123"

    with patch("services.receipt_job_service.MongoJobRepository.get_job", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "_id": "test-id",
            "status": "processing",
            "created_at": "2026-05-20T12:00:00",
        }

        result = await ReceiptJobService.fetch_job_status(job_id)

        assert result is not None
        assert result["status"] == "processing"
        mock_get.assert_called_once_with(job_id)


@pytest.mark.asyncio
async def test_fetch_job_status_not_found():
    job_id = "nonexistent-job"

    with patch("services.receipt_job_service.MongoJobRepository.get_job", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        result = await ReceiptJobService.fetch_job_status(job_id)

        assert result is None


@pytest.mark.asyncio
async def test_fetch_job_status_success_loads_file(tmp_path):
    job_id = "success-job"
    data_dir = tmp_path / "data"
    tmp_dir = data_dir / "tmp"
    tmp_dir.mkdir(parents=True)

    file_data = {"store_name": "テスト店舗", "items": []}
    file_path = tmp_dir / f"{job_id}.json"
    file_path.write_text(json.dumps(file_data), encoding="utf-8")

    with patch("services.receipt_job_service.MongoJobRepository.get_job", new_callable=AsyncMock) as mock_get, \
         patch("services.receipt_job_service.settings.LOCAL_DATA_SET_BASE_DIR", str(data_dir)):
        mock_get.return_value = {"status": "success"}

        result = await ReceiptJobService.fetch_job_status(job_id)

        assert result is not None
        assert result["store_name"] == "テスト店舗"
        assert result["status"] == "success"


@pytest.mark.asyncio
async def test_lock_receipt_job_transitions_to_locked():
    job_id = "lock-job"

    with patch("services.receipt_job_service.MongoJobRepository.get_job", new_callable=AsyncMock) as mock_get, \
         patch("services.receipt_job_service.MongoJobRepository.update_job_status_atomically", new_callable=AsyncMock) as mock_atomic_update:
        mock_get.return_value = {"status": JobStatus.SUCCESS.value}
        mock_atomic_update.return_value = True

        result = await ReceiptJobService.lock_receipt_job(job_id)

        assert result["status"] == JobStatus.LOCKED.value
        assert result["job_id"] == job_id
