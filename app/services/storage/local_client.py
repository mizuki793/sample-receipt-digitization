import json
import aiofiles
from pathlib import Path
from app.core.config import settings

class LocalStorageClient():
    def __init__(self):
        self.base_dir = Path(settings.LOCAL_DATA_SET_BASE_DIR)

    async def put_object(self, partition_key: str, file_name: str, data: dict) -> str:
        target_dir = self.base_dir / partition_key
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_file_path = target_dir / file_name
        
        async with aiofiles.open(target_file_path, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            
        return str(target_file_path)
