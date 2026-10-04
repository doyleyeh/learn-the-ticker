"""Ratios of exact, same-filing issuer observations; no market/share-basis inference."""
from fractions import Fraction

from backend.app.contracts import FinancialRatio

METHOD = "sec-net-income-revenue-v1"
DESCRIPTION = ("Application calculation: net income / revenue × 100; exact same issuer, filing, "
               "currency and reporting interval. Each revenue concept stays separate. "
               "Rounded to six decimal percentage places, ties to even; not a forecast or valuation.")
REVENUE_CONCEPTS = ("us-gaap:Revenues", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax")
INCOME_CONCEPT = "us-gaap:NetIncomeLoss"


def income_percent(income, revenue):
    ratio = Fraction(income) / Fraction(revenue) * 100_000_000
    quotient, remainder = divmod(abs(ratio.numerator), ratio.denominator)
    if remainder * 2 > ratio.denominator or (remainder * 2 == ratio.denominator and quotient % 2):
        quotient += 1
    whole, decimals = divmod(quotient, 1_000_000)
    value = str(whole) + ("." + f"{decimals:06d}".rstrip("0") if decimals else "")
    return ("-" if ratio < 0 and quotient else "") + value


def ratios_for_financials(data):
    """Inputs must pass the issuer observation validator before publication."""
    result = []
    for concept in REVENUE_CONCEPTS:
        revenues = [row for row in data.observations if row.concept == concept]
        for period, limit in (("annual", 5), ("quarter", 12)):
            dates = sorted({(row.start, row.end) for row in revenues if row.period == period})[-limit:]
            for start, end in dates:
                relevant = [row for row in data.observations if row.start == start and row.end == end
                            and row.period == period and row.concept in (concept, INCOME_CONCEPT)
                            and row.revision != "superseded"]
                numerator = [row for row in relevant if row.concept == INCOME_CONCEPT]
                denominator = [row for row in relevant if row.concept == concept]
                reason = ("missing_income" if not numerator else
                          "conflicting_inputs" if any(row.revision != "current" for row in relevant) else
                          "ambiguous_inputs" if len(numerator) != 1 or len(denominator) != 1 else None)
                if reason is None:
                    a, b = numerator[0], denominator[0]
                    reason = ("different_units" if a.unit != b.unit else
                              "different_filings" if (a.accession, a.filed) != (b.accession, b.filed) else
                              "nonpositive_revenue" if Fraction(b.value) <= 0 else None)
                result.append(FinancialRatio(denominator_concept=concept, start=start, end=end, period=period,
                    input_ids=sorted(row.id for row in relevant),
                    source_ids=sorted({row.source_id for row in relevant}), reason=reason,
                    percent=income_percent(numerator[0].value, denominator[0].value) if reason is None else None))
    return result
