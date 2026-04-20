from __future__ import annotations

from backend.models import SafetyClassification


ADVICE_TERMS = (
    "should i buy",
    "should i sell",
    "should i hold",
    "would you buy",
    "would you sell",
    "would you hold",
    "is this a buy",
    "is this a sell",
    "is this a hold",
    "buy or sell",
    "do i buy",
    "do i sell",
    "how much",
    "what percent",
    "what percentage",
    "allocate",
    "allocation",
    "position size",
    "shares should i",
    "price target",
    "target price",
    "guaranteed",
    "will it go up",
    "will definitely",
    "future returns",
    "can't lose",
    "outperform next year",
    "my portfolio",
    "for my taxes",
    "tax advice",
    "tax-loss",
    "capital gains",
    "taxes",
    "brokerage",
    "place a trade",
    "execute a trade",
    "market order",
    "limit order",
    "trade it",
)

FORBIDDEN_OUTPUT_PHRASES = (
    "you should buy",
    "you should sell",
    "you should hold",
    "buy now",
    "sell now",
    "hold this",
    "definitely buy",
    "definitely sell",
    "put 50%",
    "allocate 20%",
    "you should invest",
    "price target is",
    "guaranteed return",
    "will definitely go up",
    "will definitely outperform",
    "can't lose money",
    "place a trade",
    "execute a trade",
    "open a brokerage account",
    "for your taxes, you should",
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


def find_forbidden_output_phrases(text: str) -> list[str]:
    normalized = " ".join(text.lower().split())
    return [phrase for phrase in FORBIDDEN_OUTPUT_PHRASES if phrase in normalized]
