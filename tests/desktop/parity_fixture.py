"""Explicit synthetic asset kinds, admitted through the existing prose boundary."""
from backend.app.contracts import AssetIdentity, Claim, Source
from backend.app.evidence import admit_bundle, verify_candidate


def parity_bundles():
    for kind in ("fund", "unknown"):
        asset = AssetIdentity(id=f"XTEST:PARITY-{kind}", symbol=f"SYN-{kind.upper()}",
                              name=f"Synthetic {kind} parity", asset_type=kind, identifiers={"cik": "0000000001"})
        statements = [
            ("overview", f"Synthetic {kind} parity is a fictional browser example."),
            ("fund_objective_role", "The synthetic fund describes an educational asset basket."),
            ("holdings_exposure", "The synthetic basket has changing exposures."),
            ("construction_methodology", "Synthetic holdings follow a documented example method."),
            ("cost_trading_context", "Synthetic operating costs reduce fund assets."),
            ("news", "The synthetic fund reported a portfolio-method update."),
            *[("etf_specific_risks", f"Synthetic risk {name} remains uncertain.") for name in ("alpha", "beta", "gamma", "delta")],
        ]
        candidate = Source(id=f"parity-source-{kind}", asset_id=asset.id,
                           url="https://www.sec.gov/Archives/edgar/data/1/000000000100000001/parity.htm",
                           title=f"Synthetic {kind} disclosure", publisher="Synthetic fixture")
        text = " ".join(text for _, text in statements)
        checked = verify_candidate(candidate, asset, lambda _: text)
        claims = [Claim(asset_id=asset.id, section=section, text=text, source_ids=[candidate.id], kind="fact") for section, text in statements]
        yield admit_bundle(asset, [checked], claims)
