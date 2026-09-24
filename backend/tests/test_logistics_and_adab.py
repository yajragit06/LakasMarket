"""Tests for the logistics and Adab engines."""
from app.core import adab
from app.core.logistics import delivery_fee, distance_km
from app.models.enums import AdabEventType, District
from app.models.user import ADAB_MAX, ADAB_MIN, User


def test_local_delivery_is_free():
    assert delivery_fee(District.BANDAR, District.BANDAR) == 0.0
    # Bandar <-> Brunei-Muara is within the free radius.
    assert delivery_fee(District.BANDAR, District.BRUNEI_MUARA) == 0.0


def test_distant_district_incurs_fair_fee():
    # Bandar -> Seria (~95km) should cost meaningfully more than a local hop.
    fee = delivery_fee(District.BANDAR, District.SERIA)
    assert fee > 15
    assert distance_km(District.SERIA, District.KUALA_BELAIT) == 12


def make_user() -> User:
    return User(
        email="a@b.com",
        hashed_password="x",
        display_name="Test",
        reliability_score=70.0,
        communication_score=70.0,
    )


def test_ghosting_deducts_reliability():
    user = make_user()
    adab.apply_event(user, AdabEventType.GHOSTED)
    assert user.reliability_score == 58.0
    assert user.ghost_count == 1


def test_rudeness_deducts_communication():
    user = make_user()
    adab.apply_event(user, AdabEventType.RUDE)
    assert user.communication_score == 60.0


def test_completed_deal_rewards_and_counts():
    user = make_user()
    adab.apply_event(user, AdabEventType.COMPLETED_DEAL)
    assert user.reliability_score == 74.0
    assert user.completed_deals == 1


def test_scores_are_clamped():
    user = make_user()
    user.reliability_score = ADAB_MIN
    adab.apply_event(user, AdabEventType.GHOSTED)
    assert user.reliability_score == ADAB_MIN

    user.communication_score = ADAB_MAX
    adab.apply_event(user, AdabEventType.POLITE_INTERACTION)
    assert user.communication_score == ADAB_MAX
