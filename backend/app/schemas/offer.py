"""Offer schemas."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OfferStatus, PaymentStatus


class OfferCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    is_take_tonight: bool = False
    want_delivery: bool = False
    # Answers to the Product Knowledge Gateway: question_id -> option index.
    quiz_answers: dict[int, int] = Field(default_factory=dict)


class PaymentMark(BaseModel):
    """Buyer's claim that they've sent funds, with an optional reference."""

    reference: str | None = Field(default=None, max_length=120)


class OfferPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    buyer_id: int
    amount: Decimal
    is_take_tonight: bool
    status: OfferStatus
    delivery_fee: Decimal
    passed_knowledge_gate: bool
    created_at: datetime
    payment_status: PaymentStatus
    payment_reference: str | None


class OfferResult(BaseModel):
    """Response returned to the *buyer* after submitting an offer.

    Deliberately does not reveal the seller's exact hard floor. When an offer
    is auto-rejected the buyer sees a neutral message; the seller sees nothing.
    """

    accepted_for_review: bool
    message: str
    delivery_fee: Decimal | None = None
