"""Offer model — the heart of the Anti-Lowball Engine."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import OfferStatus, PaymentStatus


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # True when the buyer invoked the "take tonight" speed justification.
    is_take_tonight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    status: Mapped[OfferStatus] = mapped_column(
        Enum(OfferStatus, native_enum=False), nullable=False, default=OfferStatus.PENDING
    )
    # Machine reason (e.g. "below_hard_floor"). Never surfaced to the seller
    # for auto-rejected offers — kept for audit/analytics only.
    rejection_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Snapshot of the hard floor at the time the offer was made, for auditing.
    floor_price_at_offer: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # Computed delivery fee (BND) applied by the logistics engine, if any.
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    # Whether the buyer passed the Product Knowledge Gateway for this listing.
    passed_knowledge_gate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- Manual "Funds Verified" escrow -----------------------------------
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False), nullable=False, default=PaymentStatus.NONE
    )
    # Buyer-supplied transfer note/reference (e.g. bank ref). Not sensitive.
    payment_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_verified_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    listing: Mapped["Listing"] = relationship(back_populates="offers")
    buyer: Mapped["User"] = relationship(
        back_populates="offers", foreign_keys=[buyer_id]
    )

    @property
    def seller_visible(self) -> bool:
        """Auto-rejected offers are hidden to protect the seller's sentiment."""
        return self.status != OfferStatus.AUTO_REJECTED
