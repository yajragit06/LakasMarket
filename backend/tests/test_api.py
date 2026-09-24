"""End-to-end API tests covering the auth, listing, and offer flows."""
from tests.conftest import auth_headers, set_tier

LISTING = {
    "title": "Mechanical keyboard",
    "description": "A wired mechanical keyboard, barely used, no box.",
    "list_price": 100,
    "floor_percent": 20,  # hard floor = 80
}


def test_register_and_me(client):
    headers = auth_headers(client, "seller@example.com")
    me = client.get("/auth/me", headers=headers).json()
    assert me["display_name"] == "seller"
    assert me["adab_score"] == 70.0  # neutral baseline


def test_listing_creation_requires_auth(client):
    assert client.post("/listings", json=LISTING).status_code == 401


def test_create_and_browse_listing(client):
    headers = auth_headers(client, "seller@example.com")
    res = client.post("/listings", json=LISTING, headers=headers)
    assert res.status_code == 201
    body = res.json()
    assert body["hard_floor_price"] == 80.0
    assert body["seller"]["display_name"] == "seller"

    listings = client.get("/listings").json()
    assert len(listings) == 1
    assert listings[0]["title"] == LISTING["title"]


def test_search_filter(client):
    headers = auth_headers(client, "seller@example.com")
    client.post("/listings", json=LISTING, headers=headers)
    client.post(
        "/listings",
        json={**LISTING, "title": "Office chair", "description": "Ergonomic chair"},
        headers=headers,
    )
    assert len(client.get("/listings?q=keyboard").json()) == 1
    assert len(client.get("/listings?max_price=1").json()) == 0


def test_basic_tier_listing_limit(client):
    headers = auth_headers(client, "seller@example.com")
    for i in range(5):
        r = client.post("/listings", json={**LISTING, "title": f"Item {i}"}, headers=headers)
        assert r.status_code == 201
    # 6th exceeds the Basic tier cap of 5.
    r = client.post("/listings", json={**LISTING, "title": "Item 6"}, headers=headers)
    assert r.status_code == 402


def _create_listing(client, headers, **overrides) -> int:
    res = client.post("/listings", json={**LISTING, **overrides}, headers=headers)
    assert res.status_code == 201
    return res.json()["id"]


def test_lowball_is_silently_rejected(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _create_listing(client, seller)

    res = client.post(f"/listings/{lid}/offers", json={"amount": 25}, headers=buyer)
    assert res.status_code == 201
    assert res.json()["accepted_for_review"] is False  # neutral to buyer

    # Seller never sees the lowball.
    seller_offers = client.get(f"/listings/{lid}/offers", headers=seller).json()
    assert seller_offers == []


def test_fair_offer_reaches_seller(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _create_listing(client, seller)

    res = client.post(f"/listings/{lid}/offers", json={"amount": 85}, headers=buyer)
    assert res.json()["accepted_for_review"] is True

    seller_offers = client.get(f"/listings/{lid}/offers", headers=seller).json()
    assert len(seller_offers) == 1
    assert seller_offers[0]["status"] == "pending"


def test_knowledge_gateway_blocks_wrong_answer(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    res = client.post(
        "/listings",
        json={
            **LISTING,
            "knowledge_questions": [
                {"prompt": "Wired or wireless?", "options": ["Wired", "Wireless"], "correct_index": 0}
            ],
        },
        headers=seller,
    )
    lid = res.json()["id"]
    qid = res.json()["knowledge_questions"][0]["id"]

    # Wrong answer -> blocked.
    wrong = client.post(
        f"/listings/{lid}/offers",
        json={"amount": 90, "quiz_answers": {str(qid): 1}},
        headers=buyer,
    )
    assert wrong.status_code == 422

    # Correct answer -> passes the gate.
    ok = client.post(
        f"/listings/{lid}/offers",
        json={"amount": 90, "quiz_answers": {str(qid): 0}},
        headers=buyer,
    )
    assert ok.status_code == 201
    assert ok.json()["accepted_for_review"] is True


def test_adab_gate_blocks_low_score_buyer(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _create_listing(client, seller, min_buyer_adab=90)  # baseline buyer has 70
    res = client.post(f"/listings/{lid}/offers", json={"amount": 90}, headers=buyer)
    assert res.status_code == 403


def test_accept_and_complete_rewards_adab(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _create_listing(client, seller)
    client.post(f"/listings/{lid}/offers", json={"amount": 85}, headers=buyer)

    offer = client.get(f"/listings/{lid}/offers", headers=seller).json()[0]
    assert client.post(f"/offers/{offer['id']}/accept", headers=seller).status_code == 200
    completed = client.post(f"/offers/{offer['id']}/complete", headers=seller)
    assert completed.status_code == 200

    buyer_me = client.get("/auth/me", headers=buyer).json()
    assert buyer_me["completed_deals"] == 1
    assert buyer_me["reliability_score"] > 70.0


def test_report_ghost_penalises_buyer(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _create_listing(client, seller)
    client.post(f"/listings/{lid}/offers", json={"amount": 85}, headers=buyer)
    offer = client.get(f"/listings/{lid}/offers", headers=seller).json()[0]
    client.post(f"/offers/{offer['id']}/accept", headers=seller)
    client.post(f"/offers/{offer['id']}/report-ghost", headers=seller)

    buyer_me = client.get("/auth/me", headers=buyer).json()
    assert buyer_me["reliability_score"] < 70.0


def test_specs_guard_ask_gated_by_seller_plan(client, db_session):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _create_listing(client, seller)

    # Basic seller -> Specs Guard disabled, buyer nudged to read the description.
    r = client.post(f"/listings/{lid}/ask", json={"question": "Is it wired?"}, headers=buyer)
    assert r.status_code == 200
    assert r.json()["specs_guard_enabled"] is False

    # Upgrade the seller to Pro -> Specs Guard enabled.
    set_tier(db_session, "seller@example.com", "pro")
    r2 = client.post(f"/listings/{lid}/ask", json={"question": "Is it wired?"}, headers=buyer)
    assert r2.json()["specs_guard_enabled"] is True


def test_basic_tier_cannot_set_custom_floor(client, db_session):
    headers = auth_headers(client, "seller@example.com")
    res = client.post("/listings", json={**LISTING, "floor_percent": 40}, headers=headers)
    assert res.status_code == 402

    set_tier(db_session, "seller@example.com", "pro")
    res = client.post("/listings", json={**LISTING, "floor_percent": 40}, headers=headers)
    assert res.status_code == 201
    assert res.json()["hard_floor_price"] == 60.0


def test_bulk_upload_is_business_only(client, db_session):
    headers = auth_headers(client, "seller@example.com")
    bulk = {"listings": [{**LISTING, "title": f"Bulk item {i}"} for i in range(3)]}

    assert client.post("/listings/bulk", json=bulk, headers=headers).status_code == 402

    set_tier(db_session, "seller@example.com", "business")
    res = client.post("/listings/bulk", json=bulk, headers=headers)
    assert res.status_code == 201
    assert len(res.json()) == 3


def test_cannot_accept_second_offer_while_reserved(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _create_listing(client, seller)
    client.post(f"/listings/{lid}/offers", json={"amount": 85}, headers=buyer)
    client.post(f"/listings/{lid}/offers", json={"amount": 90}, headers=buyer)

    offers = client.get(f"/listings/{lid}/offers", headers=seller).json()
    first, second = offers[0]["id"], offers[1]["id"]

    assert client.post(f"/offers/{first}/accept", headers=seller).status_code == 200
    # Listing is now reserved — a second acceptance must be blocked.
    assert client.post(f"/offers/{second}/accept", headers=seller).status_code == 409

    # Completing the deal closes out the remaining pending offer.
    client.post(f"/offers/{first}/complete", headers=seller)
    statuses = {o["id"]: o["status"] for o in client.get(f"/listings/{lid}/offers", headers=seller).json()}
    assert statuses[second] == "declined"


def test_seller_analytics_gated_and_counts(client, db_session):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")

    # Basic tier: analytics is paywalled.
    assert client.get("/analytics/seller", headers=seller).status_code == 402

    set_tier(db_session, "seller@example.com", "pro")
    # Pro sellers get auto-generated quiz questions; disable so the buyer's
    # bare offers pass the gateway and reach the anti-lowball engine.
    lid = _create_listing(client, seller, auto_generate_questions=False)
    client.post(f"/listings/{lid}/offers", json={"amount": 25}, headers=buyer)  # lowball
    client.post(f"/listings/{lid}/offers", json={"amount": 90}, headers=buyer)  # fair

    stats = client.get("/analytics/seller", headers=seller).json()
    assert stats["active_listings"] == 1
    assert stats["lowballs_blocked"] == 1
    assert stats["pending_offers"] == 1
    assert stats["avg_offer_percent_of_list"] == 90.0


def test_login_rate_limited(client):
    client.post(
        "/auth/register",
        json={"email": "brute@example.com", "password": "password123", "display_name": "brute"},
    )
    # 10 attempts per minute are allowed; the 11th gets 429.
    for _ in range(10):
        res = client.post("/auth/login", data={"username": "brute@example.com", "password": "wrong"})
        assert res.status_code == 401
    res = client.post("/auth/login", data={"username": "brute@example.com", "password": "wrong"})
    assert res.status_code == 429


def test_subscription_upgrade_is_billing_gated(client, db_session):
    """Upgrading to a paid tier stages a pending request; it only activates
    after the user pays and an admin verifies."""
    headers = auth_headers(client, "seller@example.com")
    assert client.get("/subscription", headers=headers).json()["tier"] == "basic"

    # Requesting Pro does NOT flip the tier yet.
    res = client.post("/subscription/upgrade", json={"tier": "pro"}, headers=headers)
    body = res.json()
    assert body["tier"] == "basic"
    assert body["pending_tier"] == "pro"
    assert body["amount_due"] == 15.0

    # User marks payment sent -> pending.
    marked = client.post(
        "/subscription/payment/mark-sent", json={"reference": "BIBD sub 22"}, headers=headers
    )
    assert marked.json()["payment_status"] == "pending"

    # A non-admin cannot activate.
    from app.models.user import User

    seller_id = db_session.query(User).filter_by(email="seller@example.com").one().id
    assert client.post(f"/subscription/{seller_id}/activate", headers=headers).status_code == 403

    # Promote an admin and activate.
    admin = auth_headers(client, "admin@example.com")
    admin_user = db_session.query(User).filter_by(email="admin@example.com").one()
    admin_user.is_admin = True
    db_session.commit()

    activated = client.post(f"/subscription/{seller_id}/activate", headers=admin)
    assert activated.status_code == 200
    body = activated.json()
    assert body["tier"] == "pro"
    assert body["pending_tier"] is None
    assert body["has_specs_guard"] is True

    # Downgrade to Basic is immediate (no billing).
    down = client.post("/subscription/upgrade", json={"tier": "basic"}, headers=headers)
    assert down.json()["tier"] == "basic"
