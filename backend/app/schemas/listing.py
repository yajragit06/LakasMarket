"""Listing schemas."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import District, ListingStatus, SaleMode


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)


class AskAnswer(BaseModel):
    answer: str
    # False when the seller's plan doesn't include the AI Specs Guard.
    specs_guard_enabled: bool


class SellerSummary(BaseModel):
    """Public reputation snapshot shown to buyers on each listing."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    adab_score: float
    completed_deals: int


class KnowledgeQuestionIn(BaseModel):
    prompt: str = Field(min_length=3, max_length=300)
    options: list[str] = Field(min_length=2, max_length=6)
    correct_index: int = Field(ge=0)


class KnowledgeQuestionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt: str
    options: list[str]
    ai_generated: bool
    # NOTE: correct_index is intentionally omitted so buyers can't cheat.


class ListingCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    category: str | None = Field(default=None, max_length=80)
    list_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    floor_percent: float = Field(default=20.0, ge=0, le=90)
    sale_mode: SaleMode = SaleMode.FIRM
    speed_discount_percent: float = Field(default=7.5, ge=0, le=10)
    district: District = District.BANDAR
    delivery_available: bool = True
    min_buyer_adab: float = Field(default=0.0, ge=0, le=100)
    negotiation_enabled: bool = False
    # Seller-authored questions. If empty and Specs Guard is available, the
    # AI will generate them.
    knowledge_questions: list[KnowledgeQuestionIn] = Field(default_factory=list)
    auto_generate_questions: bool = True


class BulkListingCreate(BaseModel):
    """Business-tier bulk upload: up to 50 listings in one request."""

    listings: list[ListingCreate] = Field(min_length=1, max_length=50)


class ListingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    title: str
    description: str
    category: str | None
    list_price: Decimal
    floor_percent: float
    hard_floor_price: float
    sale_mode: SaleMode
    speed_discount_percent: float
    district: District
    delivery_available: bool
    min_buyer_adab: float
    negotiation_enabled: bool
    status: ListingStatus
    created_at: datetime
    knowledge_questions: list[KnowledgeQuestionPublic]
    seller: SellerSummary
