from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote


ETF_ISSUER_SOURCE_PACK_SCHEMA_VERSION = "etf-issuer-source-pack-v1"
ETF_ISSUER_SOURCE_PACK_POLICY_VERSION = "automated-official-source-pack-policy-v1"

ETF_ISSUER_SOURCE_TYPES = (
    "product_page",
    "fact_sheet",
    "holdings",
    "exposures",
    "prospectus",
    "shareholder_report",
    "methodology",
    "issuer_announcements",
)

UNSUPPORTED_ETF_SOURCE_PACK_MARKERS = (
    "active",
    "buffer",
    "commodity",
    "crypto",
    "covered call",
    "daily inverse",
    "etn",
    "fixed income",
    "inverse",
    "leveraged",
    "option income",
    "single stock",
)


@dataclass(frozen=True)
class ETFIssuerFamilyPolicy:
    issuer_key: str
    display_name: str
    allowed_domains: tuple[str, ...]
    parser_family: str
    structured_sources_first: bool = True
    human_review_required_per_source: bool = False


@dataclass(frozen=True)
class ETFIssuerSourcePackSource:
    source_type: str
    url: str
    expected_content: str
    source_use_policy: str
    storage_rights: str
    export_rights: str
    parser_status: str = "pending_review"
    raw_body_storage_allowed: bool = False


@dataclass(frozen=True)
class ETFIssuerSourcePack:
    ticker: str
    fund_name: str
    issuer: str
    policy: ETFIssuerFamilyPolicy
    sources: tuple[ETFIssuerSourcePackSource, ...]
    source_pack_status: str
    fallback_order: tuple[str, ...] = ("official_issuer", "provider_api", "yahoo")
    automated_policy_can_approve_known_source_patterns: bool = True
    human_review_required_per_source: bool = False
    unsupported_product_gate_passed: bool = True

    @property
    def diagnostics(self) -> dict[str, object]:
        return {
            "schema_version": ETF_ISSUER_SOURCE_PACK_SCHEMA_VERSION,
            "policy_version": ETF_ISSUER_SOURCE_PACK_POLICY_VERSION,
            "ticker": self.ticker,
            "issuer": self.issuer,
            "issuer_family": self.policy.issuer_key,
            "parser_family": self.policy.parser_family,
            "allowed_domains": list(self.policy.allowed_domains),
            "source_pack_status": self.source_pack_status,
            "source_types": [source.source_type for source in self.sources],
            "structured_sources_first": self.policy.structured_sources_first,
            "human_review_required_per_source": self.human_review_required_per_source,
            "automated_policy_can_approve_known_source_patterns": self.automated_policy_can_approve_known_source_patterns,
            "unsupported_product_gate_passed": self.unsupported_product_gate_passed,
            "fallback_order": list(self.fallback_order),
            "raw_body_storage_allowed_by_default": False,
        }


ISSUER_FAMILY_POLICIES: dict[str, ETFIssuerFamilyPolicy] = {
    "vanguard": ETFIssuerFamilyPolicy(
        issuer_key="vanguard",
        display_name="Vanguard",
        allowed_domains=("investor.vanguard.com",),
        parser_family="vanguard_etf_parser_family",
    ),
    "ishares": ETFIssuerFamilyPolicy(
        issuer_key="ishares",
        display_name="iShares / BlackRock",
        allowed_domains=("www.ishares.com", "www.blackrock.com"),
        parser_family="ishares_blackrock_etf_parser_family",
    ),
    "state_street": ETFIssuerFamilyPolicy(
        issuer_key="state_street",
        display_name="State Street Global Advisors",
        allowed_domains=("www.ssga.com",),
        parser_family="state_street_spdr_etf_parser_family",
    ),
    "invesco": ETFIssuerFamilyPolicy(
        issuer_key="invesco",
        display_name="Invesco",
        allowed_domains=("www.invesco.com",),
        parser_family="invesco_etf_parser_family",
    ),
    "schwab": ETFIssuerFamilyPolicy(
        issuer_key="schwab",
        display_name="Schwab",
        allowed_domains=("www.schwabassetmanagement.com",),
        parser_family="schwab_etf_parser_family",
    ),
    "fidelity": ETFIssuerFamilyPolicy(
        issuer_key="fidelity",
        display_name="Fidelity",
        allowed_domains=("digital.fidelity.com", "www.fidelity.com"),
        parser_family="fidelity_etf_parser_family",
    ),
    "first_trust": ETFIssuerFamilyPolicy(
        issuer_key="first_trust",
        display_name="First Trust",
        allowed_domains=("www.ftportfolios.com",),
        parser_family="first_trust_etf_parser_family",
    ),
    "vaneck": ETFIssuerFamilyPolicy(
        issuer_key="vaneck",
        display_name="VanEck",
        allowed_domains=("www.vaneck.com",),
        parser_family="vaneck_etf_parser_family",
    ),
    "global_x": ETFIssuerFamilyPolicy(
        issuer_key="global_x",
        display_name="Global X",
        allowed_domains=("www.globalxetfs.com",),
        parser_family="global_x_etf_parser_family",
    ),
}


def build_automated_etf_issuer_source_pack(
    *,
    ticker: str,
    fund_name: str,
    issuer: str | None,
) -> ETFIssuerSourcePack | None:
    normalized_ticker = ticker.upper()
    normalized_issuer = issuer or ""
    family = issuer_family_policy(normalized_issuer)
    if family is None:
        return None
    if not etf_source_pack_scope_gate_passes(normalized_ticker, fund_name):
        return ETFIssuerSourcePack(
            ticker=normalized_ticker,
            fund_name=fund_name,
            issuer=normalized_issuer,
            policy=family,
            sources=(),
            source_pack_status="blocked_unsupported_product_gate",
            unsupported_product_gate_passed=False,
        )
    return ETFIssuerSourcePack(
        ticker=normalized_ticker,
        fund_name=fund_name,
        issuer=normalized_issuer,
        policy=family,
        sources=_source_pack_sources(family, normalized_ticker),
        source_pack_status="automated_policy_ready",
    )


def issuer_family_policy(issuer: str) -> ETFIssuerFamilyPolicy | None:
    normalized = issuer.lower()
    if "vanguard" in normalized:
        return ISSUER_FAMILY_POLICIES["vanguard"]
    if "ishares" in normalized or "blackrock" in normalized:
        return ISSUER_FAMILY_POLICIES["ishares"]
    if "state street" in normalized or "spdr" in normalized or "ssga" in normalized:
        return ISSUER_FAMILY_POLICIES["state_street"]
    if "invesco" in normalized:
        return ISSUER_FAMILY_POLICIES["invesco"]
    if "schwab" in normalized:
        return ISSUER_FAMILY_POLICIES["schwab"]
    if "fidelity" in normalized:
        return ISSUER_FAMILY_POLICIES["fidelity"]
    if "first trust" in normalized:
        return ISSUER_FAMILY_POLICIES["first_trust"]
    if "vaneck" in normalized or "van eck" in normalized:
        return ISSUER_FAMILY_POLICIES["vaneck"]
    if "global x" in normalized:
        return ISSUER_FAMILY_POLICIES["global_x"]
    return None


def etf_source_pack_scope_gate_passes(ticker: str, fund_name: str) -> bool:
    text = f"{ticker} {fund_name}".lower()
    return not any(marker in text for marker in UNSUPPORTED_ETF_SOURCE_PACK_MARKERS)


def _source_pack_sources(
    policy: ETFIssuerFamilyPolicy,
    ticker: str,
) -> tuple[ETFIssuerSourcePackSource, ...]:
    urls = _issuer_source_urls(policy.issuer_key, ticker)
    return tuple(
        ETFIssuerSourcePackSource(
            source_type=source_type,
            url=url,
            expected_content=_expected_content(source_type),
            source_use_policy="summary_allowed" if source_type in {"fact_sheet", "holdings", "exposures"} else "metadata_only",
            storage_rights="summary_allowed" if source_type in {"fact_sheet", "holdings", "exposures"} else "metadata_only",
            export_rights="metadata_only",
            parser_status="pending_review",
            raw_body_storage_allowed=False,
        )
        for source_type, url in urls.items()
    )


def _issuer_source_urls(issuer_key: str, ticker: str) -> dict[str, str]:
    encoded = quote(ticker.upper())
    lower = quote(ticker.lower())
    if issuer_key == "vanguard":
        base = f"https://investor.vanguard.com/investment-products/etfs/profile/{lower}"
        return {
            "product_page": base,
            "fact_sheet": base,
            "holdings": f"{base}#portfolio-composition",
            "exposures": f"{base}#portfolio-composition",
            "prospectus": f"{base}#documents",
            "shareholder_report": f"{base}#documents",
            "methodology": f"{base}#overview",
            "issuer_announcements": "https://corporate.vanguard.com/content/corporatesite/us/en/corp/pressroom.html",
        }
    if issuer_key == "ishares":
        base = f"https://www.ishares.com/us/products/search/{lower}"
        return {
            "product_page": base,
            "fact_sheet": f"{base}#/",
            "holdings": f"{base}#/holdings",
            "exposures": f"{base}#/holdings",
            "prospectus": f"{base}#/documents",
            "shareholder_report": f"{base}#/documents",
            "methodology": f"{base}#/documents",
            "issuer_announcements": "https://www.blackrock.com/corporate/newsroom",
        }
    if issuer_key == "state_street":
        base = f"https://www.ssga.com/us/en/intermediary/etfs/funds/{lower}"
        return {
            "product_page": base,
            "fact_sheet": base,
            "holdings": f"{base}#holdings",
            "exposures": f"{base}#holdings",
            "prospectus": f"{base}#documents",
            "shareholder_report": f"{base}#documents",
            "methodology": f"{base}#documents",
            "issuer_announcements": "https://www.ssga.com/us/en/intermediary/insights",
        }
    if issuer_key == "invesco":
        base = f"https://www.invesco.com/us/financial-products/etfs/product-detail?audienceType=Investor&ticker={encoded}"
        return {
            "product_page": base,
            "fact_sheet": base,
            "holdings": f"{base}#holdings",
            "exposures": f"{base}#holdings",
            "prospectus": f"{base}#documents",
            "shareholder_report": f"{base}#documents",
            "methodology": f"{base}#documents",
            "issuer_announcements": "https://www.invesco.com/us/en/insights.html",
        }
    domain = policy_domain_for_issuer(issuer_key)
    base = f"https://{domain}/search?q={encoded}"
    return {source_type: base for source_type in ETF_ISSUER_SOURCE_TYPES}


def policy_domain_for_issuer(issuer_key: str) -> str:
    policy = ISSUER_FAMILY_POLICIES[issuer_key]
    return policy.allowed_domains[0]


def _expected_content(source_type: str) -> str:
    if source_type in {"holdings", "exposures"}:
        return "structured_csv_xlsx_json_or_html_table_preferred"
    if source_type in {"fact_sheet", "prospectus", "shareholder_report", "methodology"}:
        return "official_document_or_metadata"
    return "official_html_or_metadata"
