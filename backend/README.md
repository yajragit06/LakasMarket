# LakasMarket Backend

FastAPI + SQLAlchemy (PostgreSQL) service implementing LakasMarket's
anti-lowball marketplace logic.

## Layout

```
app/
├── config.py            # env-driven settings
├── database.py          # engine, session, declarative Base
├── models/              # SQLAlchemy ORM models
│   ├── enums.py         # District, SaleMode, OfferStatus, AdabEventType, ...
│   ├── user.py          # User + dual Adab reputation
│   ├── listing.py       # Listing (Hard Floor, sale mode) + KnowledgeQuestion
│   ├── offer.py         # Offer (silent auto-rejection)
│   └── subscription.py  # SaaS tiers + limits
├── core/                # Domain engines (pure logic where possible)
│   ├── anti_lowball.py  # Hard Floor + Take Tonight evaluation
│   ├── knowledge_gateway.py  # quiz grading
│   ├── adab.py          # reputation adjustments
│   ├── logistics.py     # distance-fair delivery fees
│   ├── specs_guard.py   # LLM question generation / Q&A
│   └── security.py      # password hashing + JWT
├── schemas/             # Pydantic request/response models
├── api/                 # routers + dependencies
└── main.py              # app factory
```

## Running

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # set DATABASE_URL / SECRET_KEY / OPENAI_API_KEY
uvicorn app.main:app --reload
```

In `development`, tables are auto-created on startup. For production, generate
Alembic migrations against `Base.metadata` instead.

## Key endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register` | – | Create account (starts on Basic tier) |
| POST | `/auth/login` | – | OAuth2 password → JWT |
| GET | `/auth/me` | ✅ | Current user + Adab score |
| POST | `/listings` | ✅ | Secure listing creation (tier-limited) |
| GET | `/listings` | – | Browse active listings |
| GET | `/listings/{id}` | – | Listing detail (quiz prompts, no answers) |
| GET | `/listings/mine` | ✅ | The seller's own listings (any status) |
| POST | `/listings/{id}/ask` | ✅ | Ask the AI Specs Guard (only answers if the seller's plan includes it) |
| POST | `/listings/{id}/offers` | ✅ | Make an offer — runs Adab gate, Knowledge Gateway, logistics, and Anti-Lowball engine |
| GET | `/listings/{id}/offers` | ✅ (seller) | Seller's offers (auto-rejected lowballs hidden) |
| POST | `/offers/{id}/accept` | ✅ (seller) | Accept an offer → listing reserved |
| POST | `/offers/{id}/decline` | ✅ (seller) | Decline an offer |
| POST | `/offers/{id}/complete` | ✅ (seller) | Mark sold → rewards both parties' Adab |
| POST | `/offers/{id}/report-ghost` | ✅ (seller) | Penalise a ghosting buyer's Adab |
| POST | `/listings/bulk` | ✅ (Business) | Create up to 50 listings in one call |
| GET | `/analytics/seller` | ✅ (Pro+) | Protection & sales stats (lowballs blocked, offer strength, ghosting) |
| POST | `/listings/{id}/conversations` | ✅ | Start a chat — gated by the quiz + min-Adab, idempotent per buyer |
| GET | `/conversations` | ✅ | The user's inbox (as buyer or seller) |
| GET | `/conversations/{id}` | ✅ (participant) | Thread + messages; marks the other party's messages read |
| POST | `/conversations/{id}/messages` | ✅ (participant) | Send a message; a buyer reply re-opens a ghosted thread |
| POST | `/conversations/{id}/report-ghost` | ✅ (seller) | Penalise a buyer who went silent after the seller replied |
| POST | `/conversations/{id}/negotiate` | ✅ (buyer) | Propose a price; the seller's AI bot auto-counters in-thread (Pro, bot enabled) |
| GET | `/offers/mine` | ✅ (buyer) | The buyer's own offers (silently-rejected lowballs omitted) |
| POST | `/offers/{id}/payment/mark-sent` | ✅ (buyer) | Record funds sent on an accepted deal → escrow PENDING |
| POST | `/offers/{id}/payment/verify` | ✅ (seller/admin) | Confirm funds received → "Funds Verified" |

Manual "Funds Verified" escrow: no PSP holds money; the platform records a
verification state (`none → pending → verified → released`, or `refunded` if a
deal falls through). A real payment provider can later drive the same
transitions from a webhook. Completing a verified deal releases it; reporting a
ghost on a paid deal refunds it.
| GET | `/subscription` | ✅ | Current plan, limits, Specs Guard access |
| POST | `/subscription/upgrade` | ✅ | Downgrade to Basic (immediate) or request a paid upgrade (staged) |
| POST | `/subscription/payment/mark-sent` | ✅ | User records payment for a pending upgrade |
| POST | `/subscription/{user_id}/activate` | ✅ (admin) | Verify payment & activate the pending upgrade |

Billing gate (manual): paid upgrades don't flip the plan until verified —
`upgrade` stages a `pending_tier`, the user marks payment sent, and an admin
activates it (the single choke point a real PSP webhook would call). Downgrades
to Basic are free and immediate. Monthly prices: Pro B$15, Business B$49.

Tier rules enforced at the API: Basic is capped at 5 active listings and the
standard 20% floor; custom floors are Pro+; bulk upload is Business-only.
Pending "take tonight" offers lapse to `expired` after 24h (lazy, on seller
reads/actions).

## Demo data

Seed two demo users (a Pro seller in Bandar, a Basic buyer in Seria), a wired
keyboard listing with a knowledge question, and two offers (a hidden lowball and
a fair offer with an auto-computed Seria delivery fee):

```bash
python scripts/seed.py    # idempotent; login password is "password123"
```

## Migrations

```bash
alembic upgrade head        # apply
alembic downgrade base      # roll back
alembic revision --autogenerate -m "message"   # new migration vs models
```

## Tests

```bash
pytest
```

Covers the Anti-Lowball floor/speed logic, logistics fees, and Adab scoring
(unit tests), plus end-to-end API flows (auth, listing creation + tier limits,
the offer pipeline, seller actions, and subscription upgrades) via `TestClient`
against an in-memory SQLite database — no PostgreSQL needed to run the suite.
