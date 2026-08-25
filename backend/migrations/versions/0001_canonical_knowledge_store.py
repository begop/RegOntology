"""Create the PostgreSQL canonical regulation and pgvector schema.

Revision ID: 0001
Revises: None
"""

from collections.abc import Sequence

from alembic import op

from app.infrastructure.postgres.models import Base

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INITIAL_TABLES = (
    "regulation_document",
    "regulation_version",
    "provision",
    "chunk",
    "embedding",
    "ontology_entity",
    "ontology_assertion",
    "publication",
    "audit_event",
)


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    Base.metadata.create_all(
        bind=bind,
        tables=[Base.metadata.tables[name] for name in _INITIAL_TABLES],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_regulation_version_label
        ON regulation_version (document_id, version_label)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_provision_canonical_path
        ON provision (version_id, canonical_path)
        """
    )
    op.execute(
        """
        ALTER TABLE regulation_version
        ADD CONSTRAINT regulation_version_no_published_overlap
        EXCLUDE USING gist (
          document_id WITH =,
          daterange(effective_from, effective_to, '[)') WITH &&
        ) WHERE (status = 'published')
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_embedding_vector_hnsw
        ON embedding USING hnsw (vector vector_cosine_ops)
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_audit_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'audit_event is append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_event_append_only
        BEFORE UPDATE OR DELETE ON audit_event
        FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation()
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute("DROP TRIGGER IF EXISTS audit_event_append_only ON audit_event")
    op.execute("DROP FUNCTION IF EXISTS reject_audit_mutation()")
    Base.metadata.drop_all(
        bind=bind,
        tables=[Base.metadata.tables[name] for name in _INITIAL_TABLES],
    )
