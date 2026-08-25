from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _load_cases() -> list[dict[str, Any]]:
    path = Path(__file__).resolve().parents[2] / "mock-data" / "evaluation" / "qa_gold.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _headers(profile: str) -> dict[str, str]:
    if profile == "privacy_restricted":
        return {
            "X-Demo-Role": "compliance",
            "X-Demo-Security-Classes": "public,internal,restricted",
        }
    return {"X-Demo-Role": "employee", "X-Demo-Security-Classes": "public,internal"}


def _citation_key(citation: dict[str, Any]) -> tuple[str, str, str]:
    return citation["document_id"], citation["version_id"], citation["locator"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda item: item["id"])
def test_golden_qa_contract(client: TestClient, case: dict[str, Any]) -> None:
    response = client.post(
        "/api/v1/qa/queries",
        headers=_headers(case["principal_profile"]),
        json={"question": case["question"], "as_of": case["as_of"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == case["expected_status"]
    if case["expected_status"] == "abstained":
        assert body["reason_code"] == case["expected_reason"]
        assert body["citations"] == []
    else:
        answer = body["answer"] or ""
        for fact in case.get("required_facts", []):
            assert fact in answer
        citation_keys = [_citation_key(item) for item in body["citations"]]
        for expected in case.get("required_citations", []):
            source, locator = expected.split("#", maxsplit=1)
            if ":v" in source:
                document_id, version_suffix = source.split(":v", maxsplit=1)
                assert any(
                    document == document_id
                    and version == f"{document_id}:v{version_suffix}"
                    and actual_locator.startswith(locator)
                    for document, version, actual_locator in citation_keys
                )
            else:
                assert any(
                    document == source and actual_locator.startswith(locator)
                    for document, _, actual_locator in citation_keys
                )
        for forbidden in case.get("forbidden_facts", []):
            assert forbidden not in answer
    serialized = json.dumps(body["citations"], ensure_ascii=False)
    for forbidden in case.get("forbidden_citations", []):
        assert forbidden not in serialized
