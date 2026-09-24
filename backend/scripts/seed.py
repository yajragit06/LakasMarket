"""Seed the database with demo data illustrating LakasMarket's core flows.

Run from the backend directory (with DATABASE_URL configured):

    python scripts/seed.py

Idempotent: existing demo users are left untouched.
"""
import os
import sys

# Ensure the backend package root is importable when run as `scripts/seed.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.anti_lowball import evaluate_offer
from app.core.logistics import delivery_fee
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.enums import District, SaleMode, SubscriptionTier
from app.models.listing import KnowledgeQuestion, Listing
from app.models.offer import Offer
from app.models.subscription import Subscription
from app.models.user import User


def get_or_create_user(db, email, name, district, tier) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        display_name=name,
        home_district=district,
    )
    user.subscription = Subscription(tier=tier)
    db.add(user)
    db.flush()
    return user


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # A Pro tech reseller in Bandar, and a buyer out in Seria.
        alice = get_or_create_user(
            db, "alice@lakas.bn", "Alice (Tech Reseller)", District.BANDAR, SubscriptionTier.PRO
        )
        bob = get_or_create_user(
            db, "bob@lakas.bn", "Bob", District.SERIA, SubscriptionTier.BASIC
        )

        if db.scalar(select(Listing).where(Listing.seller_id == alice.id)):
            print("Demo listings already present — nothing to do.")
            return

        keyboard = Listing(
            seller_id=alice.id,
            title="Ducky One 3 — Wired Mechanical Keyboard",
            description=(
                "Ducky One 3, WIRED only (no Bluetooth/wireless). Brown switches. "
                "Comes WITHOUT the original box. Light use, no defects."
            ),
            category="Keyboards",
            list_price=120,
            floor_percent=25,  # hard floor = 90
            sale_mode=SaleMode.FIRM,
            district=District.BANDAR,
            min_buyer_adab=0,
        )
        keyboard.knowledge_questions.append(
            KnowledgeQuestion(
                prompt="Is this keyboard wired or wireless?",
                options=["Wired", "Wireless"],
                correct_index=0,
                ai_generated=False,
            )
        )
        db.add(keyboard)
        db.flush()

        # A lowball from Bob ($40) — silently auto-rejected, seller never sees it.
        lowball = evaluate_offer(keyboard, 40, is_take_tonight=False)
        db.add(
            Offer(
                listing_id=keyboard.id,
                buyer_id=bob.id,
                amount=40,
                status=lowball.status,
                rejection_reason=lowball.reason,
                floor_price_at_offer=lowball.floor_price,
                passed_knowledge_gate=True,
            )
        )

        # A fair offer from Bob ($100) with delivery to Seria — reaches the seller.
        fee = delivery_fee(keyboard.district, bob.home_district)
        fair = evaluate_offer(keyboard, 100, is_take_tonight=False)
        db.add(
            Offer(
                listing_id=keyboard.id,
                buyer_id=bob.id,
                amount=100,
                status=fair.status,
                floor_price_at_offer=fair.floor_price,
                delivery_fee=fee,
                passed_knowledge_gate=True,
            )
        )

        db.commit()
        print("Seeded demo data:")
        print(f"  Seller: {alice.email} (Pro)   Buyer: {bob.email} (Basic)")
        print(f"  Listing '{keyboard.title}' — hard floor B$ {keyboard.hard_floor_price:.2f}")
        print(f"  Lowball B$40 -> {lowball.status.value} (hidden from seller)")
        print(f"  Fair offer B$100 -> {fair.status.value}, delivery to Seria B$ {fee:.2f}")
        print("  Login with password: password123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
