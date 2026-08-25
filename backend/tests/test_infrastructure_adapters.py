from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from neo4j.exceptions import ServiceUnavailable

from app.cli import _project_with_startup_retry
from app.domain.errors import ConfigurationError
from app.domain.models import Principal, SecurityClass
from app.infrastructure.mock_repository import MockKnowledgeRepository
from app.infrastructure.neo4j.projection import Neo4jProjectionAdapter
from app.infrastructure.postgres.models import Base
from app.infrastructure.postgres.repository import effective_document_scope
from app.infrastructure.providers import OpenAIResponsesGenerationProvider
from app.infrastructure.retrieval import DeterministicEmbeddingProvider, HybridRetriever
from app.settings.config import Settings


@pytest.mark.parametrize(
    ("demo_auth_enabled", "repository_mode", "expected_message"),
    [
        ("true", "postgres", "Demo authentication is forbidden"),
        ("false", "mock", "PostgreSQL repository is required"),
    ],
)
def test_production_profile_rejects_unsafe_auth_and_repository_defaults(
    monkeypatch: Any,
    demo_auth_enabled: str,
    repository_mode: str,
    expected_message: str,
) -> None:
    monkeypatch.setenv("REGONTOLOGY_ENV", "production")
    monkeypatch.setenv("REGONTOLOGY_DEMO_AUTH_ENABLED", demo_auth_enabled)
    monkeypatch.setenv("REGONTOLOGY_REPOSITORY_MODE", repository_mode)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused:unused@localhost/unused")

    with pytest.raises(ConfigurationError, match=expected_message):
        Settings.from_env()


class VectorAwareRepository(MockKnowledgeRepository):
    def __init__(self, mock_data_dir: Path):
        super().__init__(mock_data_dir)
        self.vector_call: tuple[object, ...] | None = None

    def vector_search(
        self,
        query_vector: tuple[float, ...],
        as_of: date,
        principal: Principal,
        document_ids: frozenset[str] | None,
        limit: int,
    ) -> tuple[tuple[str, float], ...]:
        self.vector_call = (query_vector, as_of, principal, document_ids, limit)
        return (("MOCK-ISP-001:v1.1:art-5/p-1", 0.99),)


class FakeResult:
    def __init__(self, records: tuple[dict[str, object], ...] = ()):
        self.records = records

    def consume(self) -> None:
        return None

    def single(self) -> dict[str, object] | None:
        return self.records[0] if self.records else None

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.records)


class FakeTransaction:
    def __init__(
        self,
        calls: list[tuple[str, dict[str, Any]]],
        fail_at: int | None,
    ):
        self.calls = calls
        self.fail_at = fail_at

    def run(self, query: str, **parameters: Any) -> FakeResult:
        self.calls.append((query, parameters))
        if self.fail_at == len(self.calls):
            raise ServiceUnavailable("simulated transaction failure")
        return FakeResult()


class FakeSession:
    def __init__(self, driver: FakeDriver):
        self.driver = driver

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute_write(self, callback: Any, **parameters: Any) -> None:
        self.driver.execute_write_count += 1
        transaction_calls: list[tuple[str, dict[str, Any]]] = []
        try:
            callback(
                FakeTransaction(transaction_calls, self.driver.fail_transaction_at),
                **parameters,
            )
        except ServiceUnavailable:
            self.driver.rolled_back = True
            self.driver.transaction_calls = transaction_calls
            raise
        self.driver.transaction_calls = transaction_calls
        self.driver.calls.extend(transaction_calls)

    def run(self, query: str, **parameters: Any) -> FakeResult:
        self.driver.session_calls.append((query, parameters))
        return FakeResult(self.driver.query_records)


class FakeDriver:
    def __init__(
        self,
        *,
        fail_transaction_at: int | None = None,
        query_records: tuple[dict[str, object], ...] = (),
    ) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.transaction_calls: list[tuple[str, dict[str, Any]]] = []
        self.session_calls: list[tuple[str, dict[str, Any]]] = []
        self.execute_write_count = 0
        self.fail_transaction_at = fail_transaction_at
        self.query_records = query_records
        self.rolled_back = False
        self.closed = False

    def verify_connectivity(self) -> None:
        return None

    def session(self) -> FakeSession:
        return FakeSession(self)

    def close(self) -> None:
        self.closed = True


class ValueErrorSession:
    def __init__(self, message: str):
        self.message = message

    def __enter__(self) -> ValueErrorSession:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute_write(self, *_: object, **__: object) -> None:
        raise ValueError(self.message)

    def run(self, *_: object, **__: object) -> FakeResult:
        raise ValueError(self.message)


class ValueErrorDriver:
    def __init__(self, message: str):
        self.message = message

    def verify_connectivity(self) -> None:
        raise ValueError(self.message)

    def session(self) -> ValueErrorSession:
        return ValueErrorSession(self.message)

    def close(self) -> None:
        return None


def call_one_hop(adapter: Neo4jProjectionAdapter) -> None:
    adapter.one_hop(
        publication_id="publication-A",
        seed_ids=("doc:A",),
        allowed_node_ids=("doc:A", "org:A"),
        allowed_edge_ids=("e01",),
        allowed_document_ids=("A",),
        relation_types=("OWNED_BY",),
        max_edges=10,
    )


def test_pgvector_scope_is_principal_and_request_intersection() -> None:
    assert effective_document_scope(frozenset({"A", "B"}), frozenset({"B", "C"})) == frozenset(
        {"B"}
    )
    assert effective_document_scope(frozenset({"A"}), frozenset({"B"})) == frozenset()
    assert effective_document_scope(None, frozenset({"B"})) == frozenset({"B"})


def test_hybrid_retriever_uses_database_vector_lane(mock_data_dir: Path) -> None:
    repository = VectorAwareRepository(mock_data_dir)
    principal = Principal(
        subject="employee",
        role="employee",
        allowed_security_classes=frozenset({SecurityClass.PUBLIC, SecurityClass.INTERNAL}),
        allowed_document_ids=frozenset({"MOCK-ISP-001"}),
    )
    retriever = HybridRetriever(repository, DeterministicEmbeddingProvider())

    hits = retriever.retrieve(
        "접근권한 검토",
        date(2026, 8, 24),
        principal,
        document_ids=frozenset({"MOCK-ISP-001"}),
    )

    assert repository.vector_call is not None
    assert repository.vector_call[2] is principal
    assert repository.vector_call[3] == frozenset({"MOCK-ISP-001"})
    assert any(hit.lane_scores.get("vector") == 0.99 for hit in hits)


def test_neo4j_projection_uses_fixed_parameterized_templates(mock_data_dir: Path) -> None:
    snapshot = MockKnowledgeRepository(mock_data_dir).snapshot
    driver = FakeDriver()
    adapter = Neo4jProjectionAdapter("bolt://unused", "unused", "unused", driver=driver)  # type: ignore[arg-type]

    result = adapter.replace_projection(snapshot)

    assert result["node_count"] == 24
    assert result["edge_count"] == 22
    assert driver.execute_write_count == 1
    assert len(driver.calls) == 4
    assert driver.session_calls == []
    assert all(snapshot.publication_id not in query for query, _ in driver.calls)
    assert all("publication_id" in parameters for _, parameters in driver.calls)


def test_neo4j_projection_failure_rolls_back_single_explicit_transaction(
    mock_data_dir: Path,
) -> None:
    snapshot = MockKnowledgeRepository(mock_data_dir).snapshot
    driver = FakeDriver(fail_transaction_at=3)
    adapter = Neo4jProjectionAdapter("bolt://unused", "unused", "unused", driver=driver)  # type: ignore[arg-type]

    with pytest.raises(ConfigurationError, match="projection rebuild failed"):
        adapter.replace_projection(snapshot)

    assert driver.execute_write_count == 1
    assert driver.rolled_back is True
    assert driver.calls == []
    assert len(driver.transaction_calls) == 3


def test_neo4j_one_hop_uses_bounded_allowlisted_parameters() -> None:
    malicious_seed = "x') MATCH (secret) DETACH DELETE secret //"
    malicious_relation = "OWNED_BY) MATCH (secret) //"
    driver = FakeDriver(
        query_records=(
            {
                "edge_id": "e01",
                "source": "doc:A",
                "type": "OWNED_BY",
                "target": "org:A",
                "source_document": "A",
                "source_locator": "metadata",
                "review_status": "APPROVED",
            },
        )
    )
    adapter = Neo4jProjectionAdapter("bolt://unused", "unused", "unused", driver=driver)  # type: ignore[arg-type]

    rows = adapter.one_hop(
        publication_id="publication-A",
        seed_ids=(malicious_seed,),
        allowed_node_ids=(malicious_seed, "org:A"),
        allowed_edge_ids=("e01",),
        allowed_document_ids=("A",),
        relation_types=(malicious_relation,),
        max_edges=99_999,
    )

    assert rows[0]["edge_id"] == "e01"
    query, parameters = driver.session_calls[0]
    assert malicious_seed not in query
    assert malicious_relation not in query
    assert "edge.review_status = 'APPROVED'" in query
    assert parameters["seed_ids"] == [malicious_seed]
    assert parameters["relation_types"] == [malicious_relation]
    assert parameters["max_edges"] == 400


def test_neo4j_driver_timeouts_fit_compose_health_budget(monkeypatch: Any) -> None:
    captured: dict[str, object] = {}

    def fake_driver(uri: str, **kwargs: object) -> FakeDriver:
        captured["uri"] = uri
        captured.update(kwargs)
        return FakeDriver()

    monkeypatch.setattr(
        "app.infrastructure.neo4j.projection.GraphDatabase.driver",
        fake_driver,
    )

    Neo4jProjectionAdapter("bolt://neo4j:7687", "neo4j", "secret")

    assert captured["uri"] == "bolt://neo4j:7687"
    timeout_budget = sum(
        float(captured[name])
        for name in (
            "connection_timeout",
            "connection_acquisition_timeout",
            "max_transaction_retry_time",
        )
    )
    assert timeout_budget < 5.0


def test_compose_seed_retries_graph_then_degrades_without_blocking_postgres(
    mock_data_dir: Path,
    monkeypatch: Any,
) -> None:
    snapshot = MockKnowledgeRepository(mock_data_dir).snapshot

    class EventuallyAvailableProjection:
        def __init__(self) -> None:
            self.calls = 0

        def replace_projection(self, _: object) -> dict[str, int]:
            self.calls += 1
            if self.calls < 3:
                raise ConfigurationError("starting")
            return {"node_count": 24}

    class UnavailableProjection:
        def __init__(self) -> None:
            self.calls = 0

        def replace_projection(self, _: object) -> dict[str, int]:
            self.calls += 1
            raise ConfigurationError("down")

    monkeypatch.setattr("app.cli.sleep", lambda _: None)
    eventual = EventuallyAvailableProjection()
    unavailable = UnavailableProjection()

    assert _project_with_startup_retry(eventual, snapshot) == "healthy"  # type: ignore[arg-type]
    assert eventual.calls == 3
    assert _project_with_startup_retry(unavailable, snapshot) == "degraded"  # type: ignore[arg-type]
    assert unavailable.calls == 10


def test_dns_resolution_value_error_degrades_all_neo4j_runtime_paths(
    mock_data_dir: Path,
    monkeypatch: Any,
) -> None:
    snapshot = MockKnowledgeRepository(mock_data_dir).snapshot
    driver = ValueErrorDriver("Cannot resolve address neo4j:7687")
    adapter = Neo4jProjectionAdapter("bolt://unused", "unused", "unused", driver=driver)  # type: ignore[arg-type]

    with pytest.raises(ConfigurationError, match="projection is unavailable"):
        adapter.healthcheck()
    with pytest.raises(ConfigurationError, match="projection rebuild failed"):
        adapter.replace_projection(snapshot)
    assert adapter.status(snapshot.publication_id).status == "unavailable"
    with pytest.raises(ConfigurationError, match="bounded query failed"):
        call_one_hop(adapter)

    monkeypatch.setattr("app.cli.sleep", lambda _: None)
    assert _project_with_startup_retry(adapter, snapshot) == "degraded"


def test_unrelated_value_error_is_not_hidden_as_neo4j_outage(mock_data_dir: Path) -> None:
    snapshot = MockKnowledgeRepository(mock_data_dir).snapshot
    driver = ValueErrorDriver("programmer invariant failed")
    adapter = Neo4jProjectionAdapter("bolt://unused", "unused", "unused", driver=driver)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="programmer invariant failed"):
        adapter.healthcheck()
    with pytest.raises(ValueError, match="programmer invariant failed"):
        adapter.replace_projection(snapshot)
    with pytest.raises(ValueError, match="programmer invariant failed"):
        adapter.status(snapshot.publication_id)
    with pytest.raises(ValueError, match="programmer invariant failed"):
        call_one_hop(adapter)


def test_canonical_metadata_contains_vector_and_audit_tables() -> None:
    assert {
        "regulation_document",
        "regulation_version",
        "provision",
        "chunk",
        "embedding",
    }.issubset(Base.metadata.tables)
    assert "audit_event" in Base.metadata.tables


def test_openai_adapter_sends_strict_structured_output_contract(
    mock_data_dir: Path, monkeypatch: Any
) -> None:
    repository = MockKnowledgeRepository(mock_data_dir)
    principal = Principal(
        subject="employee",
        role="employee",
        allowed_security_classes=frozenset({SecurityClass.PUBLIC, SecurityClass.INTERNAL}),
    )
    retriever = HybridRetriever(repository, DeterministicEmbeddingProvider())
    contexts = retriever.retrieve("접근권한 검토", date(2026, 8, 24), principal, limit=1)
    settings = Settings(
        environment="test",
        mock_data_dir=mock_data_dir,
        cors_origins=(),
        demo_auth_enabled=True,
        ai_provider="openai",
        openai_model="test-model",
        openai_base_url="https://example.invalid/v1",
        openai_timeout_seconds=1.0,
        openai_api_key="test-only-not-a-real-key",
    )
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {
                "output_text": (
                    '{"summary":"grounded","claims":[{"text":"grounded",'
                    '"citation_ids":["src-1"]}],"warnings":[]}'
                )
            }

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("app.infrastructure.providers.httpx.post", fake_post)
    result = OpenAIResponsesGenerationProvider(settings).generate("접근권한 검토", contexts)

    payload = captured["json"]
    output_format = payload["text"]["format"]
    assert output_format["type"] == "json_schema"
    assert output_format["strict"] is True
    assert output_format["schema"]["additionalProperties"] is False
    citation_schema = output_format["schema"]["properties"]["claims"]["items"]["properties"][
        "citation_ids"
    ]
    assert citation_schema["items"]["enum"] == ["src-1"]
    assert result.summary == "grounded"
