from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal


class SecurityClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class ProvisionLevel(StrEnum):
    CHAPTER = "chapter"
    ARTICLE = "article"
    PARAGRAPH = "paragraph"


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    role: str
    allowed_security_classes: frozenset[SecurityClass]
    allowed_document_ids: frozenset[str] | None = None

    def can_read(self, document_id: str, security_class: SecurityClass) -> bool:
        if security_class not in self.allowed_security_classes:
            return False
        return self.allowed_document_ids is None or document_id in self.allowed_document_ids


@dataclass(frozen=True, slots=True)
class RegulationDocument:
    id: str
    document_code: str
    title: str
    institution: str
    document_type: str
    owner_org: str
    security_class: SecurityClass
    status: str
    is_mock: bool


@dataclass(frozen=True, slots=True)
class RegulationVersion:
    id: str
    document_id: str
    version_label: str
    promulgated_on: date | None
    effective_from: date
    effective_to: date | None
    status: str
    supersedes_version_id: str | None
    source_sha256: str
    source_name: str
    is_mock: bool

    def is_effective(self, as_of: date) -> bool:
        return (
            self.status == "published"
            and self.effective_from <= as_of
            and (self.effective_to is None or as_of < self.effective_to)
        )


@dataclass(frozen=True, slots=True)
class Provision:
    id: str
    document_id: str
    version_id: str
    parent_id: str | None
    level: ProvisionLevel
    ordinal: int
    canonical_path: str
    locator: str
    title: str | None
    body: str
    body_sha256: str
    source_line: int
    security_class: SecurityClass
    is_mock: bool


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    publication_id: str
    graph_watermark: str
    loaded_at: datetime
    documents: dict[str, RegulationDocument]
    versions: dict[str, RegulationVersion]
    versions_by_document: dict[str, tuple[str, ...]]
    provisions: dict[str, Provision]
    provisions_by_version: dict[str, tuple[str, ...]]
    ontology_nodes: dict[str, OntologyNode]
    ontology_edges: tuple[OntologyEdge, ...]


@dataclass(frozen=True, slots=True)
class OntologyNode:
    id: str
    type: str
    label: str
    security_class: SecurityClass
    properties: dict[str, Any] = field(default_factory=dict)
    source_document_ids: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class OntologyEdge:
    id: str
    type: str
    source: str
    target: str
    source_document: str
    source_locator: str
    review_status: str


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    provision: Provision
    document: RegulationDocument
    version: RegulationVersion
    score: float
    lane_scores: dict[str, float]


@dataclass(frozen=True, slots=True)
class GeneratedClaim:
    text: str
    citation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    claims: tuple[GeneratedClaim, ...]
    summary: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Citation:
    index: int
    source_id: str
    document_id: str
    version_id: str
    provision_id: str
    document_title: str
    version_label: str
    locator: str
    quote: str


@dataclass(frozen=True, slots=True)
class QAResult:
    query_id: str
    status: Literal["answered", "partially_answered", "abstained"]
    answer: str | None
    as_of: date
    citations: tuple[Citation, ...]
    warnings: tuple[str, ...]
    reason_code: str | None
    suggested_actions: tuple[str, ...]
    trace: dict[str, Any]


@dataclass(frozen=True, slots=True)
class StoredQAResult:
    result: QAResult
    owner_subject: str


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: str
    occurred_at: datetime
    actor_subject: str
    action: str
    target_type: str
    target_id: str
    request_id: str
    outcome: str
    metadata: dict[str, Any]
    previous_hash: str | None
    event_hash: str
