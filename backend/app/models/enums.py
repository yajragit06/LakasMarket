"""Enumerations shared across LakasMarket models."""
import enum


class SubscriptionTier(str, enum.Enum):
    """SaaS tiers. Governs listing limits and access to AI features."""

    BASIC = "basic"       # Free — up to 5 active listings, standard 20% floor
    PRO = "pro"           # AI Specs Guard, analytics, custom floor
    BUSINESS = "business" # Bulk tools, integrated escrow, priority support


class District(str, enum.Enum):
    """Brunei districts and key towns used by the logistics engine."""

    BANDAR = "bandar"          # Bandar Seri Begawan (Brunei-Muara)
    BRUNEI_MUARA = "brunei_muara"
    TUTONG = "tutong"
    SERIA = "seria"            # Belait
    KUALA_BELAIT = "kuala_belait"  # KB (Belait)
    TEMBURONG = "temburong"


class ListingStatus(str, enum.Enum):
    ACTIVE = "active"
    RESERVED = "reserved"
    SOLD = "sold"
    ARCHIVED = "archived"


class SaleMode(str, enum.Enum):
    """Controls the "Take Tonight" speed-premium behaviour."""

    FIRM = "firm"   # No speed discount; price is the price.
    FAST = "fast"   # Allows a capped speed discount (e.g. 5-10%).


class OfferStatus(str, enum.Enum):
    # Silently rejected below the hard floor — the seller is never notified.
    AUTO_REJECTED = "auto_rejected"
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class PaymentStatus(str, enum.Enum):
    """Manual 'Funds Verified' escrow states for an accepted deal.

    No PSP holds money in this flow — the platform records the verification
    state as a trust ledger. A real payment provider can later drive the same
    transitions programmatically (e.g. a webhook calling the verify endpoint).
    """
    NONE = "none"          # accepted, no payment action yet
    PENDING = "pending"    # buyer says funds sent (with a reference)
    VERIFIED = "verified"  # seller/admin confirmed receipt -> "Funds Verified"
    RELEASED = "released"  # deal completed after verification
    REFUNDED = "refunded"  # deal fell through after a payment was marked


class ConversationStatus(str, enum.Enum):
    OPEN = "open"
    GHOSTED = "ghosted"   # buyer went silent ("Hilang kana tiup angin")
    CLOSED = "closed"


class AdabEventType(str, enum.Enum):
    """Reputation events that adjust a user's Adab score."""

    COMPLETED_DEAL = "completed_deal"      # + reliability
    POLITE_INTERACTION = "polite_interaction"  # + communication
    GHOSTED = "ghosted"                    # - reliability ("Hilang kana tiup angin")
    RUDE = "rude"                          # - communication (extreme rudeness)
    NO_SHOW = "no_show"                    # - reliability
    QUIZ_PASSED = "quiz_passed"            # + communication (read the listing)
