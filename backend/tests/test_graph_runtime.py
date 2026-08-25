from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.application.graph_policy import compile_graph_access_scope
from app.application.services import OntologyService
from app.domain.errors import ConfigurationError
from app.domain.graph import GraphProjectionStatus
from app.domain.models import (
    KnowledgeSnapshot,
    OntologyEdge,
    OntologyNode,
    Principal,
    SecurityClass,
)
from app.infrastructure.mock_repository import MockKnowledgeRepository
from app.infrastructure.retrieval import DeterministicEmbeddingProvider, HybridRetriever
from app.main import create_app
from app.settings.config import Settings


def edge_row(edge: OntologyEdge) -> dict[str, object]:
    return {
        "edge_id": edge.id,
        "type": edge.type,
        "source": edge.source,
        "target": edge.target,
        "source_document": edge.source_document,
        "source_locator": edge.source_locator,
        "review_status": edge.review_status,
    }


class RecordingGraphQuery:
    def __init__(
        self,
        rows: tuple[Mapping[str, object], ...] = (),
        status: GraphProjectionStatus | None = None,
        fail_query: bool = False,
    ):
        self.rows = rows
        self.status_value = status or GraphProjectionStatus(
            status="healthy",
            publication_id=None,
        )
        self.fail_query = fail_query
        self.calls: list[dict[str, object]] = []

    def status(self, expected_publication_id: str) -> GraphProjectionStatus:
        if self.status_value.status == "healthy":
            return GraphProjectionStatus(status="healthy", publication_id=expected_publication_id)
        return self.status_value

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
    ) -> tuple[Mapping[str, object], ...]:
        self.calls.append(
            {
                "publication_id": publication_id,
                "seed_ids": seed_ids,
                "allowed_node_ids": allowed_node_ids,
                "allowed_edge_ids": allowed_edge_ids,
                "allowed_document_ids": allowed_document_ids,
                "relation_types": relation_types,
                "max_edges": max_edges,
            }
        )
        if self.fail_query:
            raise ConfigurationError("simulated graph outage")
        return self.rows


def employee(document_ids: frozenset[str] | None = None) -> Principal:
    return Principal(
        subject="employee",
        role="employee",
        allowed_security_classes=frozenset({SecurityClass.PUBLIC, SecurityClass.INTERNAL}),
        allowed_document_ids=document_ids,
    )


def test_graph_scope_requires_active_locator_provenance(mock_data_dir: Path) -> None:
    repository = MockKnowledgeRepository(mock_data_dir)
    canonical = repository.snapshot.ontology_edges[3]
    stale = replace(
        canonical,
        id="stale-edge",
        source_locator="제999조 제1항",
    )
    pending_node = OntologyNode(
        id="pending:unapproved-only",
        type="Obligation",
        label="승인되지 않은 후보",
        security_class=SecurityClass.INTERNAL,
        source_document_ids=frozenset({"MOCK-ISP-001"}),
    )
    pending = replace(
        canonical,
        id="pending-edge",
        target=pending_node.id,
        review_status="PENDING",
    )
    snapshot = repository.snapshot
    ontology_nodes = {**snapshot.ontology_nodes, pending_node.id: pending_node}
    repository._snapshot = replace(  # type: ignore[attr-defined]
        snapshot,
        ontology_nodes=ontology_nodes,
        ontology_edges=(*snapshot.ontology_edges, stale, pending),
    )

    current = compile_graph_access_scope(
        repository,
        employee(frozenset({"MOCK-ISP-001"})),
        date(2026, 8, 24),
    )
    before_effective = compile_graph_access_scope(
        repository,
        employee(frozenset({"MOCK-ISP-001"})),
        date(2025, 12, 31),
    )

    assert canonical.id in {edge.id for edge in current.approved_edges}
    assert "stale-edge" not in {edge.id for edge in current.approved_edges}
    assert "pending-edge" not in {edge.id for edge in current.approved_edges}
    assert pending_node.id not in current.node_ids
    assert before_effective.document_ids == ()
    assert before_effective.approved_edges == ()


def test_graph_retrieval_passes_only_precompiled_acl_scope_and_rejects_forged_rows(
    mock_data_dir: Path,
) -> None:
    repository = MockKnowledgeRepository(mock_data_dir)
    edges = {edge.id: edge for edge in repository.snapshot.ontology_edges}
    forged_restricted = edge_row(edges["e17"])
    forged_allowed_id = {
        **edge_row(edges["e04"]),
        "source_document": "MOCK-PIP-001",
    }
    graph = RecordingGraphQuery(rows=(edge_row(edges["e04"]), forged_restricted, forged_allowed_id))
    retriever = HybridRetriever(
        repository,
        DeterministicEmbeddingProvider(),
        graph,
    )

    hits, graph_status = retriever.retrieve_with_status(
        "접근권한 검토",
        date(2026, 8, 24),
        employee(frozenset({"MOCK-ISP-001"})),
        document_ids=frozenset({"MOCK-ISP-001", "MOCK-PIP-001"}),
    )

    assert graph_status == "healthy"
    assert graph.calls
    call = graph.calls[0]
    assert call["allowed_document_ids"] == ("MOCK-ISP-001",)
    assert "e17" not in call["allowed_edge_ids"]
    assert all(hit.document.id == "MOCK-ISP-001" for hit in hits)
    assert any(hit.lane_scores.get("graph") == 0.35 for hit in hits)


def test_graph_retrieval_outage_falls_back_to_vector_and_lexical(
    mock_data_dir: Path,
) -> None:
    repository = MockKnowledgeRepository(mock_data_dir)
    graph = RecordingGraphQuery(fail_query=True)
    retriever = HybridRetriever(
        repository,
        DeterministicEmbeddingProvider(),
        graph,
    )

    hits, graph_status = retriever.retrieve_with_status(
        "접근권한 검토 주기는?",
        date(2026, 8, 24),
        employee(frozenset({"MOCK-ISP-001"})),
    )

    assert graph_status == "unavailable"
    assert hits
    assert all("graph" not in hit.lane_scores for hit in hits)
    assert any("lexical" in hit.lane_scores for hit in hits)
    assert any("vector" in hit.lane_scores for hit in hits)


def test_ontology_subgraph_uses_neo4j_and_reverifies_canonical_edges(
    mock_data_dir: Path,
) -> None:
    repository = MockKnowledgeRepository(mock_data_dir)
    edges = {edge.id: edge for edge in repository.snapshot.ontology_edges}
    graph = RecordingGraphQuery(
        rows=(
            edge_row(edges["e04"]),
            edge_row(edges["e05"]),
            edge_row(edges["e17"]),
        )
    )
    service = OntologyService(repository, graph)

    result = service.subgraph(
        principal=employee(frozenset({"MOCK-ISP-001"})),
        seed_ids=("obligation:분기접근권한검토",),
        relation_types=None,
        depth=1,
        max_nodes=50,
        as_of=date(2026, 8, 24),
    )

    assert graph.calls
    assert result["graph_status"] == "healthy"
    assert {edge["id"] for edge in result["edges"]} == {"e04", "e05"}
    assert all(node["security_class"] != "restricted" for node in result["nodes"])


class UnavailableProjection:
    def __init__(self, *_: object, **__: object):
        self.closed = False

    def healthcheck(self) -> bool:
        raise ConfigurationError("unavailable")

    def status(self, expected_publication_id: str) -> GraphProjectionStatus:
        del expected_publication_id
        return GraphProjectionStatus(status="unavailable", publication_id=None)

    def one_hop(self, **_: object) -> tuple[Mapping[str, object], ...]:
        raise AssertionError("unavailable projection must not be queried")

    def replace_projection(self, snapshot: KnowledgeSnapshot) -> dict[str, Any]:
        del snapshot
        raise ConfigurationError("unavailable")

    def close(self) -> None:
        self.closed = True


def test_neo4j_outage_does_not_block_startup_and_is_reported(
    mock_data_dir: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "app.infrastructure.neo4j.projection.Neo4jProjectionAdapter",
        UnavailableProjection,
    )
    settings = Settings(
        environment="test",
        mock_data_dir=mock_data_dir,
        cors_origins=(),
        demo_auth_enabled=True,
        ai_provider="fake",
        openai_model="unused",
        openai_base_url="https://api.openai.com/v1",
        openai_timeout_seconds=1.0,
        openai_api_key=None,
        graph_mode="neo4j",
        neo4j_uri="bolt://unavailable",
        neo4j_user="unused",
        neo4j_password="unused",
    )

    with TestClient(create_app(settings)) as client:
        health = client.get("/api/v1/health")
        ready = client.get("/health/ready")
        answer = client.post(
            "/api/v1/qa/queries",
            json={"question": "접근권한 검토 주기는?", "as_of": "2026-08-24"},
        )

    assert health.status_code == 200
    assert health.json()["graph_status"] == "unavailable"
    assert ready.status_code == 200
    assert ready.json()["status"] == "degraded"
    assert answer.status_code == 200
    assert answer.json()["status"] == "answered"
    assert answer.json()["trace"]["graph_status"] == "unavailable"
    assert "degraded_graph" in answer.json()["warnings"]
