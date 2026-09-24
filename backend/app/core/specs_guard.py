"""AI Specs Guard.

Uses an OpenAI-compatible LLM to (a) auto-generate Product Knowledge Gateway
questions from a listing description, and (b) answer buyer questions like
"with box?" / "wired or wireless?" strictly from the listing content.

This module degrades gracefully: if no API key is configured it falls back to
a lightweight heuristic so the platform still runs in development.
"""
from __future__ import annotations

import json

import httpx

from app.config import settings

_SYSTEM_GEN = (
    "You are the Specs Guard for a Brunei marketplace. Given a product listing, "
    "write up to {n} short multiple-choice fact-check questions that a buyer could "
    "only answer by actually reading the description (e.g. wired vs wireless, with/without "
    "box, storage size). Respond ONLY with JSON: a list of objects with keys "
    '"prompt", "options" (list of strings), and "correct_index" (int).'
)

_SYSTEM_ANSWER = (
    "You are the Specs Guard for a Brunei marketplace. Answer the buyer's question "
    "using ONLY the listing description. If the description does not contain the "
    "answer, reply exactly: 'Not stated in the listing.' Keep answers under 30 words."
)


def _has_llm() -> bool:
    return bool(settings.openai_api_key)


def _chat(system: str, user: str) -> str:
    """Minimal synchronous call to an OpenAI-compatible chat endpoint."""
    resp = httpx.post(
        f"{settings.openai_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate_questions(title: str, description: str, n: int = 2) -> list[dict]:
    """Return up to ``n`` quiz-question dicts for a listing.

    Falls back to a single generic question when no LLM is configured.
    """
    if not _has_llm():
        return [
            {
                "prompt": "Have you read the full description of this item?",
                "options": ["Yes, I've read it", "No, not yet"],
                "correct_index": 0,
            }
        ][:n]

    content = f"Title: {title}\n\nDescription: {description}"
    try:
        raw = _chat(_SYSTEM_GEN.format(n=n), content)
        data = json.loads(raw)
        cleaned: list[dict] = []
        for item in data[:n]:
            if {"prompt", "options", "correct_index"} <= item.keys():
                cleaned.append(
                    {
                        "prompt": str(item["prompt"]),
                        "options": [str(o) for o in item["options"]],
                        "correct_index": int(item["correct_index"]),
                    }
                )
        return cleaned or generate_questions(title, description, n=0)
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError):
        # Never block listing creation on an AI failure.
        return []


def answer_question(description: str, question: str) -> str:
    """Answer a buyer's question from the listing description."""
    if not _has_llm():
        return "Specs Guard is available on Pro. Please read the description."
    try:
        return _chat(_SYSTEM_ANSWER, f"Listing: {description}\n\nQuestion: {question}").strip()
    except httpx.HTTPError:
        return "Not stated in the listing."
