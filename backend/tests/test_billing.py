"""Focused tests for the subscription billing gate."""
from tests.conftest import auth_headers

CUSTOM_FLOOR_LISTING = {
    "title": "Mechanical keyboard",
    "description": "A wired mechanical keyboard, barely used, no box.",
    "list_price": 100,
    "floor_percent": 40,
}


def _promote_admin(client, db_session, email="admin@example.com"):
    from app.models.user import User

    headers = auth_headers(client, email)
    user = db_session.query(User).filter_by(email=email).one()
    user.is_admin = True
    db_session.commit()
    return headers


def _user_id(db_session, email):
    from app.models.user import User

    return db_session.query(User).filter_by(email=email).one().id


def test_paid_features_locked_until_activation(client, db_session):
    """A merely-requested upgrade grants nothing until it's activated."""
    seller = auth_headers(client, "seller@example.com")
    client.post("/subscription/upgrade", json={"tier": "pro"}, headers=seller)
    client.post("/subscription/payment/mark-sent", json={}, headers=seller)

    # Still Basic -> custom floor still refused.
    res = client.post("/listings", json=CUSTOM_FLOOR_LISTING, headers=seller)
    assert res.status_code == 402

    admin = _promote_admin(client, db_session)
    client.post(f"/subscription/{_user_id(db_session, 'seller@example.com')}/activate", headers=admin)

    # Now Pro -> custom floor allowed.
    res = client.post("/listings", json=CUSTOM_FLOOR_LISTING, headers=seller)
    assert res.status_code == 201


def test_cannot_activate_before_payment_marked(client, db_session):
    seller = auth_headers(client, "seller@example.com")
    client.post("/subscription/upgrade", json={"tier": "pro"}, headers=seller)  # no mark-sent
    admin = _promote_admin(client, db_session)

    res = client.post(
        f"/subscription/{_user_id(db_session, 'seller@example.com')}/activate", headers=admin
    )
    assert res.status_code == 409


def test_mark_sent_requires_pending_upgrade(client):
    seller = auth_headers(client, "seller@example.com")
    # No pending upgrade -> nothing to pay for.
    assert client.post("/subscription/payment/mark-sent", json={}, headers=seller).status_code == 409


def test_activate_requires_admin_and_existing_pending(client, db_session):
    seller = auth_headers(client, "seller@example.com")
    admin = _promote_admin(client, db_session)
    # No pending upgrade for this user -> 409 even for an admin.
    res = client.post(
        f"/subscription/{_user_id(db_session, 'seller@example.com')}/activate", headers=admin
    )
    assert res.status_code == 409
