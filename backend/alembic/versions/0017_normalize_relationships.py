"""Normalize relationships: drop duplicated name columns.

Revision ID: 0017_normalize_relationships
Revises: 0016_category_name_km
Create Date: 2026-07-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_normalize_relationships"
down_revision: Union[str, None] = "0016_category_name_km"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- commissions: add FK columns before backfill / drops ---
    op.add_column("commissions", sa.Column("student_id", sa.Integer(), nullable=True))
    op.add_column("commissions", sa.Column("invoice_id", sa.Integer(), nullable=True))
    op.add_column("commissions", sa.Column("teacher_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_commissions_student_id"), "commissions", ["student_id"], unique=False)
    op.create_index(op.f("ix_commissions_invoice_id"), "commissions", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_commissions_teacher_id"), "commissions", ["teacher_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_commissions_student_id_students"),
        "commissions",
        "students",
        ["student_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_commissions_invoice_id_invoices"),
        "commissions",
        "invoices",
        ["invoice_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_commissions_teacher_id_users"),
        "commissions",
        "users",
        ["teacher_id"],
        ["id"],
    )

    conn = op.get_bind()

    # Backfill invoices.student_id from phone / English name when missing
    conn.execute(
        sa.text(
            """
            UPDATE invoices AS i
            SET student_id = s.id
            FROM students AS s
            WHERE i.student_id IS NULL
              AND i.student_phone IS NOT NULL
              AND btrim(i.student_phone) <> ''
              AND s.phone = i.student_phone
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE invoices AS i
            SET student_id = s.id
            FROM students AS s
            WHERE i.student_id IS NULL
              AND i.student_name IS NOT NULL
              AND btrim(i.student_name) <> ''
              AND (
                    s.name_en = i.student_name
                 OR s.name_km = i.student_name
                 OR i.student_name LIKE ('% · ' || s.name_en)
                 OR i.student_name = (s.name_km || ' · ' || s.name_en)
              )
            """
        )
    )

    # Backfill commissions FKs from class + closest matching invoice by student name/amount
    conn.execute(
        sa.text(
            """
            UPDATE commissions AS c
            SET teacher_id = sc.teacher_id
            FROM classes AS sc
            WHERE c.class_id = sc.id
              AND c.teacher_id IS NULL
              AND sc.teacher_id IS NOT NULL
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE commissions AS c
            SET student_id = i.student_id
            FROM invoices AS i
            WHERE c.student_id IS NULL
              AND i.student_id IS NOT NULL
              AND i.student_name IS NOT NULL
              AND c.student_name IS NOT NULL
              AND (
                    i.student_name = c.student_name
                 OR i.student_name LIKE ('% · ' || c.student_name)
                 OR c.student_name = i.student_name
              )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE commissions AS c
            SET student_id = s.id
            FROM students AS s
            WHERE c.student_id IS NULL
              AND c.student_name IS NOT NULL
              AND btrim(c.student_name) <> ''
              AND (s.name_en = c.student_name OR s.name_km = c.student_name)
            """
        )
    )

    # Drop duplicated text columns
    op.drop_column("invoices", "student_name")
    op.drop_column("invoices", "student_phone")

    op.drop_index(op.f("ix_invoice_lines_product_name"), table_name="invoice_lines")
    op.drop_column("invoice_lines", "product_name")

    op.drop_index(op.f("ix_commissions_teacher_name"), table_name="commissions")
    op.drop_column("commissions", "class_name")
    op.drop_column("commissions", "student_name")
    op.drop_column("commissions", "teacher_name")

    op.drop_column("classes", "teacher_name")
    op.drop_column("classes", "level")
    op.drop_column("classes", "level_km")


def downgrade() -> None:
    op.add_column("classes", sa.Column("level_km", sa.String(length=100), nullable=True))
    op.add_column("classes", sa.Column("level", sa.String(length=100), nullable=True))
    op.add_column("classes", sa.Column("teacher_name", sa.String(length=150), nullable=True))

    op.add_column(
        "commissions",
        sa.Column("teacher_name", sa.String(length=150), nullable=False, server_default="Unknown"),
    )
    op.add_column("commissions", sa.Column("student_name", sa.String(length=180), nullable=True))
    op.add_column("commissions", sa.Column("class_name", sa.String(length=180), nullable=True))
    op.create_index(op.f("ix_commissions_teacher_name"), "commissions", ["teacher_name"], unique=False)
    op.alter_column("commissions", "teacher_name", server_default=None)

    op.add_column(
        "invoice_lines",
        sa.Column("product_name", sa.String(length=180), nullable=False, server_default=""),
    )
    op.create_index(op.f("ix_invoice_lines_product_name"), "invoice_lines", ["product_name"], unique=False)
    op.alter_column("invoice_lines", "product_name", server_default=None)

    op.add_column("invoices", sa.Column("student_phone", sa.String(length=80), nullable=True))
    op.add_column("invoices", sa.Column("student_name", sa.String(length=180), nullable=True))

    op.drop_constraint(op.f("fk_commissions_teacher_id_users"), "commissions", type_="foreignkey")
    op.drop_constraint(op.f("fk_commissions_invoice_id_invoices"), "commissions", type_="foreignkey")
    op.drop_constraint(op.f("fk_commissions_student_id_students"), "commissions", type_="foreignkey")
    op.drop_index(op.f("ix_commissions_teacher_id"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_invoice_id"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_student_id"), table_name="commissions")
    op.drop_column("commissions", "teacher_id")
    op.drop_column("commissions", "invoice_id")
    op.drop_column("commissions", "student_id")
