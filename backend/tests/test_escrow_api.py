"""End-to-end tests for the manual 'Funds Verified' escrow flow."""
from tests.conftest import auth_headers

LISTING = {
    "title": "Mechanical keyboard",
    "description": "A wired mechanical keyboard, barely used, no box.",
    "list_price": 100,
    "floor_percent": 20,
}


def _accepted_offer(client, seller, buyer, amount=90) -> int:
    """Create a listing, make a fair offer, and have the seller accept it."""
    lid = client.post("/listings", json=LISTING, headers=seller).json()["id"]
    client.post(f"/listings/{lid}/offers", json={"amount": amount}, headers=buyer)
    offer = client.get(f"/listings/{lid}/offers", headers=seller).json()[0]
    assert client.post(f"/offers/{offer['id']}/accept", headers=seller).status_code == 200
    return offer["id"]


def test_buyer_sees_own_offers_but_not_lowballs(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = client.post("/listings", json=LISTING, headers=seller).json()["id"]
    client.post(f"/listings/{lid}/offers", json={"amount": 20}, headers=buyer)  # lowball
    client.post(f"/listings/{lid}/offers", json={"amount": 90}, headers=buyer)  # fair

    mine = client.get("/offers/mine", headers=buyer).json()
    # The silently-rejected lowball is hidden even from the buyer's own history.
    assert len(mine) == 1
    assert float(mine[0]["amount"]) == 90.0


def test_full_escrow_happy_path(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    oid = _accepted_offer(client, seller, buyer)

    # Buyer marks funds sent with a reference.
    marked = client.post(
        f"/offers/{oid}/payment/mark-sent",
        json={"reference": "BIBD txn 4471"},
        headers=buyer,
    )
    assert marked.status_code == 200
    assert marked.json()["payment_status"] == "pending"
    assert marked.json()["payment_reference"] == "BIBD txn 4471"

    # Seller verifies receipt -> Funds Verified.
    verified = client.post(f"/offers/{oid}/payment/verify", headers=seller)
    assert verified.status_code == 200
    assert verified.json()["payment_status"] == "verified"

    # Completing the deal releases the funds.
    completed = client.post(f"/offers/{oid}/complete", headers=seller)
    assert completed.json()["payment_status"] == "released"


def test_cannot_verify_before_buyer_marks_sent(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    oid = _accepted_offer(client, seller, buyer)

    res = client.post(f"/offers/{oid}/payment/verify", headers=seller)
    assert res.status_code == 409


def test_only_buyer_marks_and_only_seller_verifies(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    oid = _accepted_offer(client, seller, buyer)

    # Seller can't mark funds on the buyer's behalf.
    assert client.post(f"/offers/{oid}/payment/mark-sent", json={}, headers=seller).status_code == 403

    client.post(f"/offers/{oid}/payment/mark-sent", json={}, headers=buyer)
    # Buyer can't verify their own payment.
    assert client.post(f"/offers/{oid}/payment/verify", headers=buyer).status_code == 403


def test_mark_sent_requires_accepted_deal(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = client.post("/listings", json=LISTING, headers=seller).json()["id"]
    client.post(f"/listings/{lid}/offers", json={"amount": 90}, headers=buyer)
    oid = client.get(f"/listings/{lid}/offers", headers=seller).json()[0]["id"]

    # Still PENDING (not accepted) -> can't pay yet.
    assert client.post(f"/offers/{oid}/payment/mark-sent", json={}, headers=buyer).status_code == 409


def test_registration_cannot_grant_admin(client, db_session):
    # Passing is_admin in the register payload must be ignored, not honored.
    auth_headers(client, "sneaky@example.com", is_admin=True)
    from app.models.user import User

    user = db_session.query(User).filter_by(email="sneaky@example.com").one()
    assert user.is_admin is False


def test_admin_can_verify_any_deal(client, db_session):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    auth_headers(client, "admin@example.com")
    oid = _accepted_offer(client, seller, buyer)
    client.post(f"/offers/{oid}/payment/mark-sent", json={}, headers=buyer)

    # Promote the admin user directly (the API never grants this).
    from app.models.user import User

    admin_user = db_session.query(User).filter_by(email="admin@example.com").one()
    admin_user.is_admin = True
    db_session.commit()
    admin = {"Authorization": _login(client, "admin@example.com")}

    res = client.post(f"/offers/{oid}/payment/verify", headers=admin)
    assert res.status_code == 200
    assert res.json()["payment_status"] == "verified"


def _login(client, email: str) -> str:
    res = client.post("/auth/login", data={"username": email, "password": "password123"})
    return f"Bearer {res.json()['access_token']}"


def test_report_ghost_refunds_marked_payment(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    oid = _accepted_offer(client, seller, buyer)
    client.post(f"/offers/{oid}/payment/mark-sent", json={}, headers=buyer)

    ghosted = client.post(f"/offers/{oid}/report-ghost", headers=seller)
    assert ghosted.status_code == 200
    assert ghosted.json()["payment_status"] == "refunded"
