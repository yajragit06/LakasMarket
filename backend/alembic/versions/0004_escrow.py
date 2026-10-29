"""manual funds-verified escrow: payment fields + is_admin

Revision ID: 0004_escrow
Revises: 0003_negotiation
Create Date: 2026-09-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.enums import PaymentStatus

revision: str = "0004_escrow"
down_revision: Union[str, None] = "0003_negotiation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_payment_status = sa.Enum(PaymentStatus, native_enum=False, length=10)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Batch mode so the FK-bearing column also applies on SQLite (dev/offline);
    # on Postgres these are plain ALTERs.
    with op.batch_alter_table("offers", schema=None) as batch:
        batch.add_column(
            sa.Column(
                "payment_status",
                _payment_status,
                nullable=False,
                server_default=PaymentStatus.NONE.value,
            )
        )
        batch.add_column(sa.Column("payment_reference", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("payment_marked_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("payment_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("payment_verified_by", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_offers_payment_verified_by_users",
            "users",
            ["payment_verified_by"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("offers", schema=None) as batch:
        batch.drop_constraint("fk_offers_payment_verified_by_users", type_="foreignkey")
        batch.drop_column("payment_verified_by")
        batch.drop_column("payment_verified_at")
        batch.drop_column("payment_marked_at")
        batch.drop_column("payment_reference")
        batch.drop_column("payment_status")
    op.drop_column("users", "is_admin")
