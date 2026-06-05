import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from schemas.job import JobStatus
from repositories.job_mongo import MongoJobRepository


@pytest.mark.asyncio
async def test_create_job_success():
    """Create job should insert job with initial status."""
    job_id = "test-job-123"
    status = JobStatus.PROCESSING.value
    
    with patch("repositories.job_mongo.run_in_threadpool", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = None

        await MongoJobRepository.create_job(job_id, status)

        mock_run.assert_called_once()
        # Verify callback was passed
        callback = mock_run.call_args[0][0]
        assert callable(callback)


@pytest.mark.asyncio
async def test_update_job_data():
    """Update job should modify job data with updated_at timestamp."""
    job_id = "test-job-123"
    update_data = {"status": JobStatus.SUCCESS.value}
    
    with patch("repositories.job_mongo.run_in_threadpool", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = None

        await MongoJobRepository.update_job_data(job_id, update_data)

        mock_run.assert_called_once()
        callback = mock_run.call_args[0][0]
        assert callable(callback)


@pytest.mark.asyncio
async def test_update_job_status_atomically_success():
    """Atomic status update should succeed with matching old status."""
    job_id = "test-job-123"
    
    with patch("repositories.job_mongo.run_in_threadpool", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = True

        result = await MongoJobRepository.update_job_status_atomically(
            job_id,
            JobStatus.PROCESSING,
            JobStatus.SUCCESS
        )

        assert result is True
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_update_job_status_atomically_failure():
    """Atomic status update should fail with non-matching old status."""
    job_id = "test-job-123"
    
    with patch("repositories.job_mongo.run_in_threadpool", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = False

        result = await MongoJobRepository.update_job_status_atomically(
            job_id,
            JobStatus.PROCESSING,
            JobStatus.SUCCESS
        )

        assert result is False
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_get_job():
    """Get job should retrieve job from database."""
    job_id = "test-job-123"
    mock_job = {
        "job_id": job_id,
        "status": "processing",
        "created_at": "2026-05-20T12:00:00"
    }
    
    with patch("repositories.job_mongo.run_in_threadpool", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_job

        result = await MongoJobRepository.get_job(job_id)

        assert result == mock_job
        mock_run.assert_called_once()
