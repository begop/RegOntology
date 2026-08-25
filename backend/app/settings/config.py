from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.domain.errors import ConfigurationError


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _discover_mock_data_dir() -> Path:
    configured = os.getenv("REGONTOLOGY_MOCK_DATA_DIR") or os.getenv("MOCK_DATA_DIR")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            Path("/app/mock-data"),
            Path(__file__).resolve().parents[3] / "mock-data",
            Path.cwd() / "mock-data",
            Path.cwd().parent / "mock-data",
        ]
    )
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if (resolved / "regulations").is_dir() and (resolved / "ontology").is_dir():
            return resolved
    raise ConfigurationError("Mock data directory was not found.")


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    mock_data_dir: Path
    cors_origins: tuple[str, ...]
    demo_auth_enabled: bool
    ai_provider: str
    openai_model: str
    openai_base_url: str
    openai_timeout_seconds: float
    openai_api_key: str | None = field(repr=False)
    max_question_chars: int = 2_000
    repository_mode: str = "mock"
    database_url: str | None = field(default=None, repr=False)
    auto_seed_mock_data: bool = False
    graph_mode: str = "mock"
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls) -> Settings:
        environment = os.getenv("REGONTOLOGY_ENV", "development").strip().lower()
        demo_auth_enabled = _as_bool(os.getenv("REGONTOLOGY_DEMO_AUTH_ENABLED"), True)
        provider = os.getenv("REGONTOLOGY_AI_PROVIDER", "fake").strip().lower()
        if provider not in {"fake", "openai"}:
            raise ConfigurationError("Unsupported AI provider.")
        api_key = os.getenv("OPENAI_API_KEY")
        if provider == "openai" and not api_key:
            raise ConfigurationError("OPENAI_API_KEY is required for the explicit OpenAI profile.")
        repository_mode = os.getenv("REGONTOLOGY_REPOSITORY_MODE", "mock").strip().lower()
        if repository_mode not in {"mock", "postgres"}:
            raise ConfigurationError("Unsupported repository mode.")
        database_url = os.getenv("DATABASE_URL")
        if repository_mode == "postgres" and not database_url:
            raise ConfigurationError("DATABASE_URL is required for the PostgreSQL profile.")
        if environment == "production" and demo_auth_enabled:
            raise ConfigurationError("Demo authentication is forbidden in production.")
        if environment == "production" and repository_mode != "postgres":
            raise ConfigurationError("The PostgreSQL repository is required in production.")
        graph_mode = os.getenv("REGONTOLOGY_GRAPH_MODE", "mock").strip().lower()
        if graph_mode not in {"mock", "neo4j"}:
            raise ConfigurationError("Unsupported graph mode.")
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if graph_mode == "neo4j" and not all((neo4j_uri, neo4j_user, neo4j_password)):
            raise ConfigurationError(
                "Neo4j connection settings are required for the Neo4j profile."
            )
        origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "REGONTOLOGY_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
            ).split(",")
            if origin.strip()
        )
        return cls(
            environment=environment,
            mock_data_dir=_discover_mock_data_dir(),
            cors_origins=origins,
            demo_auth_enabled=demo_auth_enabled,
            ai_provider=provider,
            openai_model=os.getenv("REGONTOLOGY_OPENAI_MODEL", "gpt-5-mini").strip(),
            openai_base_url=os.getenv(
                "REGONTOLOGY_OPENAI_BASE_URL", "https://api.openai.com/v1"
            ).rstrip("/"),
            openai_timeout_seconds=float(os.getenv("REGONTOLOGY_OPENAI_TIMEOUT_SECONDS", "20")),
            openai_api_key=api_key,
            max_question_chars=int(os.getenv("REGONTOLOGY_MAX_QUESTION_CHARS", "2000")),
            repository_mode=repository_mode,
            database_url=database_url,
            auto_seed_mock_data=_as_bool(os.getenv("REGONTOLOGY_AUTO_SEED_MOCK_DATA"), False),
            graph_mode=graph_mode,
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
        )
