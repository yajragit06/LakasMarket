"""Secure listing creation and retrieval endpoints."""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core import specs_guard
from app.core.rate_limit import RateLimiter
from app.database import get_db
from app.models.enums import District, ListingStatus, SaleMode, SubscriptionTier
from app.models.listing import DEFAULT_FLOOR_PERCENT, KnowledgeQuestion, Listing
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.listing import (
    AskAnswer,
    AskRequest,
    BulkListingCreate,
    ListingCreate,
    ListingPublic,
)

router = APIRouter(prefix="/listings", tags=["listings"])

# Cap LLM spend: 10 Specs Guard questions per minute per IP.
ask_limiter = RateLimiter(times=10, seconds=60)


def _active_listing_count(db: Session, seller_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Listing)
        .where(Listing.seller_id == seller_id, Listing.status == ListingStatus.ACTIVE)
    )


def _check_tier_features(payload: ListingCreate, tier: SubscriptionTier) -> None:
    """Basic sellers get the standard floor only and no negotiation bot."""
    if tier == SubscriptionTier.BASIC and payload.floor_percent != DEFAULT_FLOOR_PERCENT:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"The Basic plan uses the standard {DEFAULT_FLOOR_PERCENT:.0f}% price floor. "
            "Upgrade to Pro to set a custom Hard Floor.",
        )
    if tier == SubscriptionTier.BASIC and payload.negotiation_enabled:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "The AI Negotiation Bot is a Pro feature.",
        )


def _build_listing(payload: ListingCreate, seller_id: int, sub: Subscription | None) -> Listing:
    """Construct a Listing (with quiz questions) from a validated payload."""
    listing = Listing(
        seller_id=seller_id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        list_price=payload.list_price,
        floor_percent=payload.floor_percent,
        sale_mode=payload.sale_mode,
        speed_discount_percent=payload.speed_discount_percent,
        district=payload.district,
        delivery_available=payload.delivery_available,
        min_buyer_adab=payload.min_buyer_adab,
        negotiation_enabled=payload.negotiation_enabled,
    )

    # --- Product Knowledge Gateway questions ------------------------------
    for q in payload.knowledge_questions:
        if q.correct_index >= len(q.options):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "correct_index out of range")
        listing.knowledge_questions.append(
            KnowledgeQuestion(
                prompt=q.prompt,
                options=q.options,
                correct_index=q.correct_index,
                ai_generated=False,
            )
        )

    # Auto-generate via Specs Guard when the seller supplied none and their
    # tier includes it.
    if (
        not listing.knowledge_questions
        and payload.auto_generate_questions
        and sub
        and sub.has_specs_guard
    ):
        for gen in specs_guard.generate_questions(payload.title, payload.description, n=2):
            if gen["correct_index"] < len(gen["options"]):
                listing.knowledge_questions.append(
                    KnowledgeQuestion(
                        prompt=gen["prompt"],
                        options=gen["options"],
                        correct_index=gen["correct_index"],
                        ai_generated=True,
                    )
                )
    return listing


@router.post("", response_model=ListingPublic, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Listing:
    """Create a listing, enforcing the seller's SaaS tier limits.

    Requires authentication (secure creation). Enforces the Basic-tier active
    listing cap and standard floor, then attaches Product Knowledge Gateway
    questions — the seller's own, or AI-generated via Specs Guard (Pro+).
    """
    sub = current.subscription
    tier = sub.tier if sub else SubscriptionTier.BASIC
    limit = sub.listing_limit if sub else 5

    if limit is not None and _active_listing_count(db, current.id) >= limit:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Your {tier.value} plan allows up to {limit} active listings. "
            "Upgrade to Pro for unlimited listings.",
        )
    _check_tier_features(payload, tier)

    listing = _build_listing(payload, current.id, sub)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.post("/bulk", response_model=list[ListingPublic], status_code=status.HTTP_201_CREATED)
def bulk_create_listings(
    payload: BulkListingCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Listing]:
    """Create up to 50 listings in one call — a Business-tier tool.

    AI question generation is skipped in bulk (cost control); sellers supply
    their own questions per listing or add them later.
    """
    sub = current.subscription
    if sub is None or sub.tier != SubscriptionTier.BUSINESS:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Bulk upload is a Business-plan feature.",
        )

    listings = [_build_listing(item, current.id, sub=None) for item in payload.listings]
    db.add_all(listings)
    db.commit()
    for listing in listings:
        db.refresh(listing)
    return listings


@router.get("", response_model=list[ListingPublic])
def list_active(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="Free-text search on title/description"),
    district: District | None = None,
    category: str | None = None,
    sale_mode: SaleMode | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    limit: int = 50,
    offset: int = 0,
) -> list[Listing]:
    """Browse active listings with optional search and filters.

    Eager-loads the seller and quiz so serialization (including the buyer-facing
    Adab snapshot) doesn't trigger N+1 queries.
    """
    stmt = (
        select(Listing)
        .where(Listing.status == ListingStatus.ACTIVE)
        .options(selectinload(Listing.seller), selectinload(Listing.knowledge_questions))
    )

    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Listing.title.ilike(like), Listing.description.ilike(like)))
    if district is not None:
        stmt = stmt.where(Listing.district == district)
    if category:
        stmt = stmt.where(Listing.category == category)
    if sale_mode is not None:
        stmt = stmt.where(Listing.sale_mode == sale_mode)
    if min_price is not None:
        stmt = stmt.where(Listing.list_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Listing.list_price <= max_price)

    stmt = stmt.order_by(Listing.created_at.desc()).limit(min(limit, 100)).offset(offset)
    return list(db.scalars(stmt).all())


@router.get("/mine", response_model=list[ListingPublic])
def my_listings(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Listing]:
    """The authenticated seller's own listings (any status), newest first."""
    stmt = (
        select(Listing)
        .where(Listing.seller_id == current.id)
        .order_by(Listing.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.post("/{listing_id}/ask", response_model=AskAnswer, dependencies=[Depends(ask_limiter)])
def ask_specs_guard(
    listing_id: int,
    payload: AskRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> AskAnswer:
    """Ask the AI Specs Guard a question about a listing.

    Only answers automatically when the *seller* is on a plan that includes the
    Specs Guard (Pro/Business). Otherwise the buyer is nudged to read the
    description — the whole point of reducing redundant questions.
    """
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")

    seller_sub = listing.seller.subscription
    if seller_sub is None or not seller_sub.has_specs_guard:
        return AskAnswer(
            answer="This seller's plan doesn't include the AI Specs Guard. "
            "Please check the description — it likely already answers this.",
            specs_guard_enabled=False,
        )

    answer = specs_guard.answer_question(listing.description, payload.question)
    return AskAnswer(answer=answer, specs_guard_enabled=True)


@router.get("/{listing_id}", response_model=ListingPublic)
def get_listing(listing_id: int, db: Session = Depends(get_db)) -> Listing:
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    return listing
