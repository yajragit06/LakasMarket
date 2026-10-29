"""User model, including the dual Adab (courtesy) reputation score."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import District

# Adab scores are stored on a 0-100 scale and seeded at a neutral baseline so
# that brand-new users are neither trusted nor distrusted on day one.
ADAB_BASELINE = 70.0
ADAB_MIN = 0.0
ADAB_MAX = 100.0


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Home base for the logistics engine (distance-fair delivery fees).
    home_district: Mapped[District] = mapped_column(
        Enum(District, native_enum=False), nullable=False, default=District.BANDAR
    )

    # --- Adab (courtesy) reputation ---------------------------------------
    # Two independent axes, per the PRD's dual-rating requirement.
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=ADAB_BASELINE)
    communication_score: Mapped[float] = mapped_column(Float, nullable=False, default=ADAB_BASELINE)
    # Running counters for transparency / dispute review.
    completed_deals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ghost_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Platform staff — may verify manual escrow payments on any deal.
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    listings: Mapped[list["Listing"]] = relationship(
        back_populates="seller", cascade="all, delete-orphan"
    )
    offers: Mapped[list["Offer"]] = relationship(
        back_populates="buyer",
        cascade="all, delete-orphan",
        foreign_keys="Offer.buyer_id",
    )
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def adab_score(self) -> float:
        """Combined Adab score — the single number sellers filter buyers on."""
        return round((self.reliability_score + self.communication_score) / 2, 1)
