from datetime import UTC, datetime
from uuid import uuid4


class SystemClock:
    def __call__(self) -> datetime:
        return datetime.now(UTC)


class UuidProcessingRunIdGenerator:
    def __call__(self) -> str:
        return str(uuid4())
