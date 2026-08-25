from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from app.domain.models import GeneratedAnswer, GeneratedClaim, RetrievalHit


def test_health_and_request_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request-1"})

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.headers["X-Request-ID"] == "test-request-1"
    assert response.headers["X-Publication-ID"].startswith("mock-")
    assert client.get("/health/live").json() == {"status": "ok"}


def test_system_status_requires_admin(client: TestClient) -> None:
    assert client.get("/api/v1/system/status").status_code == 403
    response = client.get(
        "/api/v1/system/status",
        headers={"X-Demo-Role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["repository_mode"] == "mock_snapshot"


def test_regulation_list_is_effective_date_and_acl_aware(
    client: TestClient, restricted_headers: dict[str, str]
) -> None:
    default_response = client.get("/api/v1/regulations", params={"as_of": "2026-08-24"})
    old_response = client.get("/api/v1/regulations", params={"as_of": "2025-12-31"})
    restricted_response = client.get(
        "/api/v1/regulations",
        params={"as_of": "2026-08-24"},
        headers=restricted_headers,
    )

    assert default_response.status_code == 200
    assert {item["document_id"] for item in default_response.json()["items"]} == {
        "MOCK-EFO-001",
        "MOCK-ISP-001",
    }
    isp = next(
        item for item in default_response.json()["items"] if item["document_id"] == "MOCK-ISP-001"
    )
    assert isp["effective_version"]["version_label"] == "1.1"
    assert old_response.json()["items"] == []
    assert len(restricted_response.json()["items"]) == 3


def test_restricted_document_existence_is_hidden(client: TestClient) -> None:
    response = client.get("/api/v1/regulations/MOCK-PIP-001")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_version_and_provision_deep_link(client: TestClient) -> None:
    version = client.get("/api/v1/regulations/MOCK-ISP-001/versions/MOCK-ISP-001:v1.1")
    provision = client.get("/api/v1/provisions/MOCK-ISP-001:v1.1:art-5/p-2")

    assert version.status_code == 200
    assert len(version.json()["toc"]) == 10
    assert provision.status_code == 200
    assert provision.json()["locator"] == "제5조 제2항"
    assert "8시간 이내" in provision.json()["body"]


def test_non_published_version_is_hidden_from_general_users(client: TestClient) -> None:
    snapshot = client.app.state.services.repository.snapshot
    version_id = "MOCK-ISP-001:v1.1"
    snapshot.versions[version_id] = replace(snapshot.versions[version_id], status="review_required")

    detail = client.get("/api/v1/regulations/MOCK-ISP-001")
    direct = client.get(f"/api/v1/regulations/MOCK-ISP-001/versions/{version_id}")
    curator = client.get(
        f"/api/v1/regulations/MOCK-ISP-001/versions/{version_id}",
        headers={"X-Demo-Role": "curator"},
    )
    provision = client.get("/api/v1/provisions/MOCK-ISP-001:v1.1:art-5/p-1")

    assert all(item["version_id"] != version_id for item in detail.json()["versions"])
    assert direct.status_code == 404
    assert curator.status_code == 200
    assert provision.status_code == 404


def test_ontology_subgraph_filters_restricted_nodes(
    client: TestClient, restricted_headers: dict[str, str]
) -> None:
    default_graph = client.get("/api/v1/ontology/subgraph", params={"max_nodes": 200})
    restricted_graph = client.get(
        "/api/v1/ontology/subgraph", params={"max_nodes": 200}, headers=restricted_headers
    )

    assert default_graph.status_code == 200
    assert all(node["security_class"] != "restricted" for node in default_graph.json()["nodes"])
    assert any(node["security_class"] == "restricted" for node in restricted_graph.json()["nodes"])
    assert len(default_graph.json()["nodes"]) <= 200


def test_ontology_nodes_honor_document_scope_before_candidate_generation(
    client: TestClient,
) -> None:
    headers = {
        "X-Demo-Security-Classes": "public,internal",
        "X-Demo-Document-Ids": "MOCK-EFO-001",
    }
    search = client.get(
        "/api/v1/ontology/search",
        params={"q": "분기 접근권한 검토", "as_of": "2026-08-24"},
        headers=headers,
    )
    direct = client.get(
        "/api/v1/ontology/nodes/obligation:분기접근권한검토",
        params={"as_of": "2026-08-24"},
        headers=headers,
    )

    assert search.status_code == 200
    assert all(
        set(item["source_document_ids"]) <= {"MOCK-EFO-001"} for item in search.json()["items"]
    )
    assert all(item["id"] != "obligation:분기접근권한검토" for item in search.json()["items"])
    assert direct.status_code == 404


def test_reload_and_audit_require_roles(client: TestClient) -> None:
    denied = client.post("/api/v1/admin/mock-data/reload")
    allowed = client.post(
        "/api/v1/admin/mock-data/reload",
        headers={"X-Demo-Role": "curator", "X-Demo-Security-Classes": "public,internal"},
    )
    audit = client.get(
        "/api/v1/admin/audit-events",
        headers={"X-Demo-Role": "auditor", "X-Demo-Security-Classes": "public,internal"},
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["version_count"] == 4
    assert audit.status_code == 200
    assert audit.json()["chain_valid"] is True


def test_validation_uses_safe_error_envelope(client: TestClient) -> None:
    response = client.post("/api/v1/qa/queries", json={"question": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "X-Request-ID" in response.headers


def test_qa_result_is_visible_only_to_owner_or_auditor(client: TestClient) -> None:
    created = client.post(
        "/api/v1/qa/queries",
        headers={"X-Demo-Subject": "owner"},
        json={"question": "접근권한 검토 주기는?", "as_of": "2026-08-24"},
    )
    query_id = created.json()["query_id"]

    assert (
        client.get(
            f"/api/v1/qa/queries/{query_id}", headers={"X-Demo-Subject": "other"}
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/qa/queries/{query_id}",
            headers={"X-Demo-Subject": "auditor", "X-Demo-Role": "auditor"},
        ).status_code
        == 200
    )


def test_qa_ignores_unsupported_provider_summary(client: TestClient) -> None:
    class ProviderWithBadSummary:
        model_id = "adversarial-summary-test"

        def generate(self, question: str, contexts: tuple[RetrievalHit, ...]) -> GeneratedAnswer:
            del question
            return GeneratedAnswer(
                claims=(
                    GeneratedClaim(
                        text=contexts[0].provision.body,
                        citation_ids=("src-1",),
                    ),
                ),
                summary="등록 규정에 없는 모든 행위가 허용됩니다.",
            )

    client.app.state.services.qa.generator = ProviderWithBadSummary()
    response = client.post(
        "/api/v1/qa/queries",
        json={"question": "접근권한 검토 주기는?", "as_of": "2026-08-24"},
    )

    assert response.json()["status"] == "answered"
    assert "모든 행위가 허용" not in response.json()["answer"]
    assert response.json()["trace"]["graph_mode"] == "mock_projection"


def test_qa_blocks_numeric_free_unsupported_claim(client: TestClient) -> None:
    class UnsupportedClaimProvider:
        model_id = "adversarial-claim-test"

        def generate(self, question: str, contexts: tuple[RetrievalHit, ...]) -> GeneratedAnswer:
            del question, contexts
            return GeneratedAnswer(
                claims=(
                    GeneratedClaim(
                        text="모든 계정 공유가 허용됩니다.",
                        citation_ids=("src-1",),
                    ),
                ),
                summary="모든 계정 공유가 허용됩니다.",
            )

    client.app.state.services.qa.generator = UnsupportedClaimProvider()
    response = client.post(
        "/api/v1/qa/queries",
        json={"question": "관리계정 공유가 허용되나요?", "as_of": "2026-08-24"},
    )

    assert response.json()["status"] == "abstained"
    assert response.json()["reason_code"] == "insufficient_evidence"
