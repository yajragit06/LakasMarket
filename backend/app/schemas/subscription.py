"""Subscription schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentStatus, SubscriptionTier


class SubscriptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tier: SubscriptionTier
    listing_limit: int | None
    has_specs_guard: bool
    started_at: datetime
    renews_at: datetime | None
    pending_tier: SubscriptionTier | None
    payment_status: PaymentStatus
    amount_due: float


class UpgradeRequest(BaseModel):
    tier: SubscriptionTier


class BillingMark(BaseModel):
    """The user's claim that they've paid for the pending upgrade."""

    reference: str | None = Field(default=None, max_length=120)
