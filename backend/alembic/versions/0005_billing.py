"""billing gate: pending upgrade + payment fields on subscriptions

Revision ID: 0005_billing
Revises: 0004_escrow
Create Date: 2026-09-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.enums import PaymentStatus, SubscriptionTier

revision: str = "0005_billing"
down_revision: Union[str, None] = "0004_escrow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_tier = sa.Enum(SubscriptionTier, native_enum=False, length=12)
_payment_status = sa.Enum(PaymentStatus, native_enum=False, length=10)


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("pending_tier", _tier, nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column(
            "payment_status",
            _payment_status,
            nullable=False,
            server_default=PaymentStatus.NONE.value,
        ),
    )
    op.add_column(
        "subscriptions", sa.Column("payment_reference", sa.String(length=120), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "payment_reference")
    op.drop_column("subscriptions", "payment_status")
    op.drop_column("subscriptions", "pending_tier")
