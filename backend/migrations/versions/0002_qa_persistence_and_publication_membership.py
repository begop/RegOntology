"""Persist QA results and define publication membership.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_publication_single_active",
        "publication",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_table(
        "publication_member",
        sa.Column(
            "publication_id",
            sa.Text(),
            sa.ForeignKey("publication.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "version_id",
            sa.Text(),
            sa.ForeignKey("regulation_version.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("security_class", sa.String(length=16), nullable=False),
    )
    op.create_index(
        "ix_publication_member_security_class",
        "publication_member",
        ["security_class"],
    )
    op.execute(
        """
        INSERT INTO publication_member (
          publication_id, version_id, source_sha256, security_class
        )
        SELECT DISTINCT
          chunk.publication_id,
          regulation_version.id,
          regulation_version.source_sha256,
          regulation_document.security_class
        FROM chunk
        JOIN provision ON provision.id = chunk.provision_id
        JOIN regulation_version ON regulation_version.id = provision.version_id
        JOIN regulation_document ON regulation_document.id = regulation_version.document_id
        JOIN publication ON publication.id = chunk.publication_id
        WHERE publication.status = 'ACTIVE'
        ON CONFLICT (publication_id, version_id) DO NOTHING
        """
    )

    op.create_table(
        "qa_run",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("owner_subject", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("question_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("answer", sa.Text()),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason_code", sa.String(length=64)),
        sa.Column("suggested_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trace_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "publication_id",
            sa.Text(),
            sa.ForeignKey("publication.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    op.create_index("ix_qa_run_owner_subject", "qa_run", ["owner_subject"])
    op.create_index("ix_qa_run_request_id", "qa_run", ["request_id"])
    op.create_index("ix_qa_run_created_at", "qa_run", ["created_at"])
    op.create_index("ix_qa_run_status", "qa_run", ["status"])
    op.create_index("ix_qa_run_publication_id", "qa_run", ["publication_id"])

    op.create_table(
        "qa_citation",
        sa.Column(
            "qa_run_id",
            sa.Text(),
            sa.ForeignKey("qa_run.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("citation_index", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column(
            "document_id",
            sa.Text(),
            sa.ForeignKey("regulation_document.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            sa.Text(),
            sa.ForeignKey("regulation_version.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "provision_id",
            sa.Text(),
            sa.ForeignKey("provision.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quote_sha256", sa.String(length=64), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("qa_citation")
    op.drop_index("ix_qa_run_publication_id", table_name="qa_run")
    op.drop_index("ix_qa_run_status", table_name="qa_run")
    op.drop_index("ix_qa_run_created_at", table_name="qa_run")
    op.drop_index("ix_qa_run_request_id", table_name="qa_run")
    op.drop_index("ix_qa_run_owner_subject", table_name="qa_run")
    op.drop_table("qa_run")
    op.drop_index("ix_publication_member_security_class", table_name="publication_member")
    op.drop_table("publication_member")
    op.drop_index("uq_publication_single_active", table_name="publication")
