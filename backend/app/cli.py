from __future__ import annotations

import argparse
from time import sleep

from app.domain.errors import ConfigurationError
from app.domain.models import KnowledgeSnapshot
from app.infrastructure.neo4j.projection import Neo4jProjectionAdapter
from app.infrastructure.postgres.repository import PostgresKnowledgeRepository
from app.settings.config import Settings

_GRAPH_SEED_ATTEMPTS = 10
_GRAPH_SEED_RETRY_SECONDS = 1.0


def _project_with_startup_retry(
    projector: Neo4jProjectionAdapter,
    snapshot: KnowledgeSnapshot,
) -> str:
    for attempt in range(_GRAPH_SEED_ATTEMPTS):
        try:
            projector.replace_projection(snapshot)
            return "healthy"
        except ConfigurationError:
            if attempt + 1 < _GRAPH_SEED_ATTEMPTS:
                sleep(_GRAPH_SEED_RETRY_SECONDS)
    return "degraded"


def seed_mock(settings: Settings) -> None:
    if settings.repository_mode != "postgres" or settings.database_url is None:
        raise ConfigurationError("seed-mock requires REGONTOLOGY_REPOSITORY_MODE=postgres.")
    repository = PostgresKnowledgeRepository(
        settings.database_url,
        settings.mock_data_dir,
        auto_seed_mock_data=True,
    )
    snapshot = repository.snapshot
    graph_status = "not_configured"
    if settings.graph_mode == "neo4j":
        if not (settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password):
            raise ConfigurationError("Neo4j settings are incomplete.")
        projector = Neo4jProjectionAdapter(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        try:
            graph_status = _project_with_startup_retry(projector, snapshot)
        finally:
            projector.close()
    print(
        "Seed complete:",
        f"publication={snapshot.publication_id}",
        f"documents={len(snapshot.documents)}",
        f"versions={len(snapshot.versions)}",
        f"provisions={len(snapshot.provisions)}",
        f"graph={graph_status}",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="RegOntology backend maintenance commands")
    parser.add_argument("command", choices=("seed-mock",))
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.command == "seed-mock":
        seed_mock(settings)


if __name__ == "__main__":
    main()
