"""Offer endpoints wiring together the anti-lowball, gateway, adab and
logistics engines."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import adab, escrow
from app.core.anti_lowball import evaluate_offer
from app.core.lifecycle import expire_stale_offers
from app.core.knowledge_gateway import grade_quiz
from app.core.logistics import delivery_fee
from app.database import get_db
from app.models.enums import AdabEventType, ListingStatus, OfferStatus, PaymentStatus
from app.models.listing import Listing
from app.models.offer import Offer
from app.models.user import User
from app.schemas.offer import OfferCreate, OfferPublic, OfferResult, PaymentMark

router = APIRouter(tags=["offers"])


@router.post(
    "/listings/{listing_id}/offers",
    response_model=OfferResult,
    status_code=status.HTTP_201_CREATED,
)
def make_offer(
    listing_id: int,
    payload: OfferCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> OfferResult:
    listing = db.get(Listing, listing_id)
    if listing is None or listing.status != ListingStatus.ACTIVE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not available")
    if listing.seller_id == current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot offer on your own listing")

    # --- Adab gate: low-courtesy buyers can't even reach the seller --------
    if current.adab_score < listing.min_buyer_adab:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Your Adab score is below this seller's minimum. Complete polite, "
            "reliable deals to raise it.",
        )

    # --- Product Knowledge Gateway ----------------------------------------
    quiz = grade_quiz(listing, payload.quiz_answers)
    if not quiz.passed:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Please answer the listing's questions correctly first "
            f"({quiz.correct}/{quiz.total}). Re-read the description.",
        )
    if quiz.total > 0:
        adab.apply_event(current, AdabEventType.QUIZ_PASSED)

    # --- Logistics: fair delivery fee -------------------------------------
    fee = 0.0
    if payload.want_delivery:
        if not listing.delivery_available:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seller does not offer delivery")
        fee = delivery_fee(listing.district, current.home_district)

    # --- Anti-Lowball Engine ----------------------------------------------
    amount = float(payload.amount)
    decision = evaluate_offer(listing, amount, payload.is_take_tonight)

    offer = Offer(
        listing_id=listing.id,
        buyer_id=current.id,
        amount=payload.amount,
        is_take_tonight=payload.is_take_tonight,
        status=decision.status,
        rejection_reason=decision.reason,
        floor_price_at_offer=decision.floor_price,
        delivery_fee=fee,
        passed_knowledge_gate=quiz.passed,
    )
    db.add(offer)
    db.commit()

    # Silent rejection: the buyer gets a neutral message, the seller is never
    # notified, protecting the seller's sentiment.
    if decision.status == OfferStatus.AUTO_REJECTED:
        return OfferResult(
            accepted_for_review=False,
            message="Thanks — your offer wasn't a match for this listing.",
            delivery_fee=fee if payload.want_delivery else None,
        )

    return OfferResult(
        accepted_for_review=True,
        message="Your offer has been sent to the seller for review.",
        delivery_fee=fee if payload.want_delivery else None,
    )


@router.get("/listings/{listing_id}/offers", response_model=list[OfferPublic])
def list_offers_for_seller(
    listing_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Offer]:
    """Seller-only view of offers. Auto-rejected lowballs are never returned."""
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    if listing.seller_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your listing")

    stmt = (
        select(Offer)
        .where(Offer.listing_id == listing_id, Offer.status != OfferStatus.AUTO_REJECTED)
        .order_by(Offer.amount.desc())
    )
    offers = list(db.scalars(stmt).all())
    if expire_stale_offers(offers):
        db.commit()
    return offers


@router.get("/offers/mine", response_model=list[OfferPublic])
def my_offers(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Offer]:
    """The buyer's own offers. Silently-rejected lowballs are omitted so the
    neutral-rejection illusion holds even in the buyer's own history."""
    stmt = (
        select(Offer)
        .where(Offer.buyer_id == current.id, Offer.status != OfferStatus.AUTO_REJECTED)
        .order_by(Offer.created_at.desc())
    )
    offers = list(db.scalars(stmt).all())
    if expire_stale_offers(offers):
        db.commit()
    return offers


def _seller_offer(offer_id: int, db: Session, current: User) -> Offer:
    """Fetch an offer, ensuring the caller is the listing's seller."""
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found")
    listing = db.get(Listing, offer.listing_id)
    if listing is None or listing.seller_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your listing")
    # Auto-rejected lowballs are invisible to the seller — treat as not found.
    if offer.status == OfferStatus.AUTO_REJECTED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found")
    # Lapse stale "take tonight" offers before any action on them.
    if expire_stale_offers([offer]):
        db.commit()
    return offer


@router.post("/offers/{offer_id}/accept", response_model=OfferPublic)
def accept_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Offer:
    offer = _seller_offer(offer_id, db, current)
    if offer.status != OfferStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Offer is no longer pending")

    # Lock the listing row so two concurrent accepts can't both reserve it and
    # double-sell the item. The locking read serializes the check-and-set:
    # whoever commits first flips the listing to RESERVED, the other then reads
    # RESERVED under the lock and is rejected. SQLite ignores FOR UPDATE (fine
    # for the single-connection dev/test setup); Postgres enforces it.
    listing = db.get(Listing, offer.listing_id, with_for_update=True)
    if listing is None or listing.status != ListingStatus.ACTIVE:
        state = listing.status.value if listing else "gone"
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Listing is {state}; it must be active to accept an offer.",
        )
    offer.status = OfferStatus.ACCEPTED
    listing.status = ListingStatus.RESERVED
    db.commit()
    db.refresh(offer)
    return offer


@router.post("/offers/{offer_id}/decline", response_model=OfferPublic)
def decline_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Offer:
    offer = _seller_offer(offer_id, db, current)
    if offer.status != OfferStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Offer is no longer pending")
    offer.status = OfferStatus.DECLINED
    db.commit()
    db.refresh(offer)
    return offer


@router.post("/offers/{offer_id}/complete", response_model=OfferPublic)
def complete_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Offer:
    """Mark an accepted deal as completed and reward both parties' Adab."""
    offer = _seller_offer(offer_id, db, current)
    if offer.status != OfferStatus.ACCEPTED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only accepted offers can be completed")
    offer.listing.status = ListingStatus.SOLD
    # The item is gone — close out every other still-pending offer.
    for other in offer.listing.offers:
        if other.id != offer.id and other.status == OfferStatus.PENDING:
            other.status = OfferStatus.DECLINED
    # If funds were verified via manual escrow, release them on completion.
    if offer.payment_status == PaymentStatus.VERIFIED:
        offer.payment_status = PaymentStatus.RELEASED
    adab.apply_event(offer.buyer, AdabEventType.COMPLETED_DEAL)
    adab.apply_event(current, AdabEventType.COMPLETED_DEAL)
    db.commit()
    db.refresh(offer)
    return offer


@router.post("/offers/{offer_id}/payment/mark-sent", response_model=OfferPublic)
def mark_payment_sent(
    offer_id: int,
    payload: PaymentMark,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Offer:
    """Buyer records that they've sent funds for an accepted deal.

    Moves the deal's escrow state to PENDING, awaiting the seller's (or an
    admin's) verification. No money moves through the platform — this is the
    trust ledger a real PSP would later drive automatically.
    """
    offer = db.get(Offer, offer_id)
    if offer is None or offer.status == OfferStatus.AUTO_REJECTED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found")
    if offer.buyer_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your offer")
    if offer.status != OfferStatus.ACCEPTED:
        raise HTTPException(status.HTTP_409_CONFLICT, "The deal must be accepted first")
    try:
        escrow.assert_transition(offer.payment_status, PaymentStatus.PENDING)
    except escrow.InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))

    offer.payment_status = PaymentStatus.PENDING
    offer.payment_reference = payload.reference
    offer.payment_marked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(offer)
    return offer


@router.post("/offers/{offer_id}/payment/verify", response_model=OfferPublic)
def verify_payment(
    offer_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Offer:
    """Seller (or admin) confirms funds received → the 'Funds Verified' badge."""
    offer = db.get(Offer, offer_id)
    if offer is None or offer.status == OfferStatus.AUTO_REJECTED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found")
    listing = db.get(Listing, offer.listing_id)
    is_seller = listing is not None and listing.seller_id == current.id
    if not (is_seller or current.is_admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the seller or an admin can verify")
    try:
        escrow.assert_transition(offer.payment_status, PaymentStatus.VERIFIED)
    except escrow.InvalidTransition as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The buyer must mark funds as sent before you can verify."
            if offer.payment_status == PaymentStatus.NONE
            else str(exc),
        )

    offer.payment_status = PaymentStatus.VERIFIED
    offer.payment_verified_at = datetime.now(timezone.utc)
    offer.payment_verified_by = current.id
    db.commit()
    db.refresh(offer)
    return offer


@router.post("/offers/{offer_id}/report-ghost", response_model=OfferPublic)
def report_ghost(
    offer_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Offer:
    """Report a buyer who accepted then vanished ("Hilang kana tiup angin")."""
    offer = _seller_offer(offer_id, db, current)
    if offer.status != OfferStatus.ACCEPTED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Can only report ghosting on accepted offers")
    adab.apply_event(offer.buyer, AdabEventType.GHOSTED)
    # Free the listing back up for other buyers.
    offer.status = OfferStatus.DECLINED
    offer.listing.status = ListingStatus.ACTIVE
    # If the buyer had marked/verified funds, the fallen-through deal is refunded.
    if offer.payment_status in (PaymentStatus.PENDING, PaymentStatus.VERIFIED):
        offer.payment_status = PaymentStatus.REFUNDED
    db.commit()
    db.refresh(offer)
    return offer
