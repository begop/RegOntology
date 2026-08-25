from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any, Protocol

from app.domain.graph import GraphProjectionStatus
from app.domain.models import (
    AuditEvent,
    GeneratedAnswer,
    KnowledgeSnapshot,
    Principal,
    Provision,
    QAResult,
    RegulationVersion,
    RetrievalHit,
    StoredQAResult,
)


class KnowledgeRepository(Protocol):
    @property
    def snapshot(self) -> KnowledgeSnapshot: ...

    @property
    def mode(self) -> str: ...

    def reload(self) -> KnowledgeSnapshot: ...

    def healthcheck(self) -> bool: ...

    def versions_for_document(self, document_id: str) -> tuple[RegulationVersion, ...]: ...

    def effective_version(self, document_id: str, as_of: date) -> RegulationVersion | None: ...

    def active_provisions(
        self,
        as_of: date,
        principal: Principal,
        document_ids: frozenset[str] | None = None,
    ) -> tuple[Provision, ...]: ...

    def find_article_paragraphs(
        self, document_id: str, article_number: int, as_of: date, principal: Principal
    ) -> tuple[Provision, ...]: ...


class EmbeddingProvider(Protocol):
    @property
    def profile_id(self) -> str: ...

    def embed(self, text: str) -> tuple[float, ...]: ...


class GenerationProvider(Protocol):
    @property
    def model_id(self) -> str: ...

    def generate(self, question: str, contexts: Sequence[RetrievalHit]) -> GeneratedAnswer: ...


class GraphQuery(Protocol):
    def status(self, expected_publication_id: str) -> GraphProjectionStatus: ...

    def one_hop(
        self,
        *,
        publication_id: str,
        seed_ids: tuple[str, ...],
        allowed_node_ids: tuple[str, ...],
        allowed_edge_ids: tuple[str, ...],
        allowed_document_ids: tuple[str, ...],
        relation_types: tuple[str, ...],
        max_edges: int,
    ) -> tuple[Mapping[str, object], ...]: ...


class GraphProjection(GraphQuery, Protocol):
    def healthcheck(self) -> bool: ...

    def replace_projection(self, snapshot: KnowledgeSnapshot) -> dict[str, Any]: ...

    def close(self) -> None: ...


class AuditLog(Protocol):
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
    ) -> AuditEvent: ...

    def list(self, limit: int = 100) -> tuple[AuditEvent, ...]: ...

    def verify_chain(self) -> bool: ...


class QAResultStore(Protocol):
    def save(
        self,
        result: QAResult,
        *,
        owner_subject: str,
        request_id: str,
        question_sha256: str,
    ) -> None: ...

    def get(self, query_id: str) -> StoredQAResult | None: ...
