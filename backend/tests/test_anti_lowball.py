"""Tests for the Anti-Lowball Engine."""
from app.core.anti_lowball import evaluate_offer
from app.models.enums import OfferStatus, SaleMode
from app.models.listing import Listing


def make_listing(**kw) -> Listing:
    defaults = dict(
        list_price=100,
        floor_percent=20.0,
        sale_mode=SaleMode.FIRM,
        speed_discount_percent=7.5,
    )
    defaults.update(kw)
    return Listing(**defaults)


def test_hard_floor_price_computation():
    assert make_listing().hard_floor_price == 80.0
    assert make_listing(floor_percent=30).hard_floor_price == 70.0


def test_offer_below_floor_is_silently_rejected():
    listing = make_listing()  # floor at 80
    decision = evaluate_offer(listing, amount=25, is_take_tonight=False)
    assert decision.status == OfferStatus.AUTO_REJECTED
    assert decision.reason == "below_hard_floor"


def test_offer_at_floor_is_pending():
    listing = make_listing()
    decision = evaluate_offer(listing, amount=80, is_take_tonight=False)
    assert decision.status == OfferStatus.PENDING
    assert decision.reason is None


def test_take_tonight_firm_mode_grants_no_speed_discount():
    # FIRM listing: speed floor is the full list price (100), not the 80 floor.
    listing = make_listing(sale_mode=SaleMode.FIRM)
    decision = evaluate_offer(listing, amount=90, is_take_tonight=True)
    assert decision.status == OfferStatus.AUTO_REJECTED
    assert decision.reason == "below_speed_floor"
    assert decision.effective_floor == 100.0


def test_take_tonight_fast_mode_caps_discount():
    # FAST listing with 7.5% speed discount -> speed floor 92.5.
    listing = make_listing(sale_mode=SaleMode.FAST, speed_discount_percent=7.5)
    assert evaluate_offer(listing, 92.5, True).status == OfferStatus.PENDING
    assert evaluate_offer(listing, 90, True).status == OfferStatus.AUTO_REJECTED
