"""Listing model with Hard Floor pricing, sale mode, and knowledge quiz."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import District, ListingStatus, SaleMode

# Default Anti-Lowball floor: offers below 80% of list price are silently
# rejected (i.e. a 20% maximum discount) unless the seller sets a stricter one.
DEFAULT_FLOOR_PERCENT = 20.0
# Default cap for "Take Tonight" speed discounts.
DEFAULT_SPEED_DISCOUNT_PERCENT = 7.5


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Prices in BND, stored as Numeric to avoid float rounding on money.
    list_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # --- Anti-Lowball Engine ----------------------------------------------
    # Maximum discount (%) the seller will tolerate. An offer below
    # list_price * (1 - floor_percent/100) is silently auto-rejected.
    floor_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=DEFAULT_FLOOR_PERCENT
    )

    # --- "Take Tonight" speed premium -------------------------------------
    sale_mode: Mapped[SaleMode] = mapped_column(
        Enum(SaleMode, native_enum=False), nullable=False, default=SaleMode.FIRM
    )
    speed_discount_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=DEFAULT_SPEED_DISCOUNT_PERCENT
    )

    # --- Logistics --------------------------------------------------------
    district: Mapped[District] = mapped_column(
        Enum(District, native_enum=False), nullable=False, default=District.BANDAR
    )
    delivery_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # --- Adab gating ------------------------------------------------------
    # Buyers below this combined Adab score cannot initiate a chat/offer.
    min_buyer_adab: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # --- AI Negotiation Bot (Pro+) ----------------------------------------
    # When on, the bot auto-counters buyer price proposals within the floor.
    negotiation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus, native_enum=False), nullable=False, default=ListingStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    seller: Mapped["User"] = relationship(back_populates="listings")
    offers: Mapped[list["Offer"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )
    knowledge_questions: Mapped[list["KnowledgeQuestion"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", order_by="KnowledgeQuestion.id"
    )

    @property
    def hard_floor_price(self) -> float:
        """Absolute lowest price an offer may reach before silent rejection."""
        return round(float(self.list_price) * (1 - self.floor_percent / 100), 2)


class KnowledgeQuestion(Base):
    """A Product Knowledge Gateway fact-check question for a listing.

    Buyers must answer these (typically 1-2) before they can chat/offer,
    ensuring they actually read the description.
    """

    __tablename__ = "knowledge_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True, nullable=False
    )

    prompt: Mapped[str] = mapped_column(String(300), nullable=False)  # "Is this wired or wireless?"
    # Multiple-choice options.
    options: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # Set by the AI Specs Guard vs. authored by the seller.
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    listing: Mapped["Listing"] = relationship(back_populates="knowledge_questions")
