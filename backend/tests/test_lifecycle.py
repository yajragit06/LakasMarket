"""Tests for offer lifecycle rules (take-tonight expiry)."""
from datetime import datetime, timedelta, timezone

from app.core.lifecycle import TAKE_TONIGHT_TTL, expire_stale_offers
from app.models.enums import OfferStatus
from app.models.offer import Offer

NOW = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)


def make_offer(**kw) -> Offer:
    defaults = dict(status=OfferStatus.PENDING, is_take_tonight=True, created_at=NOW)
    defaults.update(kw)
    return Offer(**defaults)


def test_stale_take_tonight_offer_expires():
    offer = make_offer(created_at=NOW - TAKE_TONIGHT_TTL - timedelta(minutes=1))
    assert expire_stale_offers([offer], now=NOW) == [offer]
    assert offer.status == OfferStatus.EXPIRED


def test_fresh_take_tonight_offer_survives():
    offer = make_offer(created_at=NOW - timedelta(hours=2))
    assert expire_stale_offers([offer], now=NOW) == []
    assert offer.status == OfferStatus.PENDING


def test_regular_offers_never_expire():
    offer = make_offer(is_take_tonight=False, created_at=NOW - timedelta(days=30))
    assert expire_stale_offers([offer], now=NOW) == []


def test_non_pending_offers_untouched():
    offer = make_offer(
        status=OfferStatus.ACCEPTED, created_at=NOW - TAKE_TONIGHT_TTL - timedelta(days=1)
    )
    assert expire_stale_offers([offer], now=NOW) == []
    assert offer.status == OfferStatus.ACCEPTED


def test_naive_created_at_treated_as_utc():
    # SQLite returns naive datetimes even for timezone-aware columns.
    naive = (NOW - TAKE_TONIGHT_TTL - timedelta(hours=1)).replace(tzinfo=None)
    offer = make_offer(created_at=naive)
    assert expire_stale_offers([offer], now=NOW) == [offer]
