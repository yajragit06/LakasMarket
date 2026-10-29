"""Chat schemas."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConversationStatus


class ConversationStart(BaseModel):
    # Answers to the Product Knowledge Gateway: question_id -> option index.
    # Buyers must clear the same fact-check they would to make an offer.
    quiz_answers: dict[int, int] = Field(default_factory=dict)
    # Optional opening message sent atomically with starting the thread.
    opening_message: str | None = Field(default=None, max_length=2000)


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class NegotiateRequest(BaseModel):
    proposed_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int
    body: str
    read_at: datetime | None
    created_at: datetime


class ConversationSummary(BaseModel):
    """Row in an inbox list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    buyer_id: int
    seller_id: int
    status: ConversationStatus
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessagePublic]


class NegotiateResponse(BaseModel):
    action: str  # "accept" | "counter"
    counter_price: Decimal | None
    message: MessagePublic
