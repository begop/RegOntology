from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from neo4j import Driver, GraphDatabase, ManagedTransaction
from neo4j.exceptions import DriverError, Neo4jError

from app.domain.errors import ConfigurationError
from app.domain.graph import GraphProjectionStatus
from app.domain.models import KnowledgeSnapshot

_CONNECTION_TIMEOUT_SECONDS = 1.0
_CONNECTION_ACQUISITION_TIMEOUT_SECONDS = 1.0
_MAX_TRANSACTION_RETRY_SECONDS = 1.0
_ADDRESS_RESOLUTION_ERROR_PREFIX = "Cannot resolve address "


def _is_runtime_connectivity_error(error: Exception) -> bool:
    if isinstance(error, DriverError | Neo4jError):
        return True
    return isinstance(error, ValueError) and str(error).startswith(
        _ADDRESS_RESOLUTION_ERROR_PREFIX
    )


class Neo4jProjectionAdapter:
    """Rebuildable projection writer using only fixed, parameterized Cypher templates."""

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        *,
        driver: Driver | None = None,
    ):
        self._driver = driver or GraphDatabase.driver(
            uri,
            auth=(user, password),
            connection_timeout=_CONNECTION_TIMEOUT_SECONDS,
            connection_acquisition_timeout=_CONNECTION_ACQUISITION_TIMEOUT_SECONDS,
            max_transaction_retry_time=_MAX_TRANSACTION_RETRY_SECONDS,
        )

    def healthcheck(self) -> bool:
        try:
            self._driver.verify_connectivity()
        except (DriverError, Neo4jError, ValueError) as exc:
            if not _is_runtime_connectivity_error(exc):
                raise
            raise ConfigurationError("Neo4j projection is unavailable.") from exc
        return True

    def replace_projection(self, snapshot: KnowledgeSnapshot) -> dict[str, Any]:
        nodes: list[dict[str, object]] = [
            {
                "id": node.id,
                "type": node.type,
                "label": node.label,
                "security_class": node.security_class.value,
                "source_document_ids": list(node.source_document_ids),
            }
            for node in snapshot.ontology_nodes.values()
        ]
        edges: list[dict[str, object]] = [
            {
                "id": edge.id,
                "type": edge.type,
                "source": edge.source,
                "target": edge.target,
                "source_document": edge.source_document,
                "source_locator": edge.source_locator,
                "review_status": edge.review_status,
            }
            for edge in snapshot.ontology_edges
        ]
        try:
            with self._driver.session() as session:
                session.execute_write(
                    self._replace_projection_tx,
                    nodes=nodes,
                    edges=edges,
                    publication_id=snapshot.publication_id,
                    node_count=len(nodes),
                    edge_count=len(edges),
                )
        except (DriverError, Neo4jError, ValueError) as exc:
            if not _is_runtime_connectivity_error(exc):
                raise
            raise ConfigurationError("Neo4j projection rebuild failed.") from exc
        return {
            "publication_id": snapshot.publication_id,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    @staticmethod
    def _replace_projection_tx(
        transaction: ManagedTransaction,
        *,
        nodes: list[dict[str, object]],
        edges: list[dict[str, object]],
        publication_id: str,
        node_count: int,
        edge_count: int,
    ) -> None:
        transaction.run(
            "MATCH (n:OntologyEntity {publication_id: $publication_id}) DETACH DELETE n",
            publication_id=publication_id,
        ).consume()
        transaction.run(
            """
            UNWIND $nodes AS row
            MERGE (n:OntologyEntity {id: row.id, publication_id: $publication_id})
            SET n.type = row.type,
                n.label = row.label,
                n.security_class = row.security_class,
                n.source_document_ids = row.source_document_ids
            """,
            nodes=nodes,
            publication_id=publication_id,
        ).consume()
        transaction.run(
            """
            UNWIND $edges AS row
            MATCH (source:OntologyEntity {id: row.source, publication_id: $publication_id})
            MATCH (target:OntologyEntity {id: row.target, publication_id: $publication_id})
            MERGE (source)-[edge:ONTOLOGY_RELATION {
              id: row.id, publication_id: $publication_id
            }]->(target)
            SET edge.type = row.type,
                edge.source_document = row.source_document,
                edge.source_locator = row.source_locator,
                edge.review_status = row.review_status
            """,
            edges=edges,
            publication_id=publication_id,
        ).consume()
        transaction.run(
            """
            MERGE (watermark:ProjectionWatermark {name: 'active'})
            SET watermark.publication_id = $publication_id,
                watermark.node_count = $node_count,
                watermark.edge_count = $edge_count
            """,
            publication_id=publication_id,
            node_count=node_count,
            edge_count=edge_count,
        ).consume()

    def status(self, expected_publication_id: str) -> GraphProjectionStatus:
        query = """
            MATCH (watermark:ProjectionWatermark {name: 'active'})
            RETURN watermark.publication_id AS publication_id
            LIMIT 1
        """
        try:
            with self._driver.session() as session:
                record = session.run(query).single()
        except (DriverError, Neo4jError, ValueError) as exc:
            if not _is_runtime_connectivity_error(exc):
                raise
            return GraphProjectionStatus(status="unavailable", publication_id=None)
        projected = record.get("publication_id") if record is not None else None
        if not isinstance(projected, str):
            return GraphProjectionStatus(status="stale", publication_id=None)
        return GraphProjectionStatus(
            status="healthy" if projected == expected_publication_id else "stale",
            publication_id=projected,
        )

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
        bounded_seed_ids = seed_ids[:200]
        bounded_node_ids = allowed_node_ids[:1_000]
        bounded_edge_ids = allowed_edge_ids[:800]
        bounded_document_ids = allowed_document_ids[:200]
        bounded_relation_types = relation_types[:100]
        bounded_max_edges = max(1, min(max_edges, 400))
        if not all((bounded_seed_ids, bounded_node_ids, bounded_edge_ids, bounded_document_ids)):
            return ()
        query = """
            MATCH (seed:OntologyEntity {publication_id: $publication_id})
                  -[edge:ONTOLOGY_RELATION]-(neighbor:OntologyEntity {
                    publication_id: $publication_id
                  })
            WHERE seed.id IN $seed_ids
              AND seed.id IN $allowed_node_ids
              AND neighbor.id IN $allowed_node_ids
              AND edge.id IN $allowed_edge_ids
              AND edge.source_document IN $allowed_document_ids
              AND edge.review_status = 'APPROVED'
              AND ($relation_types = [] OR edge.type IN $relation_types)
            WITH DISTINCT edge
            RETURN edge.id AS edge_id,
                   startNode(edge).id AS source,
                   edge.type AS type,
                   endNode(edge).id AS target,
                   edge.source_document AS source_document,
                   edge.source_locator AS source_locator,
                   edge.review_status AS review_status
            ORDER BY edge.id
            LIMIT $max_edges
        """
        try:
            with self._driver.session() as session:
                result = session.run(
                    query,
                    publication_id=publication_id,
                    seed_ids=list(bounded_seed_ids),
                    allowed_node_ids=list(bounded_node_ids),
                    allowed_edge_ids=list(bounded_edge_ids),
                    allowed_document_ids=list(bounded_document_ids),
                    relation_types=list(bounded_relation_types),
                    max_edges=bounded_max_edges,
                )
                return tuple(dict(record) for record in result)
        except (DriverError, Neo4jError, ValueError) as exc:
            if not _is_runtime_connectivity_error(exc):
                raise
            raise ConfigurationError("Neo4j bounded query failed.") from exc

    def close(self) -> None:
        self._driver.close()
