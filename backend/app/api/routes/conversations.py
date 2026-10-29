"""Chat endpoints — quiz/Adab-gated buyer↔seller messaging."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import adab
from app.core.knowledge_gateway import grade_quiz
from app.core.negotiation import compose_reply, negotiate
from app.database import get_db
from app.models.conversation import Conversation, Message
from app.models.enums import (
    AdabEventType,
    ConversationStatus,
    ListingStatus,
    SubscriptionTier,
)
from app.models.listing import Listing
from app.models.user import User
from app.schemas.conversation import (
    ConversationDetail,
    ConversationStart,
    ConversationSummary,
    MessageCreate,
    MessagePublic,
    NegotiateRequest,
    NegotiateResponse,
)

router = APIRouter(tags=["chat"])


def _get_participant_conversation(conv_id: int, db: Session, user: User) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    if user.id not in (conv.buyer_id, conv.seller_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a participant")
    return conv


@router.post("/listings/{listing_id}/conversations", response_model=ConversationDetail)
def start_conversation(
    listing_id: int,
    payload: ConversationStart,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Conversation:
    """Open (or re-open) a chat with a seller.

    First contact is gated exactly like an offer: the buyer must clear the
    Product Knowledge Gateway and meet the seller's minimum Adab. Re-opening an
    existing thread skips the gate (already passed).
    """
    listing = db.get(Listing, listing_id)
    if listing is None or listing.status == ListingStatus.ARCHIVED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not available")
    if listing.seller_id == current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot message your own listing")

    existing = db.scalar(
        select(Conversation).where(
            Conversation.listing_id == listing_id, Conversation.buyer_id == current.id
        )
    )
    if existing is None:
        # --- Adab gate ---------------------------------------------------
        if current.adab_score < listing.min_buyer_adab:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Your Adab score is below this seller's minimum for contact.",
            )
        # --- Product Knowledge Gateway -----------------------------------
        quiz = grade_quiz(listing, payload.quiz_answers)
        if not quiz.passed:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Answer the listing's questions correctly first "
                f"({quiz.correct}/{quiz.total}). Re-read the description.",
            )
        if quiz.total > 0:
            adab.apply_event(current, AdabEventType.QUIZ_PASSED)

        existing = Conversation(
            listing_id=listing_id,
            buyer_id=current.id,
            seller_id=listing.seller_id,
        )
        db.add(existing)
        db.flush()

    if payload.opening_message:
        existing.messages.append(Message(sender_id=current.id, body=payload.opening_message))

    db.commit()
    db.refresh(existing)
    return existing


@router.get("/conversations", response_model=list[ConversationSummary])
def my_conversations(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Conversation]:
    """All threads where the current user is buyer or seller."""
    stmt = (
        select(Conversation)
        .where(or_(Conversation.buyer_id == current.id, Conversation.seller_id == current.id))
        .order_by(Conversation.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/conversations/{conv_id}", response_model=ConversationDetail)
def get_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Conversation:
    conv = _get_participant_conversation(conv_id, db, current)
    # Mark the other party's unread messages as read.
    now = datetime.now(timezone.utc)
    changed = False
    for msg in conv.messages:
        if msg.sender_id != current.id and msg.read_at is None:
            msg.read_at = now
            changed = True
    if changed:
        db.commit()
        db.refresh(conv)
    return conv


@router.post("/conversations/{conv_id}/messages", response_model=MessagePublic)
def send_message(
    conv_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Message:
    conv = _get_participant_conversation(conv_id, db, current)
    if conv.status == ConversationStatus.CLOSED:
        raise HTTPException(status.HTTP_409_CONFLICT, "This conversation is closed")

    # A buyer replying to a thread they'd been marked as ghosting re-opens it.
    if conv.status == ConversationStatus.GHOSTED and current.id == conv.buyer_id:
        conv.status = ConversationStatus.OPEN

    message = Message(conversation_id=conv.id, sender_id=current.id, body=payload.body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.post("/conversations/{conv_id}/negotiate", response_model=NegotiateResponse)
def negotiate_price(
    conv_id: int,
    payload: NegotiateRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> NegotiateResponse:
    """Buyer proposes a price; the seller's AI bot auto-replies in the thread.

    Requires the listing's negotiation bot to be enabled and the seller to be on
    a plan that includes it. The bot's counter is computed deterministically and
    can never dip below the seller's floor, so the LLM (if any) only phrases it.
    """
    conv = _get_participant_conversation(conv_id, db, current)
    if current.id != conv.buyer_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the buyer can propose a price")
    if conv.status == ConversationStatus.CLOSED:
        raise HTTPException(status.HTTP_409_CONFLICT, "This conversation is closed")

    listing = db.get(Listing, conv.listing_id)
    seller_sub = listing.seller.subscription if listing else None
    if (
        listing is None
        or not listing.negotiation_enabled
        or seller_sub is None
        or seller_sub.tier == SubscriptionTier.BASIC
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The AI Negotiation Bot isn't enabled for this listing.",
        )

    result = negotiate(listing, float(payload.proposed_price), is_take_tonight=False)
    # The bot speaks for the seller in the thread.
    bot_message = Message(
        conversation_id=conv.id,
        sender_id=conv.seller_id,
        body=compose_reply(result, float(payload.proposed_price)),
    )
    db.add(bot_message)
    if conv.status == ConversationStatus.GHOSTED:
        conv.status = ConversationStatus.OPEN
    db.commit()
    db.refresh(bot_message)
    return NegotiateResponse(
        action=result.action,
        counter_price=result.counter_price,
        message=bot_message,
    )


@router.post("/conversations/{conv_id}/report-ghost", response_model=ConversationSummary)
def report_ghost(
    conv_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Conversation:
    """Seller reports a buyer who went silent after the seller engaged.

    Only valid when the seller has replied and the buyer hasn't answered (the
    last message is the seller's) — this is the measurable "ghosting" signal.
    """
    conv = _get_participant_conversation(conv_id, db, current)
    if current.id != conv.seller_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the seller can report ghosting")
    if conv.status != ConversationStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conversation is not open")
    if not conv.messages or conv.messages[-1].sender_id != conv.seller_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Can only report ghosting once you've replied and the buyer has gone silent.",
        )

    adab.apply_event(conv.buyer, AdabEventType.GHOSTED)
    conv.status = ConversationStatus.GHOSTED
    db.commit()
    db.refresh(conv)
    return conv
