"""The Anti-Lowball Engine.

Evaluates an incoming offer against a listing's Hard Floor and "Take Tonight"
speed-premium rules. Offers below the floor are *silently* rejected: the
engine returns a decision that keeps the offer invisible to the seller so
their "sentiment" is never bruised by an insulting number.
"""
from dataclasses import dataclass

from app.models.enums import OfferStatus, SaleMode
from app.models.listing import Listing


@dataclass(frozen=True)
class OfferDecision:
    status: OfferStatus
    # Reason is for audit/analytics only and must not be shown to the seller
    # when the offer was auto-rejected.
    reason: str | None
    floor_price: float
    # Effective minimum for this specific offer (accounts for speed discount).
    effective_floor: float


def _speed_floor(listing: Listing) -> float:
    """Lowest price allowed for a legitimate 'take tonight' offer.

    A FAST-mode listing allows a small, capped speed discount below the list
    price. A FIRM-mode listing grants no speed concession at all.
    """
    list_price = float(listing.list_price)
    if listing.sale_mode == SaleMode.FAST:
        return round(list_price * (1 - listing.speed_discount_percent / 100), 2)
    return list_price


def evaluate_offer(listing: Listing, amount: float, is_take_tonight: bool) -> OfferDecision:
    """Decide whether an offer should surface to the seller or be dropped.

    - Below the hard floor  -> AUTO_REJECTED (silent).
    - "Take tonight" but below the capped speed floor -> AUTO_REJECTED (silent),
      preventing buyers from weaponising speed to "scalp crumbs".
    - Otherwise             -> PENDING (seller sees it).
    """
    hard_floor = listing.hard_floor_price

    if amount < hard_floor:
        return OfferDecision(
            status=OfferStatus.AUTO_REJECTED,
            reason="below_hard_floor",
            floor_price=hard_floor,
            effective_floor=hard_floor,
        )

    if is_take_tonight:
        speed_floor = _speed_floor(listing)
        # The effective floor for a speed offer is the stricter of the two.
        effective = max(hard_floor, speed_floor)
        if amount < effective:
            return OfferDecision(
                status=OfferStatus.AUTO_REJECTED,
                reason="below_speed_floor",
                floor_price=hard_floor,
                effective_floor=effective,
            )
        return OfferDecision(
            status=OfferStatus.PENDING,
            reason=None,
            floor_price=hard_floor,
            effective_floor=effective,
        )

    return OfferDecision(
        status=OfferStatus.PENDING,
        reason=None,
        floor_price=hard_floor,
        effective_floor=hard_floor,
    )
