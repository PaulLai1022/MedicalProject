"""init

Revision ID: 001
Revises:
Create Date: 2025-05-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "cases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_cases_owner_created", "cases", ["owner_user_id", "created_at"]
    )

    op.create_table(
        "case_structured",
        sa.Column(
            "case_id",
            sa.String(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("chief_complaint_machine", sa.Text()),
        sa.Column("chief_complaint_user", sa.Text()),
        sa.Column("hpi_summary_machine", sa.Text()),
        sa.Column("hpi_summary_user", sa.Text()),
        sa.Column("disposition_machine", sa.Text()),
        sa.Column("disposition_user", sa.Text()),
        sa.Column("key_findings_machine", sa.Text()),
        sa.Column("key_findings_user", sa.Text()),
        sa.Column("suspected_conditions_machine", sa.Text()),
        sa.Column("suspected_conditions_user", sa.Text()),
        sa.Column("uncertainties_machine", sa.Text()),
        sa.Column("uncertainties_user", sa.Text()),
        sa.Column("origin_map", sa.Text(), nullable=False),
        sa.Column("decision_path", sa.Text(), nullable=False),
        sa.Column("mcg_hits", sa.Text(), nullable=False),
        sa.Column("missing_core_fields", sa.Text(), nullable=False),
        sa.Column("warnings", sa.Text()),
        sa.Column("extracted_facts", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "revised_hpi_sentences",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "case_id",
            sa.String(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("machine_text", sa.Text()),
        sa.Column("user_text", sa.Text()),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("sources", sa.Text(), nullable=False),
        sa.Column("reason_clinical", sa.Text(), nullable=False),
        sa.Column("reason_guideline", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_sentences_case_order", "revised_hpi_sentences", ["case_id", "sort_order"]
    )

    op.create_table(
        "llm_call_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "case_id",
            sa.String(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("raw_response", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_llm_log_case", "llm_call_log", ["case_id", "created_at"])


def downgrade() -> None:
    op.drop_table("llm_call_log")
    op.drop_table("revised_hpi_sentences")
    op.drop_table("case_structured")
    op.drop_table("cases")
    op.drop_table("users")
