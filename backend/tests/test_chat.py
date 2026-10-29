"""End-to-end tests for the quiz/Adab-gated chat layer."""
from tests.conftest import auth_headers, set_tier

LISTING = {
    "title": "Mechanical keyboard",
    "description": "A wired mechanical keyboard, barely used, no box.",
    "list_price": 100,
    "floor_percent": 20,
}


def _listing(client, headers, **overrides) -> dict:
    res = client.post("/listings", json={**LISTING, **overrides}, headers=headers)
    assert res.status_code == 201
    return res.json()


def test_start_conversation_and_exchange_messages(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _listing(client, seller)["id"]

    started = client.post(
        f"/listings/{lid}/conversations",
        json={"opening_message": "Still available?"},
        headers=buyer,
    )
    assert started.status_code == 200
    conv = started.json()
    assert conv["status"] == "open"
    assert len(conv["messages"]) == 1

    # Seller replies.
    reply = client.post(
        f"/conversations/{conv['id']}/messages",
        json={"body": "Yes — wired only, no box."},
        headers=seller,
    )
    assert reply.status_code == 200

    # Buyer sees both messages; the seller's is now marked read on fetch.
    detail = client.get(f"/conversations/{conv['id']}", headers=buyer).json()
    assert len(detail["messages"]) == 2
    seller_msg = [m for m in detail["messages"] if m["sender_id"] != conv["buyer_id"]][0]
    assert seller_msg["read_at"] is not None


def test_conversation_is_idempotent_per_buyer(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _listing(client, seller)["id"]

    a = client.post(f"/listings/{lid}/conversations", json={}, headers=buyer).json()
    b = client.post(f"/listings/{lid}/conversations", json={}, headers=buyer).json()
    assert a["id"] == b["id"]


def test_cannot_message_own_listing(client):
    seller = auth_headers(client, "seller@example.com")
    lid = _listing(client, seller)["id"]
    res = client.post(f"/listings/{lid}/conversations", json={}, headers=seller)
    assert res.status_code == 400


def test_knowledge_gate_blocks_starting_chat(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    res = client.post(
        "/listings",
        json={
            **LISTING,
            "knowledge_questions": [
                {"prompt": "Wired?", "options": ["Wired", "Wireless"], "correct_index": 0}
            ],
        },
        headers=seller,
    )
    lid, qid = res.json()["id"], res.json()["knowledge_questions"][0]["id"]

    blocked = client.post(
        f"/listings/{lid}/conversations",
        json={"quiz_answers": {str(qid): 1}},
        headers=buyer,
    )
    assert blocked.status_code == 422

    ok = client.post(
        f"/listings/{lid}/conversations",
        json={"quiz_answers": {str(qid): 0}},
        headers=buyer,
    )
    assert ok.status_code == 200


def test_non_participant_cannot_read(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    stranger = auth_headers(client, "stranger@example.com")
    lid = _listing(client, seller)["id"]
    conv = client.post(f"/listings/{lid}/conversations", json={}, headers=buyer).json()

    assert client.get(f"/conversations/{conv['id']}", headers=stranger).status_code == 403


def test_report_ghost_requires_seller_reply_then_penalises(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _listing(client, seller)["id"]
    conv = client.post(
        f"/listings/{lid}/conversations",
        json={"opening_message": "hi"},
        headers=buyer,
    ).json()
    cid = conv["id"]

    # Buyer's message is last -> seller can't yet claim ghosting.
    assert client.post(f"/conversations/{cid}/report-ghost", headers=seller).status_code == 409

    # Seller replies; now the buyer is silent -> ghosting is reportable.
    client.post(f"/conversations/{cid}/messages", json={"body": "yes?"}, headers=seller)
    ghost = client.post(f"/conversations/{cid}/report-ghost", headers=seller)
    assert ghost.status_code == 200
    assert ghost.json()["status"] == "ghosted"

    buyer_me = client.get("/auth/me", headers=buyer).json()
    assert buyer_me["reliability_score"] < 70.0


def test_negotiation_bot_counters_in_thread(client, db_session):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    # Enabling the bot requires Pro.
    assert (
        client.post("/listings", json={**LISTING, "negotiation_enabled": True}, headers=seller).status_code
        == 402
    )
    set_tier(db_session, "seller@example.com", "pro")
    lid = _listing(client, seller, negotiation_enabled=True, auto_generate_questions=False)["id"]
    cid = client.post(
        f"/listings/{lid}/conversations", json={"opening_message": "hi"}, headers=buyer
    ).json()["id"]

    # Buyer proposes a lowball; bot counters above the (hidden) floor, in-thread.
    res = client.post(f"/conversations/{cid}/negotiate", json={"proposed_price": 40}, headers=buyer)
    assert res.status_code == 200
    body = res.json()
    assert body["action"] == "counter"
    assert float(body["counter_price"]) == 90.0
    assert "🤖" in body["message"]["body"]
    assert body["message"]["sender_id"] != buyer  # posted as the seller/bot

    # Buyer meeting the ask is accepted.
    ok = client.post(f"/conversations/{cid}/negotiate", json={"proposed_price": 100}, headers=buyer)
    assert ok.json()["action"] == "accept"


def test_negotiate_blocked_when_bot_disabled(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _listing(client, seller)["id"]  # negotiation not enabled
    cid = client.post(f"/listings/{lid}/conversations", json={}, headers=buyer).json()["id"]
    res = client.post(f"/conversations/{cid}/negotiate", json={"proposed_price": 50}, headers=buyer)
    assert res.status_code == 409


def test_seller_cannot_negotiate_against_self(client, db_session):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    set_tier(db_session, "seller@example.com", "pro")
    lid = _listing(client, seller, negotiation_enabled=True, auto_generate_questions=False)["id"]
    cid = client.post(f"/listings/{lid}/conversations", json={}, headers=buyer).json()["id"]
    # The seller is a participant but only the buyer may propose a price.
    assert (
        client.post(f"/conversations/{cid}/negotiate", json={"proposed_price": 90}, headers=seller).status_code
        == 403
    )


def test_buyer_reply_reopens_ghosted_conversation(client):
    seller = auth_headers(client, "seller@example.com")
    buyer = auth_headers(client, "buyer@example.com")
    lid = _listing(client, seller)["id"]
    cid = client.post(
        f"/listings/{lid}/conversations", json={"opening_message": "hi"}, headers=buyer
    ).json()["id"]
    client.post(f"/conversations/{cid}/messages", json={"body": "yes?"}, headers=seller)
    client.post(f"/conversations/{cid}/report-ghost", headers=seller)

    # Buyer comes back -> conversation re-opens.
    client.post(f"/conversations/{cid}/messages", json={"body": "sorry, still keen"}, headers=buyer)
    detail = client.get(f"/conversations/{cid}", headers=buyer).json()
    assert detail["status"] == "open"
