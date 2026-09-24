"""AI Negotiation Bot engine (Pro tier).

Negotiates on the seller's behalf within their rules. The core is *deterministic
and safe*: the bot never proposes a price below a soft anchor set above the
seller's true Hard Floor, so the floor itself is never revealed or breached — no
matter what an LLM might otherwise say. An LLM is used only to phrase the
message text (optional, with a templated fallback).
"""
from dataclasses import dataclass

from app.core.anti_lowball import _speed_floor
from app.models.enums import SaleMode
from app.models.listing import Listing


@dataclass(frozen=True)
class NegotiationResult:
    action: str  # "accept" | "counter"
    counter_price: float | None
    # Effective floor used internally — NOT to be exposed to the buyer.
    floor: float


def _effective_floor(listing: Listing, is_take_tonight: bool) -> float:
    hard = listing.hard_floor_price
    if is_take_tonight and listing.sale_mode == SaleMode.FAST:
        return max(hard, _speed_floor(listing))
    if is_take_tonight:  # FIRM: no speed concession
        return max(hard, float(listing.list_price))
    return hard


def negotiate(listing: Listing, buyer_price: float, is_take_tonight: bool) -> NegotiationResult:
    """Decide whether to accept the buyer's price or counter.

    - Accept if the buyer meets/beats the asking price, or already meets the
      counter the bot would otherwise make.
    - Otherwise counter at the midpoint of the buyer's price and list price,
      but never below the *soft anchor* (midpoint of floor and list). This keeps
      the true Hard Floor hidden and stops the bot from caving on a hard lowball.
    """
    list_price = float(listing.list_price)
    floor = _effective_floor(listing, is_take_tonight)
    # For a FIRM take-tonight, floor == list_price; nothing to negotiate.
    if buyer_price >= list_price or floor >= list_price:
        return NegotiationResult("accept" if buyer_price >= list_price else "counter",
                                 None if buyer_price >= list_price else round(list_price, 2),
                                 floor)

    soft_anchor = round((floor + list_price) / 2, 2)
    counter = min(list_price, max(soft_anchor, round((buyer_price + list_price) / 2, 2)))

    if buyer_price >= counter:
        return NegotiationResult("accept", None, floor)
    return NegotiationResult("counter", round(counter, 2), floor)


def compose_reply(result: NegotiationResult, buyer_price: float) -> str:
    """Templated, floor-safe message text for the bot's reply."""
    if result.action == "accept":
        return (
            f"Deal — B$ {buyer_price:.2f} works. Send a formal offer at that "
            "price and I'll confirm. 🤖"
        )
    return (
        f"Thanks for the offer. B$ {buyer_price:.2f} is a bit low for this one — "
        f"I could do B$ {result.counter_price:.2f}. Let me know. 🤖"
    )
