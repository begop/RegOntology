from __future__ import annotations

import hashlib
import re
import uuid
from collections import deque
from datetime import date
from typing import Any

from app.application.graph_policy import GraphAccessScope, compile_graph_access_scope
from app.application.ports import (
    AuditLog,
    GenerationProvider,
    GraphQuery,
    KnowledgeRepository,
    QAResultStore,
)
from app.domain.errors import (
    ConfigurationError,
    ForbiddenError,
    InvalidRequestError,
    NotFoundError,
    ProviderUnavailableError,
)
from app.domain.models import (
    Citation,
    OntologyEdge,
    OntologyNode,
    Principal,
    Provision,
    ProvisionLevel,
    QAResult,
    RetrievalHit,
    SecurityClass,
)
from app.infrastructure.providers import grounded_normalization
from app.infrastructure.retrieval import HybridRetriever, lexical_similarity


class RegulationService:
    def __init__(self, repository: KnowledgeRepository, retriever: HybridRetriever):
        self.repository = repository
        self.retriever = retriever

    def list_regulations(
        self,
        *,
        principal: Principal,
        as_of: date,
        query: str | None,
        owner_org: str | None,
        security_class: SecurityClass | None,
        status: str | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        snapshot = self.repository.snapshot
        snippets: dict[str, str] = {}
        if query:
            for hit in self.retriever.retrieve(query, as_of, principal, limit=50):
                snippets.setdefault(hit.document.id, hit.provision.body)
        items: list[dict[str, Any]] = []
        for document in sorted(snapshot.documents.values(), key=lambda item: item.document_code):
            if not principal.can_read(document.id, document.security_class):
                continue
            if owner_org and document.owner_org != owner_org:
                continue
            if security_class and document.security_class != security_class:
                continue
            if status and document.status != status.lower():
                continue
            version = self.repository.effective_version(document.id, as_of)
            if version is None:
                continue
            if query:
                metadata_score = lexical_similarity(
                    query, f"{document.document_code} {document.title} {document.owner_org}"
                )
                if document.id not in snippets and metadata_score < 0.12:
                    continue
            items.append(
                {
                    "document_id": document.id,
                    "document_code": document.document_code,
                    "title": document.title,
                    "document_type": document.document_type,
                    "owner_org": document.owner_org,
                    "security_class": document.security_class.value,
                    "status": document.status,
                    "is_mock": document.is_mock,
                    "effective_version": self._version_dict(version),
                    "match_snippets": [snippets[document.id]] if document.id in snippets else [],
                }
            )
        return items[:limit], len(items)

    def get_document(self, document_id: str, principal: Principal) -> dict[str, Any]:
        snapshot = self.repository.snapshot
        document = snapshot.documents.get(document_id)
        if document is None or not principal.can_read(document.id, document.security_class):
            raise NotFoundError()
        versions = [
            self._version_dict(item)
            for item in self.repository.versions_for_document(document.id)
            if item.status == "published" or principal.role in {"curator", "admin"}
        ]
        return {
            "document_id": document.id,
            "document_code": document.document_code,
            "title": document.title,
            "institution": document.institution,
            "document_type": document.document_type,
            "owner_org": document.owner_org,
            "security_class": document.security_class.value,
            "status": document.status,
            "is_mock": document.is_mock,
            "versions": versions,
        }

    def get_version(
        self, document_id: str, version_id: str, principal: Principal
    ) -> dict[str, Any]:
        self.get_document(document_id, principal)
        snapshot = self.repository.snapshot
        version = snapshot.versions.get(version_id)
        if version is None or version.document_id != document_id:
            raise NotFoundError()
        if version.status != "published" and principal.role not in {"curator", "admin"}:
            raise NotFoundError()
        toc = [
            self._provision_dict(snapshot.provisions[item_id])
            for item_id in snapshot.provisions_by_version[version.id]
            if snapshot.provisions[item_id].level
            in {ProvisionLevel.CHAPTER, ProvisionLevel.ARTICLE}
        ]
        return {**self._version_dict(version), "document_id": document_id, "toc": toc}

    def get_provisions(
        self,
        *,
        document_id: str,
        version_id: str,
        principal: Principal,
        parent_id: str | None,
        locator: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        self.get_version(document_id, version_id, principal)
        snapshot = self.repository.snapshot
        items = [
            snapshot.provisions[item_id] for item_id in snapshot.provisions_by_version[version_id]
        ]
        if parent_id:
            items = [item for item in items if item.parent_id == parent_id]
        if locator:
            items = [
                item
                for item in items
                if item.locator == locator or item.locator.startswith(locator)
            ]
        return [self._provision_dict(item) for item in items[:limit]]

    def get_provision(self, provision_id: str, principal: Principal) -> dict[str, Any]:
        snapshot = self.repository.snapshot
        provision = snapshot.provisions.get(provision_id)
        if provision is None:
            raise NotFoundError()
        document = snapshot.documents[provision.document_id]
        if not principal.can_read(document.id, document.security_class):
            raise NotFoundError()
        version = snapshot.versions[provision.version_id]
        if version.status != "published" and principal.role not in {"curator", "admin"}:
            raise NotFoundError()
        breadcrumb: list[dict[str, str]] = []
        current = provision
        while current.parent_id:
            current = snapshot.provisions[current.parent_id]
            breadcrumb.append({"id": current.id, "locator": current.locator})
        breadcrumb.reverse()
        return {
            **self._provision_dict(provision),
            "breadcrumb": breadcrumb,
            "document_title": document.title,
            "version_label": version.version_label,
            "effective_from": version.effective_from.isoformat(),
            "effective_to": version.effective_to.isoformat() if version.effective_to else None,
        }

    @staticmethod
    def _version_dict(version: Any) -> dict[str, Any]:
        return {
            "version_id": version.id,
            "version_label": version.version_label,
            "promulgated_on": version.promulgated_on.isoformat()
            if version.promulgated_on
            else None,
            "effective_from": version.effective_from.isoformat(),
            "effective_to": version.effective_to.isoformat() if version.effective_to else None,
            "status": version.status,
            "supersedes_version_id": version.supersedes_version_id,
            "source_sha256": version.source_sha256,
            "is_mock": version.is_mock,
        }

    @staticmethod
    def _provision_dict(provision: Provision) -> dict[str, Any]:
        return {
            "provision_id": provision.id,
            "document_id": provision.document_id,
            "version_id": provision.version_id,
            "parent_id": provision.parent_id,
            "level": provision.level.value,
            "ordinal": provision.ordinal,
            "canonical_path": provision.canonical_path,
            "locator": provision.locator,
            "title": provision.title,
            "body": provision.body,
            "body_sha256": provision.body_sha256,
            "source_span": {"line": provision.source_line},
            "is_mock": provision.is_mock,
        }


class OntologyService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        graph_query: GraphQuery | None = None,
    ):
        self.repository = repository
        self.graph_query = graph_query

    def search(
        self,
        *,
        principal: Principal,
        query: str,
        types: frozenset[str] | None,
        as_of: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        scope = compile_graph_access_scope(self.repository, principal, as_of)
        allowed_node_ids = frozenset(scope.node_ids)
        nodes = [
            node
            for node in self.repository.snapshot.ontology_nodes.values()
            if node.id in allowed_node_ids
            and (not types or node.type in types)
            and lexical_similarity(query, node.label) >= 0.10
        ]
        nodes.sort(key=lambda item: (-lexical_similarity(query, item.label), item.id))
        return [self._node_dict(node, scope) for node in nodes[:limit]]

    def subgraph(
        self,
        *,
        principal: Principal,
        seed_ids: tuple[str, ...],
        relation_types: frozenset[str] | None,
        depth: int,
        max_nodes: int,
        as_of: date,
    ) -> dict[str, Any]:
        snapshot = self.repository.snapshot
        scope = compile_graph_access_scope(self.repository, principal, as_of)
        allowed_nodes = {
            node_id: node
            for node_id, node in snapshot.ontology_nodes.items()
            if node_id in frozenset(scope.node_ids)
        }
        if seed_ids:
            initial_ids = tuple(seed_id for seed_id in seed_ids if seed_id in allowed_nodes)
        else:
            initial_ids = tuple(sorted(allowed_nodes)[: min(50, max_nodes)])
        graph_status = "healthy"
        if self.graph_query is None:
            allowed_edges = tuple(
                edge
                for edge in scope.approved_edges
                if not relation_types or edge.type in relation_types
            )
        else:
            allowed_edges, graph_status = self._runtime_edges(
                scope,
                initial_ids,
                relation_types,
                depth,
                max_nodes,
            )
        frontier = deque((node_id, 0) for node_id in initial_ids)
        selected_ids: set[str] = set()
        truncated = False
        while frontier:
            node_id, current_depth = frontier.popleft()
            if node_id in selected_ids:
                continue
            if len(selected_ids) >= max_nodes:
                truncated = True
                break
            selected_ids.add(node_id)
            if current_depth >= depth:
                continue
            for edge in allowed_edges:
                neighbor = None
                if edge.source == node_id:
                    neighbor = edge.target
                elif edge.target == node_id:
                    neighbor = edge.source
                if neighbor in allowed_nodes and neighbor not in selected_ids:
                    frontier.append((neighbor, current_depth + 1))
        selected_edges = [
            edge
            for edge in allowed_edges
            if edge.source in selected_ids and edge.target in selected_ids
        ]
        return {
            "nodes": [
                self._node_dict(allowed_nodes[node_id], scope)
                for node_id in sorted(selected_ids)
            ],
            "edges": [self._edge_dict(edge) for edge in selected_edges],
            "truncated": truncated,
            "expansion_cursor": None,
            "publication_id": snapshot.publication_id,
            "graph_watermark": snapshot.graph_watermark,
            "graph_status": graph_status,
        }

    def _runtime_edges(
        self,
        scope: GraphAccessScope,
        initial_ids: tuple[str, ...],
        relation_types: frozenset[str] | None,
        depth: int,
        max_nodes: int,
    ) -> tuple[tuple[OntologyEdge, ...], str]:
        if self.graph_query is None or not initial_ids or not scope.document_ids:
            return (), "healthy"
        try:
            projection_status = self.graph_query.status(scope.publication_id)
        except ConfigurationError:
            return (), "unavailable"
        if not projection_status.healthy:
            return (), projection_status.status
        frontier = set(initial_ids)
        queried: set[str] = set()
        verified: dict[str, OntologyEdge] = {}
        remaining_edge_budget = min(400, max(1, max_nodes * 4))
        try:
            for _ in range(depth):
                current = tuple(sorted(frontier - queried))[:200]
                if not current or remaining_edge_budget <= 0:
                    break
                queried.update(current)
                candidates = scope.candidate_edges(
                    current,
                    relation_types,
                    remaining_edge_budget,
                )
                if not candidates:
                    break
                candidate_node_ids = tuple(
                    sorted(
                        frozenset(current)
                        | {edge.source for edge in candidates}
                        | {edge.target for edge in candidates}
                    )
                )
                rows = self.graph_query.one_hop(
                    publication_id=scope.publication_id,
                    seed_ids=current,
                    allowed_node_ids=candidate_node_ids,
                    allowed_edge_ids=tuple(edge.id for edge in candidates),
                    allowed_document_ids=tuple(
                        sorted({edge.source_document for edge in candidates})
                    ),
                    relation_types=tuple(sorted({edge.type for edge in candidates})),
                    max_edges=remaining_edge_budget,
                )
                accepted = scope.verify_rows(rows, candidates)
                for edge in accepted:
                    verified[edge.id] = edge
                    if edge.source in current:
                        frontier.add(edge.target)
                    if edge.target in current:
                        frontier.add(edge.source)
                remaining_edge_budget -= len(accepted)
        except ConfigurationError:
            return tuple(verified.values()), "unavailable"
        return tuple(verified.values()), "healthy"

    def node(self, node_id: str, principal: Principal, as_of: date) -> dict[str, Any]:
        scope = compile_graph_access_scope(self.repository, principal, as_of)
        node = self.repository.snapshot.ontology_nodes.get(node_id)
        if node is None or node_id not in frozenset(scope.node_ids):
            raise NotFoundError()
        graph = self.subgraph(
            principal=principal,
            seed_ids=(node_id,),
            relation_types=None,
            depth=1,
            max_nodes=50,
            as_of=as_of,
        )
        return {
            **self._node_dict(node, scope),
            "relations": graph["edges"],
            "review_status": "APPROVED",
        }

    @staticmethod
    def _node_dict(node: OntologyNode, scope: GraphAccessScope) -> dict[str, Any]:
        allowed_sources = sorted(
            {
                edge.source_document
                for edge in scope.approved_edges
                if edge.source == node.id or edge.target == node.id
            }
        )
        return {
            "id": node.id,
            "type": node.type,
            "label": node.label,
            "security_class": node.security_class.value,
            "properties": node.properties,
            "source_document_ids": allowed_sources,
        }

    @staticmethod
    def _edge_dict(edge: OntologyEdge) -> dict[str, Any]:
        return {
            "id": edge.id,
            "type": edge.type,
            "source": edge.source,
            "target": edge.target,
            "source_document": edge.source_document,
            "source_locator": edge.source_locator,
            "review_status": edge.review_status,
        }


class QAService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        retriever: HybridRetriever,
        generator: GenerationProvider,
        audit_log: AuditLog,
        result_store: QAResultStore,
        max_question_chars: int,
        graph_mode: str,
    ):
        self.repository = repository
        self.retriever = retriever
        self.generator = generator
        self.audit_log = audit_log
        self.result_store = result_store
        self.max_question_chars = max_question_chars
        self.graph_mode = graph_mode

    def answer(
        self,
        *,
        question: str,
        as_of: date,
        principal: Principal,
        document_ids: frozenset[str] | None,
        request_id: str,
    ) -> QAResult:
        normalized_question = " ".join(question.split())
        if len(normalized_question) < 2 or len(normalized_question) > self.max_question_chars:
            raise InvalidRequestError(details=[{"field": "question", "reason": "invalid_length"}])
        query_id = str(uuid.uuid4())
        hits, graph_status = self.retriever.retrieve_with_status(
            normalized_question,
            as_of,
            principal,
            document_ids=document_ids,
            limit=12,
        )
        top_relevance = hits[0].lane_scores.get("relevance", 0.0) if hits else 0.0
        if not hits or top_relevance < 0.20:
            reason = (
                "access_limited"
                if self.retriever.denied_scope_has_evidence(
                    normalized_question, as_of, principal, document_ids
                )
                else "insufficient_evidence"
            )
            result = self._abstain(query_id, as_of, reason, graph_status)
            return self._record(result, normalized_question, principal, request_id)

        selected = self._pack_primary_article(hits[0], hits, as_of, principal)
        selected = self._add_cross_references(selected, as_of, principal)
        try:
            generated = self.generator.generate(normalized_question, selected)
        except ProviderUnavailableError:
            result = self._abstain(query_id, as_of, "system_unavailable", graph_status)
            return self._record(result, normalized_question, principal, request_id)
        citations = tuple(
            Citation(
                index=index,
                source_id=f"src-{index}",
                document_id=hit.document.id,
                version_id=hit.version.id,
                provision_id=hit.provision.id,
                document_title=hit.document.title,
                version_label=hit.version.version_label,
                locator=hit.provision.locator,
                quote=hit.provision.body,
            )
            for index, hit in enumerate(selected, start=1)
        )
        if not self._verify(generated.claims, selected):
            result = self._abstain(query_id, as_of, "insufficient_evidence", graph_status)
            return self._record(result, normalized_question, principal, request_id)
        snapshot = self.repository.snapshot
        answer = self._render_verified_claims(generated.claims)
        result = QAResult(
            query_id=query_id,
            status="answered",
            answer=answer,
            as_of=as_of,
            citations=citations,
            warnings=self._safe_warnings(generated.warnings, selected, graph_status),
            reason_code=None,
            suggested_actions=("최종 업무 판단은 담당 부서에 확인해 주세요.",),
            trace={
                "publication_id": snapshot.publication_id,
                "graph_watermark": snapshot.graph_watermark,
                "graph_mode": self.graph_mode,
                "graph_status": graph_status,
                "repository_mode": self.repository.mode,
                "retriever_version": "hybrid-rrf-v1",
                "embedding_profile": self.retriever._embedding_provider.profile_id,
                "generation_model": self.generator.model_id,
                "prompt_version": "grounded-qa-v1",
                "source_count": len(selected),
                "lanes": [sorted(hit.lane_scores) for hit in selected],
            },
        )
        return self._record(result, normalized_question, principal, request_id)

    def _pack_primary_article(
        self,
        primary: RetrievalHit,
        hits: tuple[RetrievalHit, ...],
        as_of: date,
        principal: Principal,
    ) -> list[RetrievalHit]:
        del as_of, principal
        snapshot = self.repository.snapshot
        known_hits = {hit.provision.id: hit for hit in hits}
        sibling_ids = [
            item_id
            for item_id in snapshot.provisions_by_version[primary.version.id]
            if snapshot.provisions[item_id].parent_id == primary.provision.parent_id
            and snapshot.provisions[item_id].level == ProvisionLevel.PARAGRAPH
        ]
        packed: list[RetrievalHit] = []
        for item_id in sibling_ids:
            if item_id in known_hits:
                packed.append(known_hits[item_id])
                continue
            provision = snapshot.provisions[item_id]
            packed.append(
                RetrievalHit(
                    provision=provision,
                    document=primary.document,
                    version=primary.version,
                    score=0.0,
                    lane_scores={
                        "context_pack": 1.0,
                        "relevance": top_relevance_or_default(primary),
                    },
                )
            )
        return packed or [primary]

    def get(self, query_id: str, principal: Principal) -> QAResult:
        stored = self.result_store.get(query_id)
        if stored is None or (
            stored.owner_subject != principal.subject and principal.role not in {"auditor", "admin"}
        ):
            raise NotFoundError()
        result = stored.result
        snapshot = self.repository.snapshot
        if any(
            (document := snapshot.documents.get(citation.document_id)) is None
            or citation.version_id not in snapshot.versions
            or citation.provision_id not in snapshot.provisions
            or not principal.can_read(citation.document_id, document.security_class)
            for citation in result.citations
        ):
            raise NotFoundError()
        return result

    def _add_cross_references(
        self, selected: list[RetrievalHit], as_of: date, principal: Principal
    ) -> list[RetrievalHit]:
        snapshot = self.repository.snapshot
        existing_ids = {hit.provision.id for hit in selected}
        title_to_id = {document.title: document.id for document in snapshot.documents.values()}
        additions: list[RetrievalHit] = []
        for hit in selected:
            references: list[tuple[str, str]] = []
            for title, document_id in title_to_id.items():
                match = re.search(rf"{re.escape(title)}\s*제(\d+)조", hit.provision.body)
                if match:
                    references.append((document_id, match.group(1)))
            for document_id, article_number in references:
                for provision in self.repository.find_article_paragraphs(
                    document_id, int(article_number), as_of, principal
                ):
                    if provision.id in existing_ids or len(selected) + len(additions) >= 7:
                        continue
                    additions.append(
                        RetrievalHit(
                            provision=provision,
                            document=snapshot.documents[provision.document_id],
                            version=snapshot.versions[provision.version_id],
                            score=0.0,
                            lane_scores={"cross_reference": 1.0, "relevance": 0.30},
                        )
                    )
                    existing_ids.add(provision.id)
        return [*selected, *additions]

    @staticmethod
    def _verify(claims: tuple[Any, ...], sources: list[RetrievalHit]) -> bool:
        allowed = {f"src-{index}": hit for index, hit in enumerate(sources, start=1)}
        if not claims:
            return False
        for claim in claims:
            if not claim.citation_ids or any(item not in allowed for item in claim.citation_ids):
                return False
            source_text = " ".join(allowed[item].provision.body for item in claim.citation_ids)
            trusted_normalization = grounded_normalization(source_text)
            if claim.text not in source_text and claim.text != trusted_normalization:
                return False
            claim_numbers = set(re.findall(r"\d+", claim.text))
            if not claim_numbers.issubset(set(re.findall(r"\d+", source_text))):
                return False
        return True

    @staticmethod
    def _render_verified_claims(claims: tuple[Any, ...]) -> str:
        rendered: list[str] = []
        for claim in claims:
            citation_indexes = ",".join(
                citation_id.removeprefix("src-") for citation_id in claim.citation_ids
            )
            rendered.append(f"{claim.text} [{citation_indexes}]")
        return " ".join(rendered)

    @staticmethod
    def _safe_warnings(
        provider_warnings: tuple[str, ...],
        sources: list[RetrievalHit],
        graph_status: str,
    ) -> tuple[str, ...]:
        allowed_provider_warnings = {"degraded_graph", "partial_context"}
        warnings = [
            warning for warning in provider_warnings if warning in allowed_provider_warnings
        ]
        if graph_status != "healthy":
            warnings.append("degraded_graph")
        if any(source.document.is_mock for source in sources):
            warnings.append("mock_data")
        warnings.append("reference_only")
        return tuple(dict.fromkeys(warnings))

    def _record(
        self,
        result: QAResult,
        question: str,
        principal: Principal,
        request_id: str,
    ) -> QAResult:
        question_sha256 = hashlib.sha256(question.encode("utf-8")).hexdigest()
        self.result_store.save(
            result,
            owner_subject=principal.subject,
            request_id=request_id,
            question_sha256=question_sha256,
        )
        self.audit_log.append(
            actor_subject=principal.subject,
            action="qa.query",
            target_type="qa_run",
            target_id=result.query_id,
            request_id=request_id,
            outcome=result.status,
            metadata={
                "question_sha256": question_sha256,
                "as_of": result.as_of.isoformat(),
                "reason_code": result.reason_code,
            },
        )
        return result

    def _abstain(
        self,
        query_id: str,
        as_of: date,
        reason: str,
        graph_status: str = "healthy",
    ) -> QAResult:
        actions = {
            "access_limited": ("현재 접근 범위에서 확인 가능한 담당 부서에 문의해 주세요.",),
            "system_unavailable": ("잠시 후 다시 시도하거나 규정 원문 검색을 이용해 주세요.",),
            "insufficient_evidence": ("규정명, 업무 범위 또는 기준일을 구체화해 주세요.",),
        }
        snapshot = self.repository.snapshot
        return QAResult(
            query_id=query_id,
            status="abstained",
            answer=None,
            as_of=as_of,
            citations=(),
            warnings=(
                *(("degraded_graph",) if graph_status != "healthy" else ()),
                "mock_data",
                "reference_only",
            ),
            reason_code=reason,
            suggested_actions=actions.get(reason, ("담당 부서에 문의해 주세요.",)),
            trace={
                "publication_id": snapshot.publication_id,
                "graph_watermark": snapshot.graph_watermark,
                "graph_mode": self.graph_mode,
                "graph_status": graph_status,
                "repository_mode": self.repository.mode,
                "retriever_version": "hybrid-rrf-v1",
                "embedding_profile": self.retriever._embedding_provider.profile_id,
                "generation_model": self.generator.model_id,
                "prompt_version": "grounded-qa-v1",
                "source_count": 0,
                "lanes": [],
            },
        )


def require_role(principal: Principal, *roles: str) -> None:
    if principal.role not in roles:
        raise ForbiddenError()


def top_relevance_or_default(hit: RetrievalHit) -> float:
    return max(0.20, hit.lane_scores.get("relevance", 0.0))
