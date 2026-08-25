from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.domain.models import Citation, KnowledgeSnapshot, Principal, QAResult, SecurityClass
from app.infrastructure.postgres.models import (
    Base,
    OntologyEdgeRow,
    OntologyNodeRow,
    ProvisionRow,
    PublicationMemberRow,
    PublicationRow,
    QACitationRow,
    QARunRow,
    RegulationDocumentRow,
    RegulationVersionRow,
)
from app.infrastructure.postgres.qa_store import PostgresQAResultStore
from app.infrastructure.postgres.repository import PostgresKnowledgeRepository


def _create_contract_tables(engine: Engine) -> None:
    Base.metadata.create_all(
        engine,
        tables=[
            RegulationDocumentRow.__table__,
            RegulationVersionRow.__table__,
            ProvisionRow.__table__,
            OntologyNodeRow.__table__,
            OntologyEdgeRow.__table__,
            PublicationRow.__table__,
            PublicationMemberRow.__table__,
            QARunRow.__table__,
            QACitationRow.__table__,
        ],
    )


def _seed_active_and_stale_rows(engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                RegulationDocumentRow(
                    id="ACTIVE-DOC",
                    document_code="ACTIVE",
                    title="활성 규정",
                    institution="가상 금융기관",
                    document_type="policy",
                    owner_org="보안부",
                    security_class="internal",
                    status="active",
                    is_mock=True,
                ),
                RegulationDocumentRow(
                    id="STALE-DOC",
                    document_code="STALE",
                    title="구 publication 규정",
                    institution="가상 금융기관",
                    document_type="policy",
                    owner_org="보안부",
                    security_class="internal",
                    status="active",
                    is_mock=True,
                ),
            ]
        )
        session.add_all(
            [
                RegulationVersionRow(
                    id="ACTIVE-DOC:v1",
                    document_id="ACTIVE-DOC",
                    version_label="1.0",
                    promulgated_on=date(2026, 1, 1),
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="published",
                    supersedes_version_id=None,
                    source_sha256="a" * 64,
                    source_name="active.md",
                    is_mock=True,
                ),
                RegulationVersionRow(
                    id="STALE-DOC:v1",
                    document_id="STALE-DOC",
                    version_label="1.0",
                    promulgated_on=date(2025, 1, 1),
                    effective_from=date(2025, 1, 1),
                    effective_to=None,
                    status="published",
                    supersedes_version_id=None,
                    source_sha256="b" * 64,
                    source_name="stale.md",
                    is_mock=True,
                ),
            ]
        )
        session.add_all(
            [
                ProvisionRow(
                    id="ACTIVE-DOC:v1:art-1",
                    document_id="ACTIVE-DOC",
                    version_id="ACTIVE-DOC:v1",
                    parent_id=None,
                    level="article",
                    ordinal=1,
                    canonical_path="art-1",
                    locator="제1조",
                    title="활성",
                    body="활성 publication 조문",
                    body_sha256="c" * 64,
                    source_line=1,
                    security_class="internal",
                    is_mock=True,
                ),
                ProvisionRow(
                    id="STALE-DOC:v1:art-1",
                    document_id="STALE-DOC",
                    version_id="STALE-DOC:v1",
                    parent_id=None,
                    level="article",
                    ordinal=1,
                    canonical_path="art-1",
                    locator="제1조",
                    title="구버전",
                    body="구 publication 조문",
                    body_sha256="d" * 64,
                    source_line=1,
                    security_class="internal",
                    is_mock=True,
                ),
            ]
        )
        session.add_all(
            [
                PublicationRow(
                    id="active-publication",
                    status="ACTIVE",
                    ontology_version="1",
                    embedding_version="fake-192",
                    graph_watermark="active-watermark",
                    activated_at=datetime(2026, 8, 24, tzinfo=UTC),
                    manifest_sha256="e" * 64,
                ),
                PublicationRow(
                    id="stale-publication",
                    status="RETIRED",
                    ontology_version="0",
                    embedding_version="fake-192",
                    graph_watermark="stale-watermark",
                    activated_at=datetime(2025, 8, 24, tzinfo=UTC),
                    manifest_sha256="f" * 64,
                ),
            ]
        )
        session.add_all(
            [
                PublicationMemberRow(
                    publication_id="active-publication",
                    version_id="ACTIVE-DOC:v1",
                    source_sha256="a" * 64,
                    security_class="internal",
                ),
                PublicationMemberRow(
                    publication_id="stale-publication",
                    version_id="STALE-DOC:v1",
                    source_sha256="b" * 64,
                    security_class="internal",
                ),
            ]
        )


def _seed_mock_snapshot_rows(engine: Engine, snapshot: KnowledgeSnapshot) -> None:
    with Session(engine) as session, session.begin():
        session.add(
            PublicationRow(
                id=snapshot.publication_id,
                status="ACTIVE",
                ontology_version="0.1.0",
                embedding_version="fake-char-ngram-192-v1",
                graph_watermark=snapshot.graph_watermark,
                activated_at=snapshot.loaded_at,
                manifest_sha256=snapshot.publication_id.removeprefix("mock-").ljust(64, "0"),
            )
        )
        session.add_all(
            [
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
                for document in snapshot.documents.values()
            ]
        )
        session.add_all(
            [
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
                for version in sorted(
                    snapshot.versions.values(), key=lambda item: (item.effective_from, item.id)
                )
            ]
        )
        for version_id in sorted(snapshot.provisions_by_version):
            for provision_id in snapshot.provisions_by_version[version_id]:
                provision = snapshot.provisions[provision_id]
                session.add(
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


def test_hydration_excludes_rows_outside_active_publication(
    tmp_path: Path, mock_data_dir: Path
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'hydration.db'}")
    _create_contract_tables(engine)
    _seed_active_and_stale_rows(engine)

    repository = PostgresKnowledgeRepository(
        "sqlite://",
        mock_data_dir,
        engine=engine,
    )
    snapshot = repository.snapshot

    assert snapshot.publication_id == "active-publication"
    assert set(snapshot.documents) == {"ACTIVE-DOC"}
    assert set(snapshot.versions) == {"ACTIVE-DOC:v1"}
    assert set(snapshot.provisions) == {"ACTIVE-DOC:v1:art-1"}


def test_vector_query_requires_active_publication_membership(
    tmp_path: Path,
    mock_data_dir: Path,
    monkeypatch: Any,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'vector-contract.db'}")
    _create_contract_tables(engine)
    _seed_active_and_stale_rows(engine)
    repository = PostgresKnowledgeRepository("sqlite://", mock_data_dir, engine=engine)
    captured: dict[str, Any] = {}

    class EmptyResult:
        def all(self) -> list[tuple[str, float]]:
            return []

    class CapturingSession:
        def __init__(self, unused_engine: Engine):
            del unused_engine

        def __enter__(self) -> CapturingSession:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def execute(self, statement: Any) -> EmptyResult:
            captured["statement"] = statement
            return EmptyResult()

    monkeypatch.setattr("app.infrastructure.postgres.repository.Session", CapturingSession)
    repository.vector_search(
        (0.0,) * 192,
        date(2026, 8, 24),
        Principal(
            subject="employee",
            role="employee",
            allowed_security_classes=frozenset({SecurityClass.INTERNAL}),
        ),
        None,
        10,
    )

    compiled = captured["statement"].compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "JOIN publication_member" in sql
    assert "JOIN publication" in sql
    assert "chunk.publication_id" in sql
    assert "publication_member.publication_id" in sql
    assert "active-publication" in compiled.params.values()


def test_postgres_qa_store_survives_adapter_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "qa-persistence.db"
    first_engine = create_engine(f"sqlite:///{database_path}")
    _create_contract_tables(first_engine)
    _seed_active_and_stale_rows(first_engine)
    result = QAResult(
        query_id="query-1",
        status="answered",
        answer="활성 publication 조문 [1]",
        as_of=date(2026, 8, 24),
        citations=(
            Citation(
                index=1,
                source_id="src-1",
                document_id="ACTIVE-DOC",
                version_id="ACTIVE-DOC:v1",
                provision_id="ACTIVE-DOC:v1:art-1",
                document_title="활성 규정",
                version_label="1.0",
                locator="제1조",
                quote="활성 publication 조문",
            ),
        ),
        warnings=("reference_only",),
        reason_code=None,
        suggested_actions=("담당 부서 확인",),
        trace={"publication_id": "active-publication", "source_count": 1},
    )
    PostgresQAResultStore(first_engine).save(
        result,
        owner_subject="owner-1",
        request_id="request-1",
        question_sha256="0" * 64,
    )
    first_engine.dispose()

    restarted_store = PostgresQAResultStore(create_engine(f"sqlite:///{database_path}"))
    stored = restarted_store.get("query-1")

    assert stored is not None
    assert stored.owner_subject == "owner-1"
    assert stored.result == result


def test_persisted_qa_api_enforces_owner_and_document_acl_after_restart(
    tmp_path: Path,
    client: TestClient,
) -> None:
    database_path = tmp_path / "qa-api-persistence.db"
    first_engine = create_engine(f"sqlite:///{database_path}")
    _create_contract_tables(first_engine)
    _seed_mock_snapshot_rows(first_engine, client.app.state.services.repository.snapshot)
    client.app.state.services.qa.result_store = PostgresQAResultStore(first_engine)

    created = client.post(
        "/api/v1/qa/queries",
        headers={"X-Demo-Subject": "owner"},
        json={
            "question": "퇴직자 접근권한은 언제까지 회수해야 하나요?",
            "as_of": "2026-08-24",
            "scope": {"document_ids": ["MOCK-ISP-001"]},
        },
    )
    assert created.status_code == 200
    assert created.json()["status"] == "answered"
    query_id = created.json()["query_id"]
    first_engine.dispose()

    restarted_engine = create_engine(f"sqlite:///{database_path}")
    client.app.state.services.qa.result_store = PostgresQAResultStore(restarted_engine)
    owner = client.get(f"/api/v1/qa/queries/{query_id}", headers={"X-Demo-Subject": "owner"})
    other = client.get(f"/api/v1/qa/queries/{query_id}", headers={"X-Demo-Subject": "other"})
    owner_without_source_scope = client.get(
        f"/api/v1/qa/queries/{query_id}",
        headers={
            "X-Demo-Subject": "owner",
            "X-Demo-Document-Ids": "MOCK-EFO-001",
        },
    )
    auditor = client.get(
        f"/api/v1/qa/queries/{query_id}",
        headers={"X-Demo-Subject": "auditor", "X-Demo-Role": "auditor"},
    )

    assert owner.status_code == 200
    assert owner.json() == created.json()
    assert other.status_code == 404
    assert owner_without_source_scope.status_code == 404
    assert auditor.status_code == 200
