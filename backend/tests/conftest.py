"""Shared test fixtures.

API tests run the real FastAPI app against an in-memory SQLite database via a
dependency override, so no PostgreSQL instance is required in CI.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.rate_limit import RateLimiter
from app.database import Base, get_db
from app.main import app

# Skip the dev-only create_all in the app lifespan (it targets Postgres).
settings.environment = "test"


@pytest.fixture
def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def _session_factory(_engine):
    return sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def client(_session_factory):
    def override_get_db():
        db = _session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Limiters key on client IP; every TestClient shares one, so clear between tests.
    RateLimiter.reset_all()
    # No context manager -> lifespan events don't fire (we don't want them here).
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def db_session(_session_factory):
    """A direct DB session sharing the client's database — for test-only setup
    the API deliberately forbids, e.g. promoting a user to admin."""
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()


def set_tier(db_session, email: str, tier: str) -> None:
    """Test-only shortcut to put a user on a paid tier, bypassing the billing
    gate. Feature tests that merely need a tier use this; the billing flow has
    its own dedicated tests."""
    from app.models.enums import PaymentStatus, SubscriptionTier
    from app.models.subscription import Subscription
    from app.models.user import User

    user = db_session.query(User).filter_by(email=email).one()
    sub = user.subscription
    if sub is None:
        sub = Subscription(user_id=user.id)
        db_session.add(sub)
    sub.tier = SubscriptionTier(tier)
    sub.pending_tier = None
    sub.payment_status = PaymentStatus.NONE
    db_session.commit()


def auth_headers(client: TestClient, email: str, password: str = "password123", **kw) -> dict:
    """Register (idempotently) + log in, returning an Authorization header."""
    client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0], **kw},
    )
    res = client.post("/auth/login", data={"username": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
