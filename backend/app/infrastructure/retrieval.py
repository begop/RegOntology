from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import defaultdict
from datetime import date

from app.application.graph_policy import compile_graph_access_scope
from app.application.ports import GraphQuery, KnowledgeRepository
from app.domain.errors import ConfigurationError
from app.domain.models import OntologyEdge, Principal, Provision, RetrievalHit

_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
_LOCATOR_RE = re.compile(r"제(\d+)조(?:\s*제(\d+)항)?")
_STOP_TERMS = {
    "경우",
    "관련",
    "기준",
    "무엇",
    "어떤",
    "언제",
    "얼마나",
    "알려",
    "누가",
    "하나",
}
_SUFFIXES = (
    "알려주세요",
    "무엇인가요",
    "해야하나요",
    "해야",
    "되나요",
    "인가요",
    "하나요",
    "에서는",
    "으로",
    "에서",
    "부터",
    "까지",
    "마다",
    "하고",
    "하며",
    "받아야",
    "이내에",
    "안에",
    "기간과",
    "주기는",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "과",
    "와",
    "의",
    "에",
)


def normalize_text(text: str) -> str:
    return " ".join(_TOKEN_RE.findall(unicodedata.normalize("NFKC", text).lower()))


def _character_ngrams(text: str, size: int = 2) -> set[str]:
    compact = normalize_text(text).replace(" ", "")
    if len(compact) <= size:
        return {compact} if compact else set()
    return {compact[index : index + size] for index in range(len(compact) - size + 1)}


def _terms(text: str) -> tuple[str, ...]:
    result: list[str] = []
    for raw_token in normalize_text(text).split():
        token = raw_token
        for suffix in _SUFFIXES:
            if token.endswith(suffix) and len(token) - len(suffix) >= 2:
                token = token[: -len(suffix)]
                break
        if len(token) >= 2 and token not in _STOP_TERMS:
            result.append(token)
    return tuple(result)


def _term_similarity(query_term: str, target_term: str) -> float:
    if query_term == target_term:
        return 1.0
    if query_term in target_term or target_term in query_term:
        return min(len(query_term), len(target_term)) / max(len(query_term), len(target_term))
    query_grams = _character_ngrams(query_term, 2)
    target_grams = _character_ngrams(target_term, 2)
    return len(query_grams & target_grams) / max(1, len(query_grams | target_grams))


class DeterministicEmbeddingProvider:
    """Stable, no-network hashed Korean character n-gram embedding for tests and demos."""

    profile_id = "fake-char-bigram-v1"

    def __init__(self, dimensions: int = 192):
        self.dimensions = dimensions

    def embed(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimensions
        grams = _character_ngrams(text, 2) | _character_ngrams(text, 3)
        for gram in grams:
            digest = hashlib.sha256(gram.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return tuple(vector)
        return tuple(value / norm for value in vector)


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def lexical_similarity(query: str, target: str) -> float:
    normalized_query = normalize_text(query)
    normalized_target = normalize_text(target)
    query_terms = _terms(normalized_query)
    target_terms = _terms(normalized_target)
    concept_score = sum(
        max(
            (_term_similarity(query_term, target_term) for target_term in target_terms), default=0.0
        )
        for query_term in query_terms
    ) / max(1, len(query_terms))
    query_grams = _character_ngrams(query, 2)
    target_grams = _character_ngrams(target, 2)
    gram_score = len(query_grams & target_grams) / max(1, len(query_grams))
    phrase_boost = 0.35 if normalized_query and normalized_query in normalized_target else 0.0
    return min(1.0, 0.55 * concept_score + 0.20 * gram_score + phrase_boost)


class HybridRetriever:
    def __init__(
        self,
        repository: KnowledgeRepository,
        embedding_provider: DeterministicEmbeddingProvider,
        graph_query: GraphQuery | None = None,
    ):
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._graph_query = graph_query

    def retrieve(
        self,
        question: str,
        as_of: date,
        principal: Principal,
        document_ids: frozenset[str] | None = None,
        limit: int = 10,
    ) -> tuple[RetrievalHit, ...]:
        hits, _ = self.retrieve_with_status(
            question,
            as_of,
            principal,
            document_ids=document_ids,
            limit=limit,
        )
        return hits

    def retrieve_with_status(
        self,
        question: str,
        as_of: date,
        principal: Principal,
        document_ids: frozenset[str] | None = None,
        limit: int = 10,
    ) -> tuple[tuple[RetrievalHit, ...], str]:
        provisions = self._repository.active_provisions(
            as_of=as_of, principal=principal, document_ids=document_ids
        )
        snapshot = self._repository.snapshot
        question_vector = self._embedding_provider.embed(question)
        lexical: list[tuple[Provision, float]] = []
        vector: list[tuple[Provision, float]] = []
        locator_match = _LOCATOR_RE.search(question)

        database_vector_scores: dict[str, float] | None = None
        vector_search = getattr(self._repository, "vector_search", None)
        if callable(vector_search):
            database_vector_scores = dict(
                vector_search(question_vector, as_of, principal, document_ids, 50)
            )
        for provision in provisions:
            document = snapshot.documents[provision.document_id]
            metadata = " ".join(
                filter(None, [document.title, document.document_code, provision.locator])
            )
            target = f"{metadata} {provision.body}"
            lexical_score = max(
                lexical_similarity(question, provision.body),
                0.45 * lexical_similarity(question, metadata),
            )
            if locator_match and provision.locator.startswith(f"제{locator_match.group(1)}조"):
                lexical_score = min(1.0, lexical_score + 0.35)
                paragraph = locator_match.group(2)
                if paragraph and f"제{paragraph}항" in provision.locator:
                    lexical_score = min(1.0, lexical_score + 0.25)
            vector_score = (
                database_vector_scores.get(provision.id, 0.0)
                if database_vector_scores is not None
                else max(
                    0.0,
                    cosine_similarity(question_vector, self._embedding_provider.embed(target)),
                )
            )
            if lexical_score > 0:
                lexical.append((provision, lexical_score))
            if vector_score > 0:
                vector.append((provision, vector_score))

        lexical.sort(key=lambda item: (-item[1], item[0].id))
        vector.sort(key=lambda item: (-item[1], item[0].id))
        lane_scores: dict[str, dict[str, float]] = defaultdict(dict)
        fused: dict[str, float] = defaultdict(float)
        for lane, ranked in (("lexical", lexical), ("vector", vector)):
            for rank, (provision, raw_score) in enumerate(ranked[:50], start=1):
                lane_scores[provision.id][lane] = raw_score
                fused[provision.id] += 1.0 / (60 + rank)

        graph_ranked, graph_status = self._graph_candidates(
            question,
            provisions,
            principal,
            as_of,
            document_ids,
        )
        for rank, (provision, raw_score) in enumerate(graph_ranked, start=1):
            lane_scores[provision.id]["graph"] = raw_score
            fused[provision.id] += 1.0 / (60 + rank)

        hits: list[RetrievalHit] = []
        by_id = {provision.id: provision for provision in provisions}
        for provision_id, rrf_score in fused.items():
            provision = by_id[provision_id]
            scores = lane_scores[provision_id]
            relevance = max(scores.get("lexical", 0.0), scores.get("vector", 0.0))
            final_score = rrf_score + 0.45 * scores.get("lexical", 0.0)
            final_score += 0.20 * scores.get("vector", 0.0)
            final_score += 0.20 * scores.get("graph", 0.0)
            scores["relevance"] = relevance
            hits.append(
                RetrievalHit(
                    provision=provision,
                    document=snapshot.documents[provision.document_id],
                    version=snapshot.versions[provision.version_id],
                    score=final_score,
                    lane_scores=dict(scores),
                )
            )
        hits.sort(key=lambda item: (-item.score, item.provision.id))
        return tuple(hits[:limit]), graph_status

    def _graph_candidates(
        self,
        question: str,
        allowed_provisions: tuple[Provision, ...],
        principal: Principal,
        as_of: date,
        document_ids: frozenset[str] | None,
    ) -> tuple[list[tuple[Provision, float]], str]:
        snapshot = self._repository.snapshot
        scope = compile_graph_access_scope(
            self._repository,
            principal,
            as_of,
            requested_document_ids=document_ids,
        )
        allowed_by_key = {
            (provision.document_id, provision.locator): provision
            for provision in allowed_provisions
        }
        allowed_node_ids = frozenset(scope.node_ids)
        node_matches = tuple(
            sorted(
                node.id
                for node in snapshot.ontology_nodes.values()
                if node.id in allowed_node_ids and lexical_similarity(question, node.label) >= 0.22
            )
        )[:25]
        candidate_edges = scope.candidate_edges(node_matches, None, 100)
        if self._graph_query is None:
            return self._provisions_for_graph_edges(candidate_edges, allowed_by_key), "healthy"
        if not scope.document_ids:
            return [], "healthy"
        try:
            projection_status = self._graph_query.status(scope.publication_id)
        except ConfigurationError:
            return [], "unavailable"
        if not projection_status.healthy:
            return [], projection_status.status
        if not node_matches or not candidate_edges:
            return [], "healthy"
        candidate_node_ids = tuple(
            sorted(
                frozenset(node_matches)
                | {edge.source for edge in candidate_edges}
                | {edge.target for edge in candidate_edges}
            )
        )
        try:
            rows = self._graph_query.one_hop(
                publication_id=scope.publication_id,
                seed_ids=node_matches,
                allowed_node_ids=candidate_node_ids,
                allowed_edge_ids=tuple(edge.id for edge in candidate_edges),
                allowed_document_ids=tuple(
                    sorted({edge.source_document for edge in candidate_edges})
                ),
                relation_types=tuple(sorted({edge.type for edge in candidate_edges})),
                max_edges=100,
            )
        except ConfigurationError:
            return [], "unavailable"
        verified_edges = scope.verify_rows(rows, candidate_edges)
        return self._provisions_for_graph_edges(verified_edges, allowed_by_key), "healthy"

    @staticmethod
    def _provisions_for_graph_edges(
        edges: tuple[OntologyEdge, ...],
        allowed_by_key: dict[tuple[str, str], Provision],
    ) -> list[tuple[Provision, float]]:
        scores: dict[str, float] = defaultdict(float)
        for edge in edges:
            locator_match = _LOCATOR_RE.search(edge.source_locator)
            if not locator_match:
                continue
            locator_prefix = f"제{locator_match.group(1)}조"
            paragraph = locator_match.group(2)
            if paragraph:
                locator_prefix += f" 제{paragraph}항"
            for (document_id, locator), provision in allowed_by_key.items():
                if document_id == edge.source_document and locator.startswith(locator_prefix):
                    scores[provision.id] = max(scores[provision.id], 0.35)
        provisions_by_id = {item.id: item for item in allowed_by_key.values()}
        return sorted(
            ((provisions_by_id[item_id], score) for item_id, score in scores.items()),
            key=lambda item: (-item[1], item[0].id),
        )

    def denied_scope_has_evidence(
        self,
        question: str,
        as_of: date,
        principal: Principal,
        document_ids: frozenset[str] | None = None,
    ) -> bool:
        snapshot = self._repository.snapshot
        for document in snapshot.documents.values():
            if document_ids is not None and document.id not in document_ids:
                continue
            if principal.can_read(document.id, document.security_class):
                continue
            version = self._repository.effective_version(document.id, as_of)
            if version is None:
                continue
            for provision_id in snapshot.provisions_by_version[version.id]:
                provision = snapshot.provisions[provision_id]
                if provision.level.value != "paragraph":
                    continue
                if lexical_similarity(question, f"{document.title} {provision.body}") >= 0.24:
                    return True
        return False
