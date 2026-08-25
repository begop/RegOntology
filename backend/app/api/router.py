from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import Services, get_principal, get_request_id, get_services
from app.api.schemas import (
    AuditEventResponse,
    AuditListResponse,
    HealthResponse,
    OntologySearchResponse,
    OntologySubgraphResponse,
    ProvisionDetail,
    ProvisionListResponse,
    ProvisionResponse,
    QAQueryRequest,
    QAResponse,
    RegulationDetail,
    RegulationListResponse,
    ReloadResponse,
    SystemStatusResponse,
    VersionDetail,
)
from app.application.services import require_role
from app.domain.errors import InvalidRequestError
from app.domain.models import Principal, SecurityClass

router = APIRouter(prefix="/api/v1")

ServicesDependency = Annotated[Services, Depends(get_services)]
PrincipalDependency = Annotated[Principal, Depends(get_principal)]
RequestIdDependency = Annotated[str, Depends(get_request_id)]


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health(services: ServicesDependency) -> HealthResponse:
    services.repository.healthcheck()
    snapshot = services.repository.snapshot
    graph_status = services.graph_status()
    return HealthResponse(
        status=(
            "degraded"
            if services.repository.mode == "mock_snapshot" or not graph_status.healthy
            else "ok"
        ),
        service="regontology-api",
        mode=services.repository.mode,
        publication_id=snapshot.publication_id,
        graph_status=graph_status.status,
        graph_publication_id=graph_status.publication_id,
    )


@router.get("/system/status", response_model=SystemStatusResponse, tags=["system"])
def system_status(
    services: ServicesDependency, principal: PrincipalDependency
) -> SystemStatusResponse:
    require_role(principal, "admin")
    snapshot = services.repository.snapshot
    is_mock = services.repository.mode == "mock_snapshot"
    graph_status = services.graph_status()
    warnings = ["mock_snapshot", "not_for_production"] if is_mock else []
    if not graph_status.healthy:
        warnings.append(f"graph_{graph_status.status}")
    return SystemStatusResponse(
        status="degraded" if is_mock or not graph_status.healthy else "healthy",
        repository_mode=services.repository.mode,
        ai_provider=services.settings.ai_provider,
        graph_mode=services.graph_mode,
        auth_mode="demo" if services.settings.demo_auth_enabled else "oidc_required",
        publication_id=snapshot.publication_id,
        graph_watermark=snapshot.graph_watermark,
        graph_status=graph_status.status,
        graph_publication_id=graph_status.publication_id,
        loaded_at=snapshot.loaded_at,
        warnings=warnings,
    )


@router.get("/regulations", response_model=RegulationListResponse, tags=["regulations"])
def list_regulations(
    services: ServicesDependency,
    principal: PrincipalDependency,
    q: str | None = None,
    as_of: date | None = None,
    owner_org: str | None = None,
    security_class: SecurityClass | None = None,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> RegulationListResponse:
    effective_date = as_of or date.today()
    items, total = services.regulations.list_regulations(
        principal=principal,
        as_of=effective_date,
        query=q,
        owner_org=owner_org,
        security_class=security_class,
        status=status,
        limit=limit,
    )
    return RegulationListResponse(items=items, total=total, as_of=effective_date)


@router.get("/regulations/{document_id}", response_model=RegulationDetail, tags=["regulations"])
def get_regulation(
    document_id: str,
    services: ServicesDependency,
    principal: PrincipalDependency,
    request_id: RequestIdDependency,
) -> RegulationDetail:
    result = services.regulations.get_document(document_id, principal)
    services.audit.append(
        actor_subject=principal.subject,
        action="regulation.read",
        target_type="regulation_document",
        target_id=document_id,
        request_id=request_id,
        outcome="success",
    )
    return RegulationDetail.model_validate(result)


@router.get(
    "/regulations/{document_id}/versions/{version_id}",
    response_model=VersionDetail,
    tags=["regulations"],
)
def get_version(
    document_id: str,
    version_id: str,
    services: ServicesDependency,
    principal: PrincipalDependency,
) -> VersionDetail:
    return VersionDetail.model_validate(
        services.regulations.get_version(document_id, version_id, principal)
    )


@router.get(
    "/regulations/{document_id}/versions/{version_id}/provisions",
    response_model=ProvisionListResponse,
    tags=["regulations"],
)
def list_provisions(
    document_id: str,
    version_id: str,
    services: ServicesDependency,
    principal: PrincipalDependency,
    parent_id: str | None = None,
    locator: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> ProvisionListResponse:
    items = services.regulations.get_provisions(
        document_id=document_id,
        version_id=version_id,
        principal=principal,
        parent_id=parent_id,
        locator=locator,
        limit=limit,
    )
    return ProvisionListResponse(items=[ProvisionResponse.model_validate(item) for item in items])


@router.get("/provisions/{provision_id:path}", response_model=ProvisionDetail, tags=["regulations"])
def get_provision(
    provision_id: str,
    services: ServicesDependency,
    principal: PrincipalDependency,
) -> ProvisionDetail:
    return ProvisionDetail.model_validate(
        services.regulations.get_provision(provision_id, principal)
    )


@router.post("/qa/queries", response_model=QAResponse, tags=["qa"])
def create_qa_query(
    payload: QAQueryRequest,
    services: ServicesDependency,
    principal: PrincipalDependency,
    request_id: RequestIdDependency,
) -> QAResponse:
    if payload.stream:
        raise InvalidRequestError(details=[{"field": "stream", "reason": "use_stream_endpoint"}])
    result = services.qa.answer(
        question=payload.question,
        as_of=payload.as_of or date.today(),
        principal=principal,
        document_ids=frozenset(payload.scope.document_ids) or None,
        request_id=request_id,
    )
    return QAResponse.model_validate(result)


@router.get("/qa/queries/{query_id}", response_model=QAResponse, tags=["qa"])
def get_qa_query(
    query_id: str,
    services: ServicesDependency,
    principal: PrincipalDependency,
) -> QAResponse:
    return QAResponse.model_validate(services.qa.get(query_id, principal))


@router.get("/ontology/search", response_model=OntologySearchResponse, tags=["ontology"])
def ontology_search(
    services: ServicesDependency,
    principal: PrincipalDependency,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    types: Annotated[list[str] | None, Query()] = None,
    as_of: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> OntologySearchResponse:
    items = services.ontology.search(
        principal=principal,
        query=q,
        types=frozenset(types) if types else None,
        as_of=as_of or date.today(),
        limit=limit,
    )
    return OntologySearchResponse(items=items)


@router.get("/ontology/subgraph", response_model=OntologySubgraphResponse, tags=["ontology"])
def ontology_subgraph(
    services: ServicesDependency,
    principal: PrincipalDependency,
    seed_ids: Annotated[list[str] | None, Query()] = None,
    relation_types: Annotated[list[str] | None, Query()] = None,
    depth: Annotated[int, Query(ge=1, le=2)] = 1,
    max_nodes: Annotated[int, Query(ge=1, le=200)] = 50,
    as_of: date | None = None,
) -> OntologySubgraphResponse:
    result = services.ontology.subgraph(
        principal=principal,
        seed_ids=tuple(seed_ids or ()),
        relation_types=frozenset(relation_types) if relation_types else None,
        depth=depth,
        max_nodes=max_nodes,
        as_of=as_of or date.today(),
    )
    return OntologySubgraphResponse.model_validate(result)


@router.get("/ontology/nodes/{node_id:path}", tags=["ontology"])
def ontology_node(
    node_id: str,
    services: ServicesDependency,
    principal: PrincipalDependency,
    as_of: date | None = None,
) -> dict[str, object]:
    return services.ontology.node(node_id, principal, as_of or date.today())


@router.post("/admin/mock-data/reload", response_model=ReloadResponse, tags=["admin"])
def reload_mock_data(
    request: Request,
    services: ServicesDependency,
    principal: PrincipalDependency,
    request_id: RequestIdDependency,
) -> ReloadResponse:
    del request
    require_role(principal, "curator", "admin")
    snapshot = services.repository.reload()
    if services.graph_projector is not None:
        services.graph_projector.replace_projection(snapshot)
    services.audit.append(
        actor_subject=principal.subject,
        action="mock_data.reload",
        target_type="publication",
        target_id=snapshot.publication_id,
        request_id=request_id,
        outcome="success",
        metadata={"source": "repository_mock_data"},
    )
    return ReloadResponse(
        publication_id=snapshot.publication_id,
        document_count=len(snapshot.documents),
        version_count=len(snapshot.versions),
        provision_count=len(snapshot.provisions),
        ontology_node_count=len(snapshot.ontology_nodes),
        ontology_edge_count=len(snapshot.ontology_edges),
    )


@router.get("/admin/audit-events", response_model=AuditListResponse, tags=["admin"])
def list_audit_events(
    services: ServicesDependency,
    principal: PrincipalDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> AuditListResponse:
    require_role(principal, "auditor", "admin")
    return AuditListResponse(
        items=[AuditEventResponse.model_validate(item) for item in services.audit.list(limit)],
        chain_valid=services.audit.verify_chain(),
    )
