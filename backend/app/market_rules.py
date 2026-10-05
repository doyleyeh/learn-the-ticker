"""Private numeric-review rules; never permissions for generic text admission."""
from datetime import date, timedelta
from backend.app.contracts import SourcePolicy
from backend.app.source_registry import SourceRule, source_rule

PRIVATE_MARKET_RULES = (
    SourceRule("private-yahoo-valuations-v1", "finance.yahoo.com", r"/quote/[A-Z0-9][A-Z0-9.-]{0,29}/key-statistics/",
        "Yahoo Finance via yfinance — private provider valuations", SourcePolicy.metadata, False,
        date(2026, 10, 5), "https://help.yahoo.com/kb/account/SLN2310.html", timedelta(days=1)),
    SourceRule("private-yahoo-history-v1", "finance.yahoo.com", r"/quote/[A-Z0-9][A-Z0-9.-]{0,29}/history/",
        "Yahoo Finance via yfinance — experimental local-only exception", SourcePolicy.metadata, False,
        date(2026, 10, 4), "https://help.yahoo.com/kb/account/SLN2310.html", timedelta(days=1)),
    SourceRule("private-eodhd-history-v1", "eodhd.com", r"/api/eod/[A-Z0-9][A-Z0-9.-]{0,29}\.US",
        "EODHD — bounded private history candidate", SourcePolicy.metadata, False,
        date(2026, 10, 4), "https://eodhd.com/financial-apis/terms-conditions", timedelta(days=1)),
)


def private_market_rule(url):
    return source_rule(url, PRIVATE_MARKET_RULES)
