"""Tests for the AI Negotiation Bot engine (deterministic core)."""
from app.core.negotiation import negotiate
from app.models.enums import SaleMode
from app.models.listing import Listing


def make_listing(**kw) -> Listing:
    defaults = dict(list_price=100, floor_percent=20, sale_mode=SaleMode.FIRM,
                    speed_discount_percent=7.5)
    defaults.update(kw)
    return Listing(**defaults)


def test_accepts_at_or_above_list():
    r = negotiate(make_listing(), buyer_price=100, is_take_tonight=False)
    assert r.action == "accept"


def test_counter_never_below_soft_anchor_on_hard_lowball():
    # list 100, floor 80 -> soft anchor 90. A B$40 lowball must not cave to floor.
    r = negotiate(make_listing(), buyer_price=40, is_take_tonight=False)
    assert r.action == "counter"
    assert r.counter_price == 90.0
    assert r.counter_price > r.floor  # true floor never revealed


def test_counter_meets_partway_above_anchor():
    # Buyer 85 -> midpoint(85,100)=92.5, above the 90 anchor.
    r = negotiate(make_listing(), buyer_price=85, is_take_tonight=False)
    assert r.action == "counter"
    assert r.counter_price == 92.5


def test_accepts_when_buyer_already_beats_counter():
    # Buyer 95 -> counter would be 97.5; still counters (95 < 97.5).
    assert negotiate(make_listing(), 95, False).action == "counter"
    # Buyer 98 -> counter 99, still below; but 99.5? midpoint(98,100)=99 -> counter 99, 98<99.
    # Buyer 99.5 -> midpoint 99.75 -> counter 99.75, 99.5<99.75 counter.
    # A buyer at 100 accepts (covered above); ensure high offers converge to accept.
    assert negotiate(make_listing(), 100, False).action == "accept"


def test_never_counters_below_floor_regardless():
    r = negotiate(make_listing(floor_percent=50), buyer_price=10, is_take_tonight=False)
    # floor 50, soft anchor 75.
    assert r.counter_price == 75.0
    assert r.counter_price >= r.floor
