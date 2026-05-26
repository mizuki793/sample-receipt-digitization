from abc import ABC, abstractmethod
from pathlib import Path
from app.core.config import settings
from app.services.storage.local_client import LocalStorageClient
from app.services.storage.s3_client import S3StorageClient

class BaseStorageClient(ABC):
    @abstractmethod
    async def put_object_json(self, partition_key: str, file_name: str, data: dict) -> str:
        pass

    @abstractmethod
    async def put_object_file(self, partition_key: str, file_name: str, data: bytes) -> str:
        pass

    @abstractmethod
    async def del_object_file(self, file_path: str, file_name: str) -> Path | str: # 戻り値の型も修正
        pass

def get_storage_client() -> BaseStorageClient: 
    if settings.STORAGE_TYPE == "S3":
        return S3StorageClient()
    return LocalStorageClient()
