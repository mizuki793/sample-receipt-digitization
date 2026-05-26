from enum import Enum

class JobStatus(str, Enum):
    PROCESSING = "processing"
    NEEDS_CORRECTION = "needs_correction"
    FAILED = "failed"
    SUCCESS = "success"
