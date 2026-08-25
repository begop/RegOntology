from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, Request

from app.application.ports import AuditLog, GraphProjection, KnowledgeRepository
from app.application.services import OntologyService, QAService, RegulationService
from app.domain.errors import ConfigurationError, InvalidRequestError
from app.domain.graph import GraphProjectionStatus
from app.domain.models import Principal, SecurityClass
from app.settings.config import Settings


@dataclass(slots=True)
class Services:
    settings: Settings
    repository: KnowledgeRepository
    regulations: RegulationService
    ontology: OntologyService
    qa: QAService
    audit: AuditLog
    graph_projector: GraphProjection | None = None
    graph_mode: str = "mock_projection"

    def graph_status(self) -> GraphProjectionStatus:
        publication_id = self.repository.snapshot.publication_id
        if self.graph_projector is None:
            return GraphProjectionStatus(status="healthy", publication_id=publication_id)
        try:
            return self.graph_projector.status(publication_id)
        except ConfigurationError:
            return GraphProjectionStatus(status="unavailable", publication_id=None)


def get_services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


def get_request_id(request: Request) -> str:
    return str(request.state.request_id)


def get_principal(
    request: Request,
    x_demo_role: str = Header(default="employee", alias="X-Demo-Role"),
    x_demo_security_classes: str = Header(
        default="public,internal", alias="X-Demo-Security-Classes"
    ),
    x_demo_subject: str = Header(default="demo-user", alias="X-Demo-Subject"),
    x_demo_document_ids: str | None = Header(default=None, alias="X-Demo-Document-Ids"),
) -> Principal:
    services = get_services(request)
    if not services.settings.demo_auth_enabled:
        raise ConfigurationError("OIDC adapter is required when demo authentication is disabled.")
    try:
        allowed = frozenset(
            SecurityClass(value.strip().lower())
            for value in x_demo_security_classes.split(",")
            if value.strip()
        )
    except ValueError as exc:
        raise InvalidRequestError(
            details=[{"field": "X-Demo-Security-Classes", "reason": "invalid_value"}]
        ) from exc
    if not allowed:
        raise InvalidRequestError(details=[{"field": "X-Demo-Security-Classes", "reason": "empty"}])
    return Principal(
        subject=x_demo_subject[:128],
        role=x_demo_role.strip().lower()[:32],
        allowed_security_classes=allowed,
        allowed_document_ids=(
            frozenset(
                document_id.strip()
                for document_id in x_demo_document_ids.split(",")
                if document_id.strip()
            )
            if x_demo_document_ids is not None
            else None
        ),
    )
