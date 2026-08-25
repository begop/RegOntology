from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class VersionSummary(StrictModel):
    version_id: str
    version_label: str
    promulgated_on: date | None
    effective_from: date
    effective_to: date | None
    status: str
    supersedes_version_id: str | None
    source_sha256: str
    is_mock: bool


class RegulationListItem(StrictModel):
    document_id: str
    document_code: str
    title: str
    document_type: str
    owner_org: str
    security_class: str
    status: str
    is_mock: bool
    effective_version: VersionSummary
    match_snippets: list[str]


class RegulationListResponse(StrictModel):
    items: list[RegulationListItem]
    total: int
    next_cursor: str | None = None
    as_of: date


class RegulationDetail(StrictModel):
    document_id: str
    document_code: str
    title: str
    institution: str
    document_type: str
    owner_org: str
    security_class: str
    status: str
    is_mock: bool
    versions: list[VersionSummary]


class ProvisionResponse(StrictModel):
    provision_id: str
    document_id: str
    version_id: str
    parent_id: str | None
    level: str
    ordinal: int
    canonical_path: str
    locator: str
    title: str | None
    body: str
    body_sha256: str
    source_span: dict[str, int]
    is_mock: bool


class VersionDetail(VersionSummary):
    document_id: str
    toc: list[ProvisionResponse]


class ProvisionDetail(ProvisionResponse):
    breadcrumb: list[dict[str, str]]
    document_title: str
    version_label: str
    effective_from: date
    effective_to: date | None


class ProvisionListResponse(StrictModel):
    items: list[ProvisionResponse]
    next_cursor: str | None = None


class QAScope(StrictModel):
    document_ids: list[str] = Field(default_factory=list, max_length=100)
    owner_org_ids: list[str] = Field(default_factory=list, max_length=100)


class QAQueryRequest(StrictModel):
    question: str = Field(min_length=2, max_length=2_000)
    as_of: date | None = None
    scope: QAScope = Field(default_factory=QAScope)
    conversation_id: str | None = None
    stream: bool = False


class CitationResponse(StrictModel):
    index: int
    source_id: str
    document_id: str
    version_id: str
    provision_id: str
    document_title: str
    version_label: str
    locator: str
    quote: str


class QAResponse(StrictModel):
    query_id: str
    status: Literal["answered", "partially_answered", "abstained"]
    answer: str | None
    as_of: date
    citations: list[CitationResponse]
    warnings: list[str]
    reason_code: str | None
    suggested_actions: list[str]
    trace: dict[str, Any]


class OntologyNodeResponse(StrictModel):
    id: str
    type: str
    label: str
    security_class: str
    properties: dict[str, Any]
    source_document_ids: list[str]


class OntologyEdgeResponse(StrictModel):
    id: str
    type: str
    source: str
    target: str
    source_document: str
    source_locator: str
    review_status: str


class OntologySearchResponse(StrictModel):
    items: list[OntologyNodeResponse]


class OntologySubgraphResponse(StrictModel):
    nodes: list[OntologyNodeResponse]
    edges: list[OntologyEdgeResponse]
    truncated: bool
    expansion_cursor: str | None
    publication_id: str
    graph_watermark: str
    graph_status: Literal["healthy", "stale", "unavailable"]


class AuditEventResponse(StrictModel):
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


class AuditListResponse(StrictModel):
    items: list[AuditEventResponse]
    chain_valid: bool


class ReloadResponse(StrictModel):
    publication_id: str
    document_count: int
    version_count: int
    provision_count: int
    ontology_node_count: int
    ontology_edge_count: int


class HealthResponse(StrictModel):
    status: Literal["ok", "ready", "degraded"]
    service: str
    mode: str
    publication_id: str
    graph_status: Literal["healthy", "stale", "unavailable"]
    graph_publication_id: str | None


class SystemStatusResponse(StrictModel):
    status: Literal["healthy", "degraded"]
    repository_mode: str
    ai_provider: str
    graph_mode: str
    auth_mode: str
    publication_id: str
    graph_watermark: str
    graph_status: Literal["healthy", "stale", "unavailable"]
    graph_publication_id: str | None
    loaded_at: datetime
    warnings: list[str]
