"""Seller analytics schemas (Pro/Business)."""
from pydantic import BaseModel


class SellerAnalytics(BaseModel):
    """Mirrors the PRD's success metrics from one seller's point of view."""

    active_listings: int
    reserved_listings: int
    sold_listings: int
    # The headline: offers so insulting the platform absorbed them for you.
    lowballs_blocked: int
    pending_offers: int
    accepted_offers: int
    expired_take_tonight_offers: int
    # Chat health (PRD §7 ghosting rate).
    conversations: int
    ghosted_conversations: int
    # Trust: deals where funds were verified via manual escrow.
    funds_verified_deals: int
    # Average visible (non-lowball) offer as a % of list price — tracks the
    # PRD's "sale value vs target price" metric. None until offers exist.
    avg_offer_percent_of_list: float | None
