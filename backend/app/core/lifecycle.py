"""Offer lifecycle rules.

A "take tonight" offer's entire premise is same-day urgency — if it sits
unanswered past its window, the urgency claim was hollow and the offer
lapses (PRD: real-time "Take Now" timers). Expiry is applied lazily when a
seller reads or acts on offers, so no background scheduler is needed.
"""
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.models.enums import OfferStatus
from app.models.offer import Offer

TAKE_TONIGHT_TTL = timedelta(hours=24)


def expire_stale_offers(offers: Iterable[Offer], now: datetime | None = None) -> list[Offer]:
    """Mark stale pending "take tonight" offers EXPIRED; return those changed.

    The caller is responsible for committing the session.
    """
    now = now or datetime.now(timezone.utc)
    expired: list[Offer] = []
    for offer in offers:
        if offer.status != OfferStatus.PENDING or not offer.is_take_tonight:
            continue
        if offer.created_at is None:
            continue
        created = offer.created_at
        # SQLite returns naive datetimes even for timezone=True columns.
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if now - created > TAKE_TONIGHT_TTL:
            offer.status = OfferStatus.EXPIRED
            expired.append(offer)
    return expired
