from __future__ import annotations

import threading

from app.domain.models import QAResult, StoredQAResult


class InMemoryQAResultStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, StoredQAResult] = {}

    def save(
        self,
        result: QAResult,
        *,
        owner_subject: str,
        request_id: str,
        question_sha256: str,
    ) -> None:
        del request_id, question_sha256
        with self._lock:
            self._records[result.query_id] = StoredQAResult(
                result=result,
                owner_subject=owner_subject,
            )

    def get(self, query_id: str) -> StoredQAResult | None:
        with self._lock:
            return self._records.get(query_id)
