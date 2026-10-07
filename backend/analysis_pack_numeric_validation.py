from __future__ import annotations

import re
from typing import Any

from backend.models import AnalysisPackImportBundle


_EXPLICIT_VALUE_MARKERS = (" is ", " at ", " equals ", " value ", " level ", " yield ", ":", "=")
_PRICE_WORDS = ("price", "close", "closing", "level", "trading at", "traded at")
_TECHNICAL_NON_PRICE_WORDS = ("adx", "dmi", "volume", "volume change")
_NUMERIC_TOKEN = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:,\d{3})*(?:\.\d+)?%?")


def validate_analysis_pack_numeric_integrity(bundle: AnalysisPackImportBundle) -> list[str]:
    context = bundle.validation_metadata.get("ai_context_artifact")
    if not isinstance(context, dict):
        return ["ai_context_missing_for_numeric_validation"]
    allowed_facts = [
        fact for fact in context.get("allowed_numeric_facts", [])
        if isinstance(fact, dict) and isinstance(fact.get("value"), (int, float))
    ]
    return validate_generated_numeric_integrity(_analysis_texts(bundle), allowed_facts)


def validate_generated_numeric_integrity(texts: list[str], allowed_facts: list[dict[str, Any]]) -> list[str]:
    reason_codes: list[str] = []
    for text in texts:
        lowered = text.lower()
        if _technical_field_misuse(lowered):
            reason_codes.append("technical_indicator_field_misused_as_price")
        reason_codes.extend(_validate_text_numbers(text, allowed_facts))
    return list(dict.fromkeys(reason_codes))


def _analysis_texts(bundle: AnalysisPackImportBundle) -> list[str]:
    texts: list[str] = []
    if bundle.market_context_pack is not None:
        for section in bundle.market_context_pack.market_ai_comprehensive_analysis.sections:
            texts.append(section.analysis)
            texts.extend(section.bullets)
    for pack in bundle.ticker_packs.values():
        for section in pack.ai_comprehensive_analysis.sections:
            texts.append(section.analysis)
            texts.extend(section.bullets)
    return [text for text in texts if text]


def _technical_field_misuse(lowered: str) -> bool:
    for sentence in _sentences(lowered):
        if any(word in sentence for word in _TECHNICAL_NON_PRICE_WORDS) and any(word in sentence for word in _PRICE_WORDS):
            return True
    return False


def _validate_text_numbers(text: str, allowed_facts: list[dict[str, Any]]) -> list[str]:
    reason_codes: list[str] = []
    for sentence in _sentences(text):
        lowered = sentence.lower()
        sentence_facts = [
            fact for fact in allowed_facts
            if any(alias and alias.lower() in lowered for alias in fact.get("aliases", []))
        ]
        if not sentence_facts or not _looks_like_explicit_numeric_claim(lowered):
            continue
        for token, start, end in _numeric_tokens(sentence):
            if _ignore_numeric_token(sentence, token, start, end):
                continue
            value = _coerce_number(token)
            if value is None:
                continue
            if not any(_matches_fact(value, fact) for fact in sentence_facts):
                reason_codes.append("unsupported_or_deviating_numeric_claim")
                break
    return reason_codes


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def _looks_like_explicit_numeric_claim(sentence: str) -> bool:
    return any(marker in sentence for marker in _EXPLICIT_VALUE_MARKERS)


def _numeric_tokens(sentence: str) -> list[tuple[str, int, int]]:
    return [(match.group(0), match.start(), match.end()) for match in _NUMERIC_TOKEN.finditer(sentence)]


def _ignore_numeric_token(sentence: str, token: str, start: int, end: int) -> bool:
    clean = token.replace(",", "").rstrip("%")
    if clean.isdigit() and 1900 <= int(clean) <= 2100:
        return True
    before = sentence[max(0, start - 2):start]
    after = sentence[end:end + 18].lower()
    if "-" in before or after.startswith(("-year", "-month", "-day")):
        return True
    if any(after.startswith(suffix) for suffix in (" bps", " basis point", " day", " days", " item", " items", " week", " weeks")):
        return True
    return False


def _coerce_number(token: str) -> float | None:
    try:
        return float(token.replace(",", "").rstrip("%"))
    except ValueError:
        return None


def _matches_fact(value: float, fact: dict[str, Any]) -> bool:
    expected = float(fact["value"])
    tolerance = float(fact.get("tolerance_abs") or max(0.02, abs(expected) * 0.02))
    return abs(value - expected) <= tolerance
