"""Subscription (SaaS tier) endpoints, with a manual billing gate.

Upgrading to a paid tier does NOT flip the plan immediately: it records a
pending upgrade, the user marks payment sent, and an admin verifies it — the
same provider-agnostic verification pattern as the escrow flow. A real PSP can
later drive `activate` from a webhook. Downgrades to Basic are immediate (no
billing) and cancel any in-flight upgrade.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import escrow
from app.database import get_db
from app.models.enums import PaymentStatus, SubscriptionTier
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import BillingMark, SubscriptionPublic, UpgradeRequest

router = APIRouter(prefix="/subscription", tags=["subscription"])


def _get_or_create(db: Session, user: User) -> Subscription:
    sub = user.subscription
    if sub is None:
        sub = Subscription(user_id=user.id, tier=SubscriptionTier.BASIC)
        db.add(sub)
        db.flush()
        user.subscription = sub
    return sub


def _activate(sub: Subscription, tier: SubscriptionTier) -> None:
    """Apply a (paid) tier and clear any pending billing state."""
    sub.tier = tier
    sub.renews_at = (
        None if tier == SubscriptionTier.BASIC else datetime.now(timezone.utc) + timedelta(days=30)
    )
    sub.pending_tier = None
    sub.payment_status = PaymentStatus.NONE
    sub.payment_reference = None


@router.get("", response_model=SubscriptionPublic)
def get_my_subscription(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Subscription:
    sub = _get_or_create(db, current)
    db.commit()
    db.refresh(sub)
    return sub


@router.post("/upgrade", response_model=SubscriptionPublic)
def change_tier(
    payload: UpgradeRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Subscription:
    """Downgrade to Basic immediately, or request a paid upgrade (billing-gated).

    A paid upgrade records a pending request; the plan only changes once the
    payment is verified. See /payment/mark-sent and /{user_id}/activate.
    """
    sub = _get_or_create(db, current)

    if payload.tier == sub.tier and sub.pending_tier is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Already on the {payload.tier.value} plan")

    if payload.tier == SubscriptionTier.BASIC:
        # Downgrade / cancel is free and immediate.
        _activate(sub, SubscriptionTier.BASIC)
    else:
        # Paid upgrade: stage it, awaiting payment. Tier is unchanged for now.
        sub.pending_tier = payload.tier
        sub.payment_status = PaymentStatus.NONE
        sub.payment_reference = None

    db.commit()
    db.refresh(sub)
    return sub


@router.post("/payment/mark-sent", response_model=SubscriptionPublic)
def mark_billing_sent(
    payload: BillingMark,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Subscription:
    """User records they've paid for their pending upgrade → awaits verification."""
    sub = _get_or_create(db, current)
    if sub.pending_tier is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No pending upgrade to pay for")
    try:
        escrow.assert_transition(sub.payment_status, PaymentStatus.PENDING)
    except escrow.InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))

    sub.payment_status = PaymentStatus.PENDING
    sub.payment_reference = payload.reference
    db.commit()
    db.refresh(sub)
    return sub


@router.post("/{user_id}/activate", response_model=SubscriptionPublic)
def activate_upgrade(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Subscription:
    """Admin confirms payment received and activates the pending upgrade.

    This is the single choke point a real PSP webhook would call instead.
    """
    if not current.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an admin can activate upgrades")
    target = db.get(User, user_id)
    sub = target.subscription if target else None
    if sub is None or sub.pending_tier is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No pending upgrade for that user")
    if sub.payment_status != PaymentStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The user must mark payment as sent before it can be activated.",
        )

    _activate(sub, sub.pending_tier)
    db.commit()
    db.refresh(sub)
    return sub
