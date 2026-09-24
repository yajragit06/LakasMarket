"""Manual 'Funds Verified' escrow — the payment-state machine.

Deliberately small and provider-agnostic: it encodes only the *legal
transitions* between payment states. Today they're driven by buyer/seller
actions; a real PSP can later drive the same transitions from a webhook without
changing this module.
"""
from app.models.enums import PaymentStatus

# current -> allowed next states
_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.NONE: {PaymentStatus.PENDING},
    PaymentStatus.PENDING: {PaymentStatus.VERIFIED, PaymentStatus.REFUNDED},
    PaymentStatus.VERIFIED: {PaymentStatus.RELEASED, PaymentStatus.REFUNDED},
    PaymentStatus.RELEASED: set(),
    PaymentStatus.REFUNDED: set(),
}


class InvalidTransition(ValueError):
    """Raised when a payment-state transition is not permitted."""


def can_transition(current: PaymentStatus, target: PaymentStatus) -> bool:
    return target in _TRANSITIONS[current]


def assert_transition(current: PaymentStatus, target: PaymentStatus) -> None:
    if not can_transition(current, target):
        raise InvalidTransition(f"Cannot move payment from {current.value} to {target.value}")
