from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


JSON_VALUE = JSON().with_variant(JSONB(), "postgresql")


class RegulationDocumentRow(Base):
    __tablename__ = "regulation_document"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    document_code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    institution: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    owner_org: Mapped[str] = mapped_column(Text, nullable=False)
    security_class: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False)


class RegulationVersionRow(Base):
    __tablename__ = "regulation_version"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("regulation_document.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version_label: Mapped[str] = mapped_column(Text, nullable=False)
    promulgated_on: Mapped[date | None] = mapped_column(Date)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    supersedes_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("regulation_version.id", ondelete="RESTRICT")
    )
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ProvisionRow(Base):
    __tablename__ = "provision"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("regulation_document.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version_id: Mapped[str] = mapped_column(
        ForeignKey("regulation_version.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("provision.id", ondelete="RESTRICT"))
    level: Mapped[str] = mapped_column(String(24), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_path: Mapped[str] = mapped_column(Text, nullable=False)
    locator: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_line: Mapped[int] = mapped_column(Integer, nullable=False)
    security_class: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ChunkRow(Base):
    __tablename__ = "chunk"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    provision_id: Mapped[str] = mapped_column(
        ForeignKey("provision.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    context_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    publication_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    security_class: Mapped[str] = mapped_column(String(16), nullable=False, index=True)


class EmbeddingRow(Base):
    __tablename__ = "embedding"

    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("chunk.id", ondelete="CASCADE"), primary_key=True
    )
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[list[float]] = mapped_column(Vector(192), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class OntologyNodeRow(Base):
    __tablename__ = "ontology_entity"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, nullable=False)
    security_class: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    ontology_version: Mapped[str] = mapped_column(Text, nullable=False)
    publication_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)


class OntologyEdgeRow(Base):
    __tablename__ = "ontology_assertion"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    predicate: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    subject_entity_id: Mapped[str] = mapped_column(
        ForeignKey("ontology_entity.id", ondelete="CASCADE"), nullable=False
    )
    object_entity_id: Mapped[str] = mapped_column(
        ForeignKey("ontology_entity.id", ondelete="CASCADE"), nullable=False
    )
    source_document_id: Mapped[str] = mapped_column(
        ForeignKey("regulation_document.id", ondelete="RESTRICT"), nullable=False
    )
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    publication_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)


class PublicationRow(Base):
    __tablename__ = "publication"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    ontology_version: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_version: Mapped[str] = mapped_column(Text, nullable=False)
    graph_watermark: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class PublicationMemberRow(Base):
    __tablename__ = "publication_member"

    publication_id: Mapped[str] = mapped_column(
        ForeignKey("publication.id", ondelete="CASCADE"), primary_key=True
    )
    version_id: Mapped[str] = mapped_column(
        ForeignKey("regulation_version.id", ondelete="RESTRICT"), primary_key=True
    )
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    security_class: Mapped[str] = mapped_column(String(16), nullable=False, index=True)


class QARunRow(Base):
    __tablename__ = "qa_run"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner_subject: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    question_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    answer: Mapped[str | None] = mapped_column(Text)
    warnings: Mapped[list[str]] = mapped_column(JSON_VALUE, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64))
    suggested_actions: Mapped[list[str]] = mapped_column(JSON_VALUE, nullable=False)
    trace_summary: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, nullable=False)
    publication_id: Mapped[str] = mapped_column(
        ForeignKey("publication.id", ondelete="RESTRICT"), nullable=False, index=True
    )


class QACitationRow(Base):
    __tablename__ = "qa_citation"

    qa_run_id: Mapped[str] = mapped_column(
        ForeignKey("qa_run.id", ondelete="CASCADE"), primary_key=True
    )
    citation_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("regulation_document.id", ondelete="RESTRICT"), nullable=False
    )
    version_id: Mapped[str] = mapped_column(
        ForeignKey("regulation_version.id", ondelete="RESTRICT"), nullable=False
    )
    provision_id: Mapped[str] = mapped_column(
        ForeignKey("provision.id", ondelete="RESTRICT"), nullable=False
    )
    quote_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class AuditEventRow(Base):
    __tablename__ = "audit_event"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    actor_subject: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    action: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_VALUE, nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
