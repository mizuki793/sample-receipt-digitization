from app.core.config import settings
from app.services.storage.local_client import LocalStorageClient
from app.services.storage.s3_client import S3StorageClient

# 💡 戻り値の型定義（BaseStorageClient）を外し、どちらかを返すだけにする
def get_storage_client():
    if settings.STORAGE_TYPE == "S3":
        return S3StorageClient()
    return LocalStorageClient()
