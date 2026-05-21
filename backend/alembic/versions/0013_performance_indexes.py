"""Add indexes for invoice and enrollment lookups."""

from alembic import op

revision = "0013_performance_indexes"
down_revision = "0012_level_description"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_invoices_student_id", "invoices", ["student_id"], unique=False)
    op.create_index(
        "ix_enrollments_student_class",
        "enrollments",
        ["student_id", "class_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_enrollments_student_class", table_name="enrollments")
    op.drop_index("ix_invoices_student_id", table_name="invoices")
