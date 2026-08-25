from __future__ import annotations

from datetime import date
from pathlib import Path

from app.domain.models import Principal, ProvisionLevel, SecurityClass
from app.infrastructure.mock_repository import MockKnowledgeRepository


def test_parser_preserves_expected_structure(mock_data_dir: Path) -> None:
    repository = MockKnowledgeRepository(mock_data_dir)
    snapshot = repository.snapshot

    expected_paragraphs = {
        "MOCK-EFO-001:v1.0": 17,
        "MOCK-ISP-001:v1.0": 17,
        "MOCK-ISP-001:v1.1": 17,
        "MOCK-PIP-001:v1.0": 18,
    }
    assert len(snapshot.documents) == 3
    assert len(snapshot.versions) == 4
    for version_id, paragraph_count in expected_paragraphs.items():
        provisions = [
            snapshot.provisions[item_id] for item_id in snapshot.provisions_by_version[version_id]
        ]
        assert sum(item.level == ProvisionLevel.CHAPTER for item in provisions) == 3
        assert sum(item.level == ProvisionLevel.ARTICLE for item in provisions) == 7
        assert sum(item.level == ProvisionLevel.PARAGRAPH for item in provisions) == paragraph_count


def test_effective_date_selection_is_exclusive_at_end(mock_data_dir: Path) -> None:
    repository = MockKnowledgeRepository(mock_data_dir)

    assert repository.effective_version("MOCK-ISP-001", date(2025, 12, 31)) is None
    assert repository.effective_version("MOCK-ISP-001", date(2026, 6, 30)).version_label == "1.0"
    assert repository.effective_version("MOCK-ISP-001", date(2026, 7, 1)).version_label == "1.1"


def test_restricted_content_is_filtered_before_candidates(mock_data_dir: Path) -> None:
    repository = MockKnowledgeRepository(mock_data_dir)
    employee = Principal(
        subject="employee",
        role="employee",
        allowed_security_classes=frozenset({SecurityClass.PUBLIC, SecurityClass.INTERNAL}),
    )

    candidates = repository.active_provisions(date(2026, 8, 24), employee)

    assert candidates
    assert all(item.document_id != "MOCK-PIP-001" for item in candidates)
