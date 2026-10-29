"""Subscription model for the SaaS tiering logic."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PaymentStatus, SubscriptionTier

# Active-listing limits per tier. ``None`` means unlimited.
TIER_LISTING_LIMITS: dict[SubscriptionTier, int | None] = {
    SubscriptionTier.BASIC: 5,
    SubscriptionTier.PRO: None,
    SubscriptionTier.BUSINESS: None,
}

# Which tiers unlock the AI Specs Guard.
TIER_HAS_SPECS_GUARD: dict[SubscriptionTier, bool] = {
    SubscriptionTier.BASIC: False,
    SubscriptionTier.PRO: True,
    SubscriptionTier.BUSINESS: True,
}

# Monthly price in BND. Placeholder pricing — the billing gate is provider-
# agnostic; a real PSP would supply/confirm these amounts.
TIER_MONTHLY_PRICE: dict[SubscriptionTier, float] = {
    SubscriptionTier.BASIC: 0.0,
    SubscriptionTier.PRO: 15.0,
    SubscriptionTier.BUSINESS: 49.0,
}


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, native_enum=False),
        nullable=False,
        default=SubscriptionTier.BASIC,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Billing gate (manual verification) -------------------------------
    # An upgrade to a paid tier is requested here and only activates once the
    # payment is verified. pending_tier is None when no upgrade is in flight.
    pending_tier: Mapped[SubscriptionTier | None] = mapped_column(
        Enum(SubscriptionTier, native_enum=False), nullable=True
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False), nullable=False, default=PaymentStatus.NONE
    )
    payment_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user: Mapped["User"] = relationship(back_populates="subscription")

    @property
    def listing_limit(self) -> int | None:
        return TIER_LISTING_LIMITS[self.tier]

    @property
    def has_specs_guard(self) -> bool:
        return TIER_HAS_SPECS_GUARD[self.tier]

    @property
    def amount_due(self) -> float:
        """Monthly price of the pending upgrade, if any."""
        return TIER_MONTHLY_PRICE[self.pending_tier] if self.pending_tier else 0.0
