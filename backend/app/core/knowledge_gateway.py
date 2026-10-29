"""Product Knowledge Gateway.

Buyers must answer a listing's fact-check questions before they can chat or
make an offer, proving they read the description (no more "is it wired?" on a
wired keyboard).
"""
from dataclasses import dataclass

from app.models.listing import Listing


@dataclass(frozen=True)
class QuizResult:
    passed: bool
    total: int
    correct: int


def grade_quiz(listing: Listing, answers: dict[int, int]) -> QuizResult:
    """Grade buyer ``answers`` (question_id -> chosen option index).

    A listing with no questions is treated as passed. All questions must be
    answered correctly to pass.
    """
    questions = listing.knowledge_questions
    if not questions:
        return QuizResult(passed=True, total=0, correct=0)

    correct = 0
    for q in questions:
        chosen = answers.get(q.id)
        if chosen is not None and chosen == q.correct_index:
            correct += 1

    return QuizResult(passed=correct == len(questions), total=len(questions), correct=correct)
