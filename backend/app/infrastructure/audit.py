from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from app.domain.models import AuditEvent


class InMemoryAppendOnlyAuditLog:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[AuditEvent] = []

    def append(
        self,
        *,
        actor_subject: str,
        action: str,
        target_type: str,
        target_id: str,
        request_id: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        safe_metadata = metadata or {}
        with self._lock:
            previous_hash = self._events[-1].event_hash if self._events else None
            event_id = str(uuid.uuid4())
            occurred_at = datetime.now(UTC)
            canonical = json.dumps(
                {
                    "id": event_id,
                    "occurred_at": occurred_at.isoformat(),
                    "actor_subject": actor_subject,
                    "action": action,
                    "target_type": target_type,
                    "target_id": target_id,
                    "request_id": request_id,
                    "outcome": outcome,
                    "metadata": safe_metadata,
                    "previous_hash": previous_hash,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            event = AuditEvent(
                id=event_id,
                occurred_at=occurred_at,
                actor_subject=actor_subject,
                action=action,
                target_type=target_type,
                target_id=target_id,
                request_id=request_id,
                outcome=outcome,
                metadata=safe_metadata,
                previous_hash=previous_hash,
                event_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            )
            self._events.append(event)
            return event

    def list(self, limit: int = 100) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(reversed(self._events[-limit:]))

    def verify_chain(self) -> bool:
        with self._lock:
            previous: str | None = None
            for event in self._events:
                if event.previous_hash != previous:
                    return False
                previous = event.event_hash
            return True
