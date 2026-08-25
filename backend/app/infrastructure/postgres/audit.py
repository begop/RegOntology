from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.domain.models import AuditEvent
from app.infrastructure.postgres.models import AuditEventRow


class PostgresAppendOnlyAuditLog:
    def __init__(self, engine: Engine):
        self._engine = engine

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
        with Session(self._engine) as session, session.begin():
            session.execute(text("SELECT pg_advisory_xact_lock(hashtext('regontology_audit'))"))
            previous = session.scalar(
                select(AuditEventRow).order_by(AuditEventRow.occurred_at.desc()).limit(1)
            )
            previous_hash = previous.event_hash if previous else None
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
            event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            session.add(
                AuditEventRow(
                    id=event_id,
                    occurred_at=occurred_at,
                    actor_subject=actor_subject,
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    request_id=request_id,
                    outcome=outcome,
                    metadata_json=safe_metadata,
                    previous_hash=previous_hash,
                    event_hash=event_hash,
                )
            )
        return AuditEvent(
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
            event_hash=event_hash,
        )

    def list(self, limit: int = 100) -> tuple[AuditEvent, ...]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(AuditEventRow).order_by(AuditEventRow.occurred_at.desc()).limit(limit)
            ).all()
        return tuple(
            AuditEvent(
                id=row.id,
                occurred_at=row.occurred_at,
                actor_subject=row.actor_subject,
                action=row.action,
                target_type=row.target_type,
                target_id=row.target_id,
                request_id=row.request_id,
                outcome=row.outcome,
                metadata=row.metadata_json,
                previous_hash=row.previous_hash,
                event_hash=row.event_hash,
            )
            for row in rows
        )

    def verify_chain(self) -> bool:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(AuditEventRow).order_by(AuditEventRow.occurred_at.asc())
            ).all()
        previous_hash: str | None = None
        for row in rows:
            if row.previous_hash != previous_hash:
                return False
            previous_hash = row.event_hash
        return True
