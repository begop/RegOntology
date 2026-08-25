from __future__ import annotations

import hashlib
import json
import re
import threading
from collections import defaultdict
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from app.domain.errors import ConfigurationError, NotFoundError
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

_CHAPTER_RE = re.compile(r"^##\s+제(\d+)장\s*(.*)$")
_ARTICLE_RE = re.compile(r"^###\s+제(\d+)조(?:\(([^)]*)\))?\s*$")
_PARAGRAPH_RE = re.compile(r"^(\d+)\.\s+(.+)$")


def _frontmatter_value(raw: str) -> Any:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    if value.lower() in {"null", "none", "~"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], list[str], int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ConfigurationError("Mock regulation is missing YAML frontmatter.")
    try:
        closing = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ConfigurationError("Mock regulation frontmatter is not closed.") from exc
    metadata: dict[str, Any] = {}
    for line in lines[1:closing]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ConfigurationError("Mock regulation frontmatter contains an invalid field.")
        metadata[key.strip()] = _frontmatter_value(value)
    return metadata, lines[closing + 1 :], closing + 2


def _as_date(value: Any, field_name: str, required: bool = False) -> date | None:
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f"{field_name} must be an ISO date.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigurationError(f"{field_name} must be an ISO date.") from exc


class MockKnowledgeRepository:
    """Immutable, reloadable projection parsed from the repository's seven mock files."""

    mode = "mock_snapshot"

    def __init__(self, mock_data_dir: Path):
        self._mock_data_dir = mock_data_dir
        self._lock = threading.RLock()
        self._snapshot = self._load()

    @property
    def snapshot(self) -> KnowledgeSnapshot:
        with self._lock:
            return self._snapshot

    def reload(self) -> KnowledgeSnapshot:
        candidate = self._load()
        with self._lock:
            self._snapshot = candidate
            return candidate

    def healthcheck(self) -> bool:
        return bool(self.snapshot.documents)

    def _load(self) -> KnowledgeSnapshot:
        regulation_dir = self._mock_data_dir / "regulations"
        files = sorted(regulation_dir.glob("*.md"))
        if not files:
            raise ConfigurationError("No mock regulation files were found.")

        documents: dict[str, RegulationDocument] = {}
        versions: dict[str, RegulationVersion] = {}
        provisions: dict[str, Provision] = {}
        provisions_by_version: dict[str, tuple[str, ...]] = {}
        manifest_parts: list[bytes] = []

        for path in files:
            raw = path.read_bytes()
            manifest_parts.append(path.name.encode("utf-8") + raw)
            document, version, parsed = self._parse_regulation(path, raw)
            existing = documents.get(document.id)
            if existing and replace(existing) != replace(document):
                comparable_fields = (
                    existing.title == document.title
                    and existing.owner_org == document.owner_org
                    and existing.security_class == document.security_class
                )
                if not comparable_fields:
                    raise ConfigurationError(
                        "Document metadata changed across immutable mock versions."
                    )
            documents[document.id] = document
            if version.id in versions:
                raise ConfigurationError("Duplicate mock regulation version.")
            versions[version.id] = version
            provisions.update({item.id: item for item in parsed})
            provisions_by_version[version.id] = tuple(item.id for item in parsed)

        versions_by_document: dict[str, tuple[str, ...]] = {}
        for document_id in documents:
            ordered = sorted(
                (version for version in versions.values() if version.document_id == document_id),
                key=lambda item: (item.effective_from, item.version_label),
            )
            for previous, current in zip(ordered, ordered[1:], strict=False):
                if previous.effective_to is None or previous.effective_to > current.effective_from:
                    raise ConfigurationError("Published mock version effective periods overlap.")
            versions_by_document[document_id] = tuple(item.id for item in ordered)

        ontology_raw = (self._mock_data_dir / "ontology" / "ontology_seed.json").read_bytes()
        evaluation_raw = (self._mock_data_dir / "evaluation" / "qa_gold.jsonl").read_bytes()
        manifest_parts.extend([ontology_raw, evaluation_raw])
        ontology = json.loads(ontology_raw)
        edges = tuple(OntologyEdge(**raw_edge) for raw_edge in ontology["edges"])
        source_documents: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            source_documents[edge.source].add(edge.source_document)
            source_documents[edge.target].add(edge.source_document)
        nodes = {
            raw_node["id"]: OntologyNode(
                id=raw_node["id"],
                type=raw_node["type"],
                label=raw_node["label"],
                security_class=SecurityClass(raw_node["security_class"]),
                properties={
                    key: value
                    for key, value in raw_node.items()
                    if key not in {"id", "type", "label", "security_class"}
                },
                source_document_ids=frozenset(source_documents[raw_node["id"]]),
            )
            for raw_node in ontology["nodes"]
        }
        digest = hashlib.sha256(b"\n".join(manifest_parts)).hexdigest()
        publication_id = f"mock-{digest[:20]}"
        return KnowledgeSnapshot(
            publication_id=publication_id,
            graph_watermark=publication_id,
            loaded_at=datetime.now(UTC),
            documents=documents,
            versions=versions,
            versions_by_document=versions_by_document,
            provisions=provisions,
            provisions_by_version=provisions_by_version,
            ontology_nodes=nodes,
            ontology_edges=edges,
        )

    def _parse_regulation(
        self, path: Path, raw: bytes
    ) -> tuple[RegulationDocument, RegulationVersion, tuple[Provision, ...]]:
        text = raw.decode("utf-8-sig")
        metadata, body_lines, first_body_line = _parse_frontmatter(text)
        required = {
            "document_id",
            "title",
            "institution",
            "version",
            "status",
            "effective_from",
            "security_class",
            "owner_org",
            "is_mock",
        }
        if missing := required.difference(metadata):
            raise ConfigurationError(f"Mock regulation metadata is incomplete: {sorted(missing)}")
        document_id = str(metadata["document_id"])
        version_label = str(metadata["version"])
        version_id = f"{document_id}:v{version_label}"
        security_class = SecurityClass(str(metadata["security_class"]).lower())
        document = RegulationDocument(
            id=document_id,
            document_code=document_id,
            title=str(metadata["title"]),
            institution=str(metadata["institution"]),
            document_type="internal_policy",
            owner_org=str(metadata["owner_org"]),
            security_class=security_class,
            status="active",
            is_mock=bool(metadata["is_mock"]),
        )
        supersedes = metadata.get("supersedes")
        version = RegulationVersion(
            id=version_id,
            document_id=document_id,
            version_label=version_label,
            promulgated_on=_as_date(metadata.get("promulgated_on"), "promulgated_on"),
            effective_from=_as_date(metadata["effective_from"], "effective_from", required=True),  # type: ignore[arg-type]
            effective_to=_as_date(metadata.get("effective_to"), "effective_to"),
            status=str(metadata["status"]).lower(),
            supersedes_version_id=(f"{document_id}:v{supersedes}" if supersedes else None),
            source_sha256=hashlib.sha256(raw).hexdigest(),
            source_name=path.name,
            is_mock=bool(metadata["is_mock"]),
        )
        return (
            document,
            version,
            self._parse_provisions(body_lines, first_body_line, document, version),
        )

    @staticmethod
    def _parse_provisions(
        lines: list[str],
        first_line: int,
        document: RegulationDocument,
        version: RegulationVersion,
    ) -> tuple[Provision, ...]:
        records: list[dict[str, Any]] = []
        current_chapter: dict[str, Any] | None = None
        current_article: dict[str, Any] | None = None
        for offset, raw_line in enumerate(lines):
            line = raw_line.strip()
            chapter_match = _CHAPTER_RE.match(line)
            if chapter_match:
                number = int(chapter_match.group(1))
                path = f"ch-{number}"
                current_chapter = {
                    "id": f"{version.id}:{path}",
                    "parent_id": None,
                    "level": ProvisionLevel.CHAPTER,
                    "ordinal": number,
                    "canonical_path": path,
                    "locator": f"제{number}장",
                    "title": chapter_match.group(2).strip() or None,
                    "body": "",
                    "source_line": first_line + offset,
                }
                records.append(current_chapter)
                current_article = None
                continue
            article_match = _ARTICLE_RE.match(line)
            if article_match:
                if current_chapter is None:
                    raise ConfigurationError("Article appears before a chapter in mock data.")
                number = int(article_match.group(1))
                path = f"art-{number}"
                current_article = {
                    "id": f"{version.id}:{path}",
                    "parent_id": current_chapter["id"],
                    "level": ProvisionLevel.ARTICLE,
                    "ordinal": number,
                    "canonical_path": path,
                    "locator": f"제{number}조",
                    "title": article_match.group(2) or None,
                    "body": "",
                    "source_line": first_line + offset,
                }
                records.append(current_article)
                continue
            paragraph_match = _PARAGRAPH_RE.match(line)
            if paragraph_match and current_article is not None:
                number = int(paragraph_match.group(1))
                body = paragraph_match.group(2).strip()
                path = f"{current_article['canonical_path']}/p-{number}"
                records.append(
                    {
                        "id": f"{version.id}:{path}",
                        "parent_id": current_article["id"],
                        "level": ProvisionLevel.PARAGRAPH,
                        "ordinal": number,
                        "canonical_path": path,
                        "locator": f"{current_article['locator']} 제{number}항",
                        "title": None,
                        "body": body,
                        "source_line": first_line + offset,
                    }
                )

        article_bodies: dict[str, list[str]] = {}
        for record in records:
            if record["level"] == ProvisionLevel.PARAGRAPH and record["parent_id"]:
                article_bodies.setdefault(record["parent_id"], []).append(record["body"])
        for record in records:
            if record["level"] == ProvisionLevel.ARTICLE:
                record["body"] = "\n".join(article_bodies.get(record["id"], []))

        return tuple(
            Provision(
                document_id=document.id,
                version_id=version.id,
                security_class=document.security_class,
                is_mock=document.is_mock,
                body_sha256=hashlib.sha256(record["body"].encode("utf-8")).hexdigest(),
                **record,
            )
            for record in records
        )

    def versions_for_document(self, document_id: str) -> tuple[RegulationVersion, ...]:
        snapshot = self.snapshot
        if document_id not in snapshot.documents:
            raise NotFoundError()
        return tuple(
            snapshot.versions[version_id]
            for version_id in snapshot.versions_by_document[document_id]
        )

    def effective_version(self, document_id: str, as_of: date) -> RegulationVersion | None:
        matches = [
            version
            for version in self.versions_for_document(document_id)
            if version.is_effective(as_of)
        ]
        if len(matches) > 1:
            raise ConfigurationError("More than one regulation version is effective.")
        return matches[0] if matches else None

    def active_provisions(
        self,
        as_of: date,
        principal: Principal,
        document_ids: frozenset[str] | None = None,
    ) -> tuple[Provision, ...]:
        snapshot = self.snapshot
        selected: list[Provision] = []
        for document in snapshot.documents.values():
            if document_ids is not None and document.id not in document_ids:
                continue
            if not principal.can_read(document.id, document.security_class):
                continue
            version = self.effective_version(document.id, as_of)
            if version is None:
                continue
            selected.extend(
                snapshot.provisions[item_id]
                for item_id in snapshot.provisions_by_version[version.id]
                if snapshot.provisions[item_id].level == ProvisionLevel.PARAGRAPH
            )
        return tuple(selected)

    def find_article_paragraphs(
        self, document_id: str, article_number: int, as_of: date, principal: Principal
    ) -> tuple[Provision, ...]:
        snapshot = self.snapshot
        document = snapshot.documents.get(document_id)
        if document is None or not principal.can_read(document.id, document.security_class):
            return ()
        version = self.effective_version(document_id, as_of)
        if version is None:
            return ()
        prefix = f"art-{article_number}/p-"
        return tuple(
            snapshot.provisions[item_id]
            for item_id in snapshot.provisions_by_version[version.id]
            if snapshot.provisions[item_id].canonical_path.startswith(prefix)
        )
