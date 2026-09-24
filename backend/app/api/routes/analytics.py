"""Seller analytics endpoints — a Pro/Business tier feature."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.conversation import Conversation
from app.models.enums import (
    ConversationStatus,
    ListingStatus,
    OfferStatus,
    PaymentStatus,
    SubscriptionTier,
)
from app.models.listing import Listing
from app.models.offer import Offer
from app.models.user import User
from app.schemas.analytics import SellerAnalytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/seller", response_model=SellerAnalytics)
def seller_analytics(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> SellerAnalytics:
    """The seller's protection and sales metrics.

    Includes offers the platform silently absorbed (lowballs) — the seller
    never saw those individually, but the aggregate shows the value of the
    Anti-Lowball Engine without exposing any single insulting number.
    """
    sub = current.subscription
    if sub is None or sub.tier == SubscriptionTier.BASIC:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Analytics is a Pro feature. Upgrade to see your protection stats.",
        )

    listing_counts = dict(
        db.execute(
            select(Listing.status, func.count())
            .where(Listing.seller_id == current.id)
            .group_by(Listing.status)
        ).all()
    )

    offer_counts = dict(
        db.execute(
            select(Offer.status, func.count())
            .join(Listing, Offer.listing_id == Listing.id)
            .where(Listing.seller_id == current.id)
            .group_by(Offer.status)
        ).all()
    )

    # Average visible offer strength relative to list price.
    pairs = db.execute(
        select(Offer.amount, Listing.list_price)
        .join(Listing, Offer.listing_id == Listing.id)
        .where(
            Listing.seller_id == current.id,
            Offer.status != OfferStatus.AUTO_REJECTED,
        )
    ).all()
    avg_pct = (
        round(sum(float(a) / float(p) for a, p in pairs) / len(pairs) * 100, 1)
        if pairs
        else None
    )

    conv_counts = dict(
        db.execute(
            select(Conversation.status, func.count())
            .where(Conversation.seller_id == current.id)
            .group_by(Conversation.status)
        ).all()
    )

    funds_verified = db.scalar(
        select(func.count())
        .select_from(Offer)
        .join(Listing, Offer.listing_id == Listing.id)
        .where(
            Listing.seller_id == current.id,
            Offer.payment_status.in_((PaymentStatus.VERIFIED, PaymentStatus.RELEASED)),
        )
    )

    return SellerAnalytics(
        active_listings=listing_counts.get(ListingStatus.ACTIVE, 0),
        reserved_listings=listing_counts.get(ListingStatus.RESERVED, 0),
        sold_listings=listing_counts.get(ListingStatus.SOLD, 0),
        lowballs_blocked=offer_counts.get(OfferStatus.AUTO_REJECTED, 0),
        pending_offers=offer_counts.get(OfferStatus.PENDING, 0),
        accepted_offers=offer_counts.get(OfferStatus.ACCEPTED, 0),
        expired_take_tonight_offers=offer_counts.get(OfferStatus.EXPIRED, 0),
        avg_offer_percent_of_list=avg_pct,
        conversations=sum(conv_counts.values()),
        ghosted_conversations=conv_counts.get(ConversationStatus.GHOSTED, 0),
        funds_verified_deals=funds_verified or 0,
    )
