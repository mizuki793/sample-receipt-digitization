# app/services/storage/s3_client.py
import json
import aioboto3
from app.core.config import settings

class S3StorageClient():
    def __init__(self):
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.prefix = settings.AWS_S3_PREFIX
        self.session = aioboto3.Session()

    async def put_object(self, partition_key: str, file_name: str, data: dict) -> str:
        # S3に入れることは現時点では考えていないため、枠だけを作成
        return "s3://"
