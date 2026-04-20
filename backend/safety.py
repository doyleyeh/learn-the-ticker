from __future__ import annotations

from backend.models import SafetyClassification


ADVICE_TERMS = (
    "should i buy",
    "should i sell",
    "should i hold",
    "do i buy",
    "do i sell",
    "how much",
    "allocate",
    "allocation",
    "price target",
    "guaranteed",
    "will it go up",
    "my portfolio",
    "for my taxes",
    "taxes",
    "brokerage",
    "trade it",
)


def classify_question(question: str, supported: bool) -> SafetyClassification:
    if not supported:
        return SafetyClassification.unsupported_asset_redirect

    normalized = " ".join(question.lower().split())
    if any(term in normalized for term in ADVICE_TERMS):
        return SafetyClassification.personalized_advice_redirect
    return SafetyClassification.educational


def educational_redirect() -> tuple[str, str]:
    return (
        "I can't make a personal investment decision for you or tell you what action to take with this asset. "
        "I can explain what it is, what it owns or does, its main risks, how it compares with similar assets, "
        "and factors beginners often review before making their own decision.",
        "This keeps the answer educational and avoids personal instructions.",
    )
