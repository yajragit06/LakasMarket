"""Adab (courtesy) scoring engine.

Adjusts a user's dual reputation (reliability + communication) in response to
behavioural events. Ghosting ("Hilang kana tiup angin") and rudeness cost
points; completing deals and reading listings earn them.
"""
from app.models.enums import AdabEventType
from app.models.user import ADAB_MAX, ADAB_MIN, User

# Point deltas per event. Positive lifts, negative penalties.
_RELIABILITY_DELTAS: dict[AdabEventType, float] = {
    AdabEventType.COMPLETED_DEAL: 4.0,
    AdabEventType.GHOSTED: -12.0,   # heaviest penalty — the core problem
    AdabEventType.NO_SHOW: -8.0,
}

_COMMUNICATION_DELTAS: dict[AdabEventType, float] = {
    AdabEventType.POLITE_INTERACTION: 2.0,
    AdabEventType.QUIZ_PASSED: 1.0,
    AdabEventType.RUDE: -10.0,
}


def _clamp(value: float) -> float:
    return max(ADAB_MIN, min(ADAB_MAX, round(value, 1)))


def apply_event(user: User, event: AdabEventType) -> User:
    """Mutate ``user`` in place for a reputation event and return it.

    The caller is responsible for committing the session.
    """
    if event in _RELIABILITY_DELTAS:
        user.reliability_score = _clamp(user.reliability_score + _RELIABILITY_DELTAS[event])
    if event in _COMMUNICATION_DELTAS:
        user.communication_score = _clamp(user.communication_score + _COMMUNICATION_DELTAS[event])

    # Counters may be unset (None) on an object not yet flushed to the DB.
    if event == AdabEventType.COMPLETED_DEAL:
        user.completed_deals = (user.completed_deals or 0) + 1
    elif event == AdabEventType.GHOSTED:
        user.ghost_count = (user.ghost_count or 0) + 1

    return user
