"""LakasMarket FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, auth, conversations, listings, offers, subscriptions
from app.config import settings
from app.database import Base, engine

# Importing app.models via the routers registers all tables on Base.metadata.
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For development convenience only. Production should use Alembic migrations.
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="LakasMarket API",
    version="0.1.0",
    description="Anti-lowball marketplace platform for Brunei.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(offers.router)
app.include_router(subscriptions.router)
app.include_router(analytics.router)
app.include_router(conversations.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "lakasmarket"}
