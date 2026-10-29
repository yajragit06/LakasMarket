"""Unit tests for the escrow payment-state machine."""
import pytest

from app.core import escrow
from app.core.escrow import InvalidTransition
from app.models.enums import PaymentStatus as P


@pytest.mark.parametrize(
    "current,target,ok",
    [
        (P.NONE, P.PENDING, True),
        (P.NONE, P.VERIFIED, False),      # can't skip the buyer's mark-sent
        (P.PENDING, P.VERIFIED, True),
        (P.PENDING, P.REFUNDED, True),
        (P.VERIFIED, P.RELEASED, True),
        (P.VERIFIED, P.REFUNDED, True),
        (P.RELEASED, P.REFUNDED, False),  # terminal
        (P.REFUNDED, P.VERIFIED, False),  # terminal
        (P.VERIFIED, P.PENDING, False),   # no going backwards
    ],
)
def test_transitions(current, target, ok):
    assert escrow.can_transition(current, target) is ok
    if ok:
        escrow.assert_transition(current, target)
    else:
        with pytest.raises(InvalidTransition):
            escrow.assert_transition(current, target)
