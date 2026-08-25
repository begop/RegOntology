from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

from app.application.ports import KnowledgeRepository
from app.domain.models import OntologyEdge, Principal

_LOCATOR_ANCHOR_RE = re.compile(r"제(\d+)조(?:\s*제(\d+)항)?")


@dataclass(frozen=True, slots=True)
class GraphAccessScope:
    """Canonical PostgreSQL-derived policy inputs for bounded graph templates."""

    publication_id: str
    document_ids: tuple[str, ...]
    node_ids: tuple[str, ...]
    approved_edges: tuple[OntologyEdge, ...]

    def candidate_edges(
        self,
        seed_ids: Iterable[str],
        relation_types: frozenset[str] | None,
        limit: int,
    ) -> tuple[OntologyEdge, ...]:
        seeds = frozenset(seed_ids)
        if not seeds or limit <= 0:
            return ()
        return tuple(
            edge
            for edge in self.approved_edges
            if (edge.source in seeds or edge.target in seeds)
            and (not relation_types or edge.type in relation_types)
        )[:limit]

    def verify_rows(
        self,
        rows: Iterable[Mapping[str, object]],
        candidate_edges: Iterable[OntologyEdge],
    ) -> tuple[OntologyEdge, ...]:
        candidates = {edge.id: edge for edge in candidate_edges}
        verified: list[OntologyEdge] = []
        seen: set[str] = set()
        for row in rows:
            edge_id = row.get("edge_id")
            if not isinstance(edge_id, str) or edge_id in seen:
                continue
            edge = candidates.get(edge_id)
            if edge is None:
                continue
            expected = {
                "edge_id": edge.id,
                "type": edge.type,
                "source": edge.source,
                "target": edge.target,
                "source_document": edge.source_document,
                "source_locator": edge.source_locator,
                "review_status": "APPROVED",
            }
            if all(row.get(key) == value for key, value in expected.items()):
                verified.append(edge)
                seen.add(edge_id)
        return tuple(verified)


def compile_graph_access_scope(
    repository: KnowledgeRepository,
    principal: Principal,
    as_of: date,
    requested_document_ids: frozenset[str] | None = None,
) -> GraphAccessScope:
    """Compile document/security/time policy before any Neo4j candidate query."""

    snapshot = repository.snapshot
    effective_versions = {
        document.id: version
        for document in snapshot.documents.values()
        if (requested_document_ids is None or document.id in requested_document_ids)
        and principal.can_read(document.id, document.security_class)
        and (version := repository.effective_version(document.id, as_of)) is not None
    }
    allowed_documents = tuple(sorted(effective_versions))
    allowed_document_set = frozenset(allowed_documents)
    active_locators = {
        document_id: frozenset(
            snapshot.provisions[provision_id].locator
            for provision_id in snapshot.provisions_by_version[version.id]
        )
        for document_id, version in effective_versions.items()
    }
    provenance_edges = tuple(
        edge
        for edge in snapshot.ontology_edges
        if edge.review_status == "APPROVED"
        and edge.source_document in allowed_document_set
        and _has_active_provenance(
            edge.source_locator,
            active_locators[edge.source_document],
        )
    )
    approved_sources_by_node: dict[str, set[str]] = {}
    for edge in provenance_edges:
        approved_sources_by_node.setdefault(edge.source, set()).add(edge.source_document)
        approved_sources_by_node.setdefault(edge.target, set()).add(edge.source_document)
    allowed_nodes = tuple(
        sorted(
            node.id
            for node in snapshot.ontology_nodes.values()
            if node.security_class in principal.allowed_security_classes
            and bool(approved_sources_by_node.get(node.id))
        )
    )
    allowed_node_set = frozenset(allowed_nodes)
    approved_edges = tuple(
        sorted(
            (
                edge
                for edge in provenance_edges
                if edge.source_document in allowed_document_set
                and edge.source in allowed_node_set
                and edge.target in allowed_node_set
            ),
            key=lambda edge: edge.id,
        )
    )
    return GraphAccessScope(
        publication_id=snapshot.publication_id,
        document_ids=allowed_documents,
        node_ids=allowed_nodes,
        approved_edges=approved_edges,
    )


def _has_active_provenance(source_locator: str, active_locators: frozenset[str]) -> bool:
    if source_locator == "metadata":
        return True
    anchor_match = _LOCATOR_ANCHOR_RE.search(source_locator)
    if anchor_match is None:
        return False
    anchor = f"제{anchor_match.group(1)}조"
    if anchor_match.group(2):
        anchor += f" 제{anchor_match.group(2)}항"
    return anchor in active_locators
