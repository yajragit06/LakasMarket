"""initial schema: users, subscriptions, listings, knowledge_questions, offers

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.enums import (
    District,
    ListingStatus,
    OfferStatus,
    SaleMode,
    SubscriptionTier,
)

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enums are stored as VARCHAR (native_enum=False), matching the ORM models.
_district = sa.Enum(District, native_enum=False, length=20)
_sale_mode = sa.Enum(SaleMode, native_enum=False, length=10)
_listing_status = sa.Enum(ListingStatus, native_enum=False, length=10)
_offer_status = sa.Enum(OfferStatus, native_enum=False, length=15)
_tier = sa.Enum(SubscriptionTier, native_enum=False, length=10)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("home_district", _district, nullable=False),
        sa.Column("reliability_score", sa.Float(), nullable=False),
        sa.Column("communication_score", sa.Float(), nullable=False),
        sa.Column("completed_deals", sa.Integer(), nullable=False),
        sa.Column("ghost_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tier", _tier, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("renews_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True)

    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "seller_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("list_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("floor_percent", sa.Float(), nullable=False),
        sa.Column("sale_mode", _sale_mode, nullable=False),
        sa.Column("speed_discount_percent", sa.Float(), nullable=False),
        sa.Column("district", _district, nullable=False),
        sa.Column("delivery_available", sa.Boolean(), nullable=False),
        sa.Column("min_buyer_adab", sa.Float(), nullable=False),
        sa.Column("status", _listing_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_listings_seller_id", "listings", ["seller_id"])

    op.create_table(
        "knowledge_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "listing_id",
            sa.Integer(),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prompt", sa.String(length=300), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("correct_index", sa.Integer(), nullable=False),
        sa.Column("ai_generated", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_knowledge_questions_listing_id", "knowledge_questions", ["listing_id"])

    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "listing_id",
            sa.Integer(),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "buyer_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("is_take_tonight", sa.Boolean(), nullable=False),
        sa.Column("status", _offer_status, nullable=False),
        sa.Column("rejection_reason", sa.String(length=120), nullable=True),
        sa.Column("floor_price_at_offer", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("passed_knowledge_gate", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_offers_listing_id", "offers", ["listing_id"])
    op.create_index("ix_offers_buyer_id", "offers", ["buyer_id"])


def downgrade() -> None:
    op.drop_table("offers")
    op.drop_table("knowledge_questions")
    op.drop_table("listings")
    op.drop_table("subscriptions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
