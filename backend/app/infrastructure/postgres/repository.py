from __future__ import annotations

import threading
from collections import defaultdict
from datetime import date
from pathlib import Path

from sqlalchemy import Engine, and_, create_engine, delete, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.errors import ConfigurationError
from app.domain.models import (
    KnowledgeSnapshot,
    OntologyEdge,
    OntologyNode,
    Principal,
    Provision,
    ProvisionLevel,
    RegulationDocument,
    RegulationVersion,
    SecurityClass,
)
from app.infrastructure.mock_repository import MockKnowledgeRepository
from app.infrastructure.postgres.models import (
    ChunkRow,
    EmbeddingRow,
    OntologyEdgeRow,
    OntologyNodeRow,
    ProvisionRow,
    PublicationMemberRow,
    PublicationRow,
    RegulationDocumentRow,
    RegulationVersionRow,
)
from app.infrastructure.retrieval import DeterministicEmbeddingProvider


def effective_document_scope(
    principal_scope: frozenset[str] | None,
    requested_scope: frozenset[str] | None,
) -> frozenset[str] | None:
    if requested_scope is None:
        return principal_scope
    if principal_scope is None:
        return requested_scope
    return frozenset(requested_scope.intersection(principal_scope))


class PostgresKnowledgeRepository(MockKnowledgeRepository):
    """PostgreSQL canonical repository hydrated from versioned canonical rows."""

    mode = "postgresql"

    def __init__(
        self,
        database_url: str,
        mock_data_dir: Path,
        *,
        auto_seed_mock_data: bool = False,
        engine: Engine | None = None,
    ):
        super().__init__(mock_data_dir)
        self._lock = threading.RLock()
        self._engine = engine or create_engine(database_url, pool_pre_ping=True)
        self._sessions = sessionmaker(self._engine, expire_on_commit=False)
        try:
            self.healthcheck()
            if auto_seed_mock_data:
                self._seed_snapshot(self._snapshot)
            self._snapshot = self._hydrate_snapshot()
        except SQLAlchemyError as exc:
            raise ConfigurationError("PostgreSQL canonical store is unavailable.") from exc

    @property
    def engine(self) -> Engine:
        return self._engine

    def healthcheck(self) -> bool:
        with self._engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True

    def reload(self) -> KnowledgeSnapshot:
        candidate = self._load()
        try:
            self._seed_snapshot(candidate)
            hydrated = self._hydrate_snapshot()
        except SQLAlchemyError as exc:
            raise ConfigurationError("PostgreSQL mock seed failed.") from exc
        with self._lock:
            self._snapshot = hydrated
            return hydrated

    def _seed_snapshot(self, snapshot: KnowledgeSnapshot) -> None:
        embedding_provider = DeterministicEmbeddingProvider()
        with self._sessions.begin() as session:
            session.execute(
                update(PublicationRow)
                .where(
                    PublicationRow.status == "ACTIVE",
                    PublicationRow.id != snapshot.publication_id,
                )
                .values(status="RETIRED")
            )
            session.merge(
                PublicationRow(
                    id=snapshot.publication_id,
                    status="ACTIVE",
                    ontology_version="0.1.0",
                    embedding_version=embedding_provider.profile_id,
                    graph_watermark=snapshot.graph_watermark,
                    activated_at=snapshot.loaded_at,
                    manifest_sha256=snapshot.publication_id.removeprefix("mock-").ljust(64, "0"),
                )
            )
            for document in snapshot.documents.values():
                session.merge(
                    RegulationDocumentRow(
                        id=document.id,
                        document_code=document.document_code,
                        title=document.title,
                        institution=document.institution,
                        document_type=document.document_type,
                        owner_org=document.owner_org,
                        security_class=document.security_class.value,
                        status=document.status,
                        is_mock=document.is_mock,
                    )
                )
            session.flush()
            for version in sorted(
                snapshot.versions.values(), key=lambda item: (item.effective_from, item.id)
            ):
                session.merge(
                    RegulationVersionRow(
                        id=version.id,
                        document_id=version.document_id,
                        version_label=version.version_label,
                        promulgated_on=version.promulgated_on,
                        effective_from=version.effective_from,
                        effective_to=version.effective_to,
                        status=version.status,
                        supersedes_version_id=version.supersedes_version_id,
                        source_sha256=version.source_sha256,
                        source_name=version.source_name,
                        is_mock=version.is_mock,
                    )
                )
                session.flush()
            session.execute(
                delete(PublicationMemberRow).where(
                    PublicationMemberRow.publication_id == snapshot.publication_id
                )
            )
            session.add_all(
                [
                    PublicationMemberRow(
                        publication_id=snapshot.publication_id,
                        version_id=version.id,
                        source_sha256=version.source_sha256,
                        security_class=snapshot.documents[version.document_id].security_class.value,
                    )
                    for version in snapshot.versions.values()
                ]
            )
            for version_id in sorted(snapshot.provisions_by_version):
                for provision_id in snapshot.provisions_by_version[version_id]:
                    provision = snapshot.provisions[provision_id]
                    session.merge(
                        ProvisionRow(
                            id=provision.id,
                            document_id=provision.document_id,
                            version_id=provision.version_id,
                            parent_id=provision.parent_id,
                            level=provision.level.value,
                            ordinal=provision.ordinal,
                            canonical_path=provision.canonical_path,
                            locator=provision.locator,
                            title=provision.title,
                            body=provision.body,
                            body_sha256=provision.body_sha256,
                            source_line=provision.source_line,
                            security_class=provision.security_class.value,
                            is_mock=provision.is_mock,
                        )
                    )
                    session.flush()
                    if provision.level == ProvisionLevel.PARAGRAPH:
                        chunk_id = f"{provision.id}:chunk-0"
                        session.merge(
                            ChunkRow(
                                id=chunk_id,
                                provision_id=provision.id,
                                text=provision.body,
                                context_prefix=f"{provision.document_id} > {provision.locator}",
                                publication_id=snapshot.publication_id,
                                security_class=provision.security_class.value,
                            )
                        )
                        session.flush()
                        vector = embedding_provider.embed(provision.body)
                        session.merge(
                            EmbeddingRow(
                                chunk_id=chunk_id,
                                model_id=embedding_provider.profile_id,
                                dimensions=len(vector),
                                vector=list(vector),
                                content_sha256=provision.body_sha256,
                            )
                        )
            for node in snapshot.ontology_nodes.values():
                session.merge(
                    OntologyNodeRow(
                        id=node.id,
                        entity_type=node.type,
                        label=node.label,
                        properties=node.properties,
                        security_class=node.security_class.value,
                        ontology_version="0.1.0",
                        publication_id=snapshot.publication_id,
                    )
                )
            session.flush()
            for edge in snapshot.ontology_edges:
                session.merge(
                    OntologyEdgeRow(
                        id=edge.id,
                        predicate=edge.type,
                        subject_entity_id=edge.source,
                        object_entity_id=edge.target,
                        source_document_id=edge.source_document,
                        source_locator=edge.source_locator,
                        review_status=edge.review_status,
                        confidence=1.0,
                        publication_id=snapshot.publication_id,
                    )
                )

    def _hydrate_snapshot(self) -> KnowledgeSnapshot:
        with self._sessions() as session:
            publication = session.scalar(
                select(PublicationRow)
                .where(PublicationRow.status == "ACTIVE")
                .order_by(PublicationRow.activated_at.desc())
                .limit(1)
            )
            if publication is None:
                raise ConfigurationError(
                    "PostgreSQL contains no active publication; run migration and seed first."
                )
            member_version_ids = select(PublicationMemberRow.version_id).where(
                PublicationMemberRow.publication_id == publication.id
            )
            active_document_ids = (
                select(RegulationVersionRow.document_id)
                .join(
                    PublicationMemberRow,
                    PublicationMemberRow.version_id == RegulationVersionRow.id,
                )
                .where(PublicationMemberRow.publication_id == publication.id)
            )
            documents = {
                row.id: RegulationDocument(
                    id=row.id,
                    document_code=row.document_code,
                    title=row.title,
                    institution=row.institution,
                    document_type=row.document_type,
                    owner_org=row.owner_org,
                    security_class=SecurityClass(row.security_class),
                    status=row.status,
                    is_mock=row.is_mock,
                )
                for row in session.scalars(
                    select(RegulationDocumentRow).where(
                        RegulationDocumentRow.id.in_(active_document_ids)
                    )
                ).all()
            }
            versions = {
                row.id: RegulationVersion(
                    id=row.id,
                    document_id=row.document_id,
                    version_label=row.version_label,
                    promulgated_on=row.promulgated_on,
                    effective_from=row.effective_from,
                    effective_to=row.effective_to,
                    status=row.status,
                    supersedes_version_id=row.supersedes_version_id,
                    source_sha256=row.source_sha256,
                    source_name=row.source_name,
                    is_mock=row.is_mock,
                )
                for row in session.scalars(
                    select(RegulationVersionRow).where(
                        RegulationVersionRow.id.in_(member_version_ids)
                    )
                ).all()
            }
            provisions = {
                row.id: Provision(
                    id=row.id,
                    document_id=row.document_id,
                    version_id=row.version_id,
                    parent_id=row.parent_id,
                    level=ProvisionLevel(row.level),
                    ordinal=row.ordinal,
                    canonical_path=row.canonical_path,
                    locator=row.locator,
                    title=row.title,
                    body=row.body,
                    body_sha256=row.body_sha256,
                    source_line=row.source_line,
                    security_class=SecurityClass(row.security_class),
                    is_mock=row.is_mock,
                )
                for row in session.scalars(
                    select(ProvisionRow).where(ProvisionRow.version_id.in_(member_version_ids))
                ).all()
            }
            edges = tuple(
                OntologyEdge(
                    id=row.id,
                    type=row.predicate,
                    source=row.subject_entity_id,
                    target=row.object_entity_id,
                    source_document=row.source_document_id,
                    source_locator=row.source_locator,
                    review_status=row.review_status,
                )
                for row in session.scalars(
                    select(OntologyEdgeRow).where(
                        OntologyEdgeRow.publication_id == publication.id,
                        OntologyEdgeRow.source_document_id.in_(active_document_ids),
                    )
                ).all()
            )
            source_documents: dict[str, set[str]] = defaultdict(set)
            for edge in edges:
                source_documents[edge.source].add(edge.source_document)
                source_documents[edge.target].add(edge.source_document)
            nodes = {
                row.id: OntologyNode(
                    id=row.id,
                    type=row.entity_type,
                    label=row.label,
                    security_class=SecurityClass(row.security_class),
                    properties=row.properties,
                    source_document_ids=frozenset(source_documents[row.id]),
                )
                for row in session.scalars(
                    select(OntologyNodeRow).where(OntologyNodeRow.publication_id == publication.id)
                ).all()
            }
        versions_by_document = {
            document_id: tuple(
                item.id
                for item in sorted(
                    (
                        version
                        for version in versions.values()
                        if version.document_id == document_id
                    ),
                    key=lambda version: (version.effective_from, version.version_label),
                )
            )
            for document_id in documents
        }
        provisions_by_version = {
            version_id: tuple(
                item.id
                for item in sorted(
                    (
                        provision
                        for provision in provisions.values()
                        if provision.version_id == version_id
                    ),
                    key=lambda provision: (provision.source_line, provision.id),
                )
            )
            for version_id in versions
        }
        return KnowledgeSnapshot(
            publication_id=publication.id,
            graph_watermark=publication.graph_watermark,
            loaded_at=publication.activated_at,
            documents=documents,
            versions=versions,
            versions_by_document=versions_by_document,
            provisions=provisions,
            provisions_by_version=provisions_by_version,
            ontology_nodes=nodes,
            ontology_edges=edges,
        )

    def vector_search(
        self,
        query_vector: tuple[float, ...],
        as_of: date,
        principal: Principal,
        document_ids: frozenset[str] | None,
        limit: int,
    ) -> tuple[tuple[str, float], ...]:
        publication_id = self.snapshot.publication_id
        distance = EmbeddingRow.vector.cosine_distance(list(query_vector)).label("distance")
        statement = (
            select(ProvisionRow.id, distance)
            .join(ChunkRow, ChunkRow.provision_id == ProvisionRow.id)
            .join(EmbeddingRow, EmbeddingRow.chunk_id == ChunkRow.id)
            .join(RegulationVersionRow, RegulationVersionRow.id == ProvisionRow.version_id)
            .join(RegulationDocumentRow, RegulationDocumentRow.id == ProvisionRow.document_id)
            .join(
                PublicationMemberRow,
                and_(
                    PublicationMemberRow.version_id == RegulationVersionRow.id,
                    PublicationMemberRow.publication_id == ChunkRow.publication_id,
                ),
            )
            .join(PublicationRow, PublicationRow.id == PublicationMemberRow.publication_id)
            .where(
                ChunkRow.publication_id == publication_id,
                PublicationMemberRow.publication_id == publication_id,
                PublicationRow.status == "ACTIVE",
                RegulationVersionRow.status == "published",
                RegulationVersionRow.effective_from <= as_of,
                (RegulationVersionRow.effective_to.is_(None))
                | (RegulationVersionRow.effective_to > as_of),
                RegulationDocumentRow.security_class.in_(
                    [item.value for item in principal.allowed_security_classes]
                ),
            )
            .order_by(distance)
            .limit(limit)
        )
        effective_scope = effective_document_scope(principal.allowed_document_ids, document_ids)
        if effective_scope is not None:
            if not effective_scope:
                return ()
            statement = statement.where(RegulationDocumentRow.id.in_(effective_scope))
        with Session(self._engine) as session:
            rows = session.execute(statement).all()
        return tuple(
            (provision_id, max(0.0, 1.0 - float(raw_distance)))
            for provision_id, raw_distance in rows
        )
