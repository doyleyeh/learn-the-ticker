"""Code-owned document permissions. A site's reputation is not a usage license."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urlsplit

from backend.app.contracts import SourcePolicy


@dataclass(frozen=True)
class SourceRule:
    id: str
    host: str
    path_pattern: str
    publisher: str
    policy: SourcePolicy
    official: bool
    reviewed_at: date
    rights_url: str
    # Underlying date AND retrieval date must be known and within this bound.
    max_age: timedelta


SEC_RIGHTS = "https://www.sec.gov/about/privacy-information#website-dissemination"
SOURCE_RULES = (
    SourceRule("openfigi-v3", "api.openfigi.com", r"/v3/(?:mapping|search)",
               "OpenFIGI / Bloomberg Finance L.P.", SourcePolicy.metadata, False,
               date(2026, 10, 4), "https://www.openfigi.com/docs/terms-of-service", timedelta(days=1)),
    SourceRule("sec-filings-v1", "www.sec.gov", r"/Archives/edgar/data/[0-9]+/[0-9]{18}/[A-Za-z0-9_.-]+\.(?:htm|html|txt)",
               "U.S. Securities and Exchange Commission", SourcePolicy.full_text, True,
               date(2026, 10, 4), SEC_RIGHTS, timedelta(days=1)),
    SourceRule("sec-listings-v1", "www.sec.gov", r"/files/company_tickers_exchange\.json",
               "U.S. Securities and Exchange Commission", SourcePolicy.full_text, True,
               date(2026, 10, 4), SEC_RIGHTS, timedelta(days=1)),
    SourceRule("sec-submissions-v1", "data.sec.gov", r"/submissions/CIK[0-9]{10}\.json",
               "U.S. Securities and Exchange Commission", SourcePolicy.full_text, True,
               date(2026, 10, 4), SEC_RIGHTS, timedelta(days=1)),
)


def source_rule(url: str, rules=SOURCE_RULES) -> SourceRule | None:
    """Match canonical public document paths only; overlapping rules fail closed."""
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.port not in (None, 443) or parsed.query or parsed.fragment
                or "%" in parsed.path or "\\" in parsed.path
                or any(part in (".", "..") for part in parsed.path.split("/"))):
            return None
        matches = [rule for rule in rules if parsed.hostname == rule.host and re.fullmatch(rule.path_pattern, parsed.path)]
        return matches[0] if len(matches) == 1 else None
    except ValueError:
        return None
