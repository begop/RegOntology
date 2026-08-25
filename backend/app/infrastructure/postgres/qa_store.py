from __future__ import annotations

import hashlib
from typing import Literal, cast

from sqlalchemy import Engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.errors import ConfigurationError
from app.domain.models import Citation, QAResult, StoredQAResult
from app.infrastructure.postgres.models import (
    ProvisionRow,
    QACitationRow,
    QARunRow,
    RegulationDocumentRow,
    RegulationVersionRow,
)

QAStatus = Literal["answered", "partially_answered", "abstained"]


class PostgresQAResultStore:
    """Canonical QA result storage shared by every API instance."""

    def __init__(self, engine: Engine):
        self._engine = engine

    def save(
        self,
        result: QAResult,
        *,
        owner_subject: str,
        request_id: str,
        question_sha256: str,
    ) -> None:
        publication_id = result.trace.get("publication_id")
        if not isinstance(publication_id, str) or not publication_id:
            raise ConfigurationError("QA result is missing its publication provenance.")
        try:
            with Session(self._engine) as session, session.begin():
                session.add(
                    QARunRow(
                        id=result.query_id,
                        owner_subject=owner_subject,
                        request_id=request_id,
                        question_sha256=question_sha256,
                        as_of=result.as_of,
                        status=result.status,
                        answer=result.answer,
                        warnings=list(result.warnings),
                        reason_code=result.reason_code,
                        suggested_actions=list(result.suggested_actions),
                        trace_summary=result.trace,
                        publication_id=publication_id,
                    )
                )
                session.add_all(
                    [
                        QACitationRow(
                            qa_run_id=result.query_id,
                            citation_index=citation.index,
                            source_id=citation.source_id,
                            document_id=citation.document_id,
                            version_id=citation.version_id,
                            provision_id=citation.provision_id,
                            quote_sha256=hashlib.sha256(citation.quote.encode("utf-8")).hexdigest(),
                        )
                        for citation in result.citations
                    ]
                )
        except SQLAlchemyError as exc:
            raise ConfigurationError("QA result could not be persisted.") from exc

    def get(self, query_id: str) -> StoredQAResult | None:
        try:
            with Session(self._engine) as session:
                row = session.get(QARunRow, query_id)
                if row is None:
                    return None
                citation_rows = session.scalars(
                    select(QACitationRow)
                    .where(QACitationRow.qa_run_id == query_id)
                    .order_by(QACitationRow.citation_index)
                ).all()
                citations = tuple(
                    self._citation_from_row(session, citation) for citation in citation_rows
                )
        except SQLAlchemyError as exc:
            raise ConfigurationError("QA result could not be loaded.") from exc
        return StoredQAResult(
            result=QAResult(
                query_id=row.id,
                status=cast(QAStatus, row.status),
                answer=row.answer,
                as_of=row.as_of,
                citations=citations,
                warnings=tuple(row.warnings),
                reason_code=row.reason_code,
                suggested_actions=tuple(row.suggested_actions),
                trace=row.trace_summary,
            ),
            owner_subject=row.owner_subject,
        )

    @staticmethod
    def _citation_from_row(session: Session, row: QACitationRow) -> Citation:
        document = session.get(RegulationDocumentRow, row.document_id)
        version = session.get(RegulationVersionRow, row.version_id)
        provision = session.get(ProvisionRow, row.provision_id)
        if document is None or version is None or provision is None:
            raise ConfigurationError("A persisted QA citation has missing canonical source rows.")
        if (
            provision.document_id != row.document_id
            or provision.version_id != row.version_id
            or version.document_id != row.document_id
            or hashlib.sha256(provision.body.encode("utf-8")).hexdigest() != row.quote_sha256
        ):
            raise ConfigurationError("A persisted QA citation failed its integrity check.")
        return Citation(
            index=row.citation_index,
            source_id=row.source_id,
            document_id=row.document_id,
            version_id=row.version_id,
            provision_id=row.provision_id,
            document_title=document.title,
            version_label=version.version_label,
            locator=provision.locator,
            quote=provision.body,
        )
