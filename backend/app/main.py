from __future__ import annotations

import re
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.dependencies import Services
from app.api.router import router
from app.application.ports import (
    AuditLog,
    GraphProjection,
    KnowledgeRepository,
    QAResultStore,
)
from app.application.services import OntologyService, QAService, RegulationService
from app.domain.errors import ConfigurationError, DomainError
from app.infrastructure.audit import InMemoryAppendOnlyAuditLog
from app.infrastructure.mock_repository import MockKnowledgeRepository
from app.infrastructure.providers import build_generation_provider
from app.infrastructure.qa_store import InMemoryQAResultStore
from app.infrastructure.retrieval import DeterministicEmbeddingProvider, HybridRetriever
from app.settings.config import Settings

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if _REQUEST_ID_RE.fullmatch(supplied) else str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        services: Services = request.app.state.services
        snapshot = services.repository.snapshot
        response.headers["X-Publication-ID"] = snapshot.publication_id
        response.headers["X-Graph-Watermark"] = snapshot.graph_watermark
        return response


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, object]] | None = None,
) -> JSONResponse:
    request_id = str(getattr(request.state, "request_id", "unknown"))
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": details or [],
            }
        },
        headers={"X-Request-ID": request_id},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()
    repository: KnowledgeRepository
    postgres_engine = None
    if active_settings.repository_mode == "postgres":
        from app.infrastructure.postgres.repository import PostgresKnowledgeRepository

        if active_settings.database_url is None:
            raise RuntimeError("Validated PostgreSQL settings are missing.")
        repository = PostgresKnowledgeRepository(
            active_settings.database_url,
            active_settings.mock_data_dir,
            auto_seed_mock_data=active_settings.auto_seed_mock_data,
        )
        postgres_engine = repository.engine
    else:
        repository = MockKnowledgeRepository(active_settings.mock_data_dir)
    graph_projector: GraphProjection | None = None
    graph_mode = "mock_projection"
    if active_settings.graph_mode == "neo4j":
        from app.infrastructure.neo4j.projection import Neo4jProjectionAdapter

        if not (
            active_settings.neo4j_uri
            and active_settings.neo4j_user
            and active_settings.neo4j_password
        ):
            raise RuntimeError("Validated Neo4j settings are missing.")
        graph_projector = Neo4jProjectionAdapter(
            active_settings.neo4j_uri,
            active_settings.neo4j_user,
            active_settings.neo4j_password,
        )
        if active_settings.auto_seed_mock_data:
            with suppress(ConfigurationError):
                graph_projector.replace_projection(repository.snapshot)
        graph_mode = "neo4j_projection"
    embedding = DeterministicEmbeddingProvider()
    retriever = HybridRetriever(repository, embedding, graph_projector)
    audit: AuditLog
    qa_result_store: QAResultStore
    if postgres_engine is not None:
        from app.infrastructure.postgres.audit import PostgresAppendOnlyAuditLog
        from app.infrastructure.postgres.qa_store import PostgresQAResultStore

        audit = PostgresAppendOnlyAuditLog(postgres_engine)
        qa_result_store = PostgresQAResultStore(postgres_engine)
    else:
        audit = InMemoryAppendOnlyAuditLog()
        qa_result_store = InMemoryQAResultStore()
    generation = build_generation_provider(active_settings)
    services = Services(
        settings=active_settings,
        repository=repository,
        regulations=RegulationService(repository, retriever),
        ontology=OntologyService(repository, graph_projector),
        qa=QAService(
            repository,
            retriever,
            generation,
            audit,
            qa_result_store,
            max_question_chars=active_settings.max_question_chars,
            graph_mode=graph_mode,
        ),
        audit=audit,
        graph_projector=graph_projector,
        graph_mode=graph_mode,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if graph_projector is not None:
            graph_projector.close()

    application = FastAPI(
        title="Regulation Knowledge Graph QA API",
        version="0.1.0",
        description=(
            "근거 인용형 금융기관 규정 QA 데모 API. 포함된 데이터는 모두 가상 목업이며 "
            "실제 금융·법률 판단에 사용할 수 없습니다."
        ),
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.services = services
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Demo-Role",
            "X-Demo-Security-Classes",
            "X-Demo-Subject",
            "X-Demo-Document-Ids",
        ],
        expose_headers=["X-Request-ID", "X-Publication-ID", "X-Graph-Watermark"],
    )

    @application.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return _error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.public_message,
            details=exc.details,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details: list[dict[str, object]] = [
            {
                "field": ".".join(str(item) for item in error.get("loc", ())[1:]),
                "reason": str(error.get("type", "invalid")),
            }
            for error in exc.errors()
        ]
        return _error_response(
            request,
            status_code=422,
            code="validation_error",
            message="요청을 처리할 수 없습니다.",
            details=details,
        )

    application.include_router(router)

    @application.get("/health/live", include_in_schema=False)
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", include_in_schema=False)
    def ready() -> dict[str, str]:
        repository.healthcheck()
        graph_status = services.graph_status()
        return {
            "status": "ready" if graph_status.healthy else "degraded",
            "publication_id": repository.snapshot.publication_id,
            "graph_status": graph_status.status,
        }

    return application


app = create_app()
