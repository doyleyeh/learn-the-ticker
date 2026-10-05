"""Explicit production private-retrieval/publication check; no model or persistent library."""
import argparse
import asyncio
import json
from pathlib import Path
import tempfile
import threading
from unittest.mock import patch

from backend.app.contracts import EvidenceBundle, ResearchRequest, uid
from backend.app.db import Database, Job
from backend.app.evidence import factual_context
from backend.app.figi_identity import valid_figi
from backend.app.market_evidence import attach_market
from backend.app.research import ResearchService
from backend.app.source_operations import shareable_view
from backend.app.source_review import SourceReviewScope


async def check(*, live=False, asset_id="", service_factory=None, require_valuations=False):
    if not live:
        return {"status": "not_run", "reason": "Pass --live and an independently selected --asset-id to opt into this private check."}
    if not asset_id.startswith("FIGI:") or not valid_figi(asset_id[5:]):
        return {"status": "blocked", "reason": "Use an exact independently selected listing FIGI."}
    db = Database("sqlite://", testing=True)
    service = None
    try:
        with tempfile.TemporaryDirectory(prefix="ltt-market-qualification-") as directory:
            workspace = Path(directory)
            service = (service_factory(db, workspace) if service_factory else ResearchService(db, {}, workspace))
            db.put("settings", "settings", {"cloud_enabled": True, "experimental_yahoo_enabled": True})
            identities = await service.resolve(asset_id)
            if len(identities) != 1 or identities[0].asset.id != asset_id:
                return {"status": "blocked", "reason": "Independent exact listing verification was unavailable."}
            resolved = identities[0]
            job_id = uid()
            with db.session.begin() as session:
                session.add(Job(id=job_id, status="running", request=ResearchRequest(query=asset_id).model_dump(mode="json")))
            scope = SourceReviewScope(service, job_id)
            mapped, gap = await service.market_adapter.retrieve(resolved, threading.Event(), scope)
            if mapped is None:
                return {"status": "blocked", "reason": gap}
            bundle = attach_market(EvidenceBundle(asset=resolved.asset, identity_verification=resolved.verification,
                language="en", level="beginner"), mapped, personal_mode=True, created_at=service.clock())
            service.checkpoint(job_id, bundle, scope)
            checkpoint = db.job(job_id)["result"]
            if not checkpoint or checkpoint["completion"] != "section_checkpoint":
                raise ValueError
            db.complete_research(job_id, bundle.model_dump(mode="json"))
            retained = EvidenceBundle.model_validate(db.get("asset:" + asset_id))
            context = factual_context(retained)
            exported, notice = shareable_view(retained)
            if (retained != bundle or context["claims"] or context["sources"] or not context.get("context_gaps")
                    or exported.market or exported.sources or not notice or db.get("bundle:" + checkpoint["id"]) != checkpoint):
                raise ValueError
            source = retained.sources[0]
            valuations = retained.market.valuations
            if require_valuations and (not valuations or not any(p.metric == "PeRatio" and p.sampling != "trailing" and p.value is not None for p in valuations.points)):
                return {"status": "blocked", "reason": "Historical provider P/E observations were not admitted; no retry was made."}
            valuation_report = None
            if valuations:
                citation = next(s for s in retained.sources if s.id == valuations.source_id)
                valuation_report = {"source_url": str(citation.url), "source_hash": citation.content_hash,
                    "retrieved_at": citation.retrieved_at.isoformat(), "observations": len(valuations.points),
                    "available": sum(p.value is not None for p in valuations.points),
                    "series": [{"metric": metric, "sampling": sampling,
                        "dates": [p.date.isoformat() for p in valuations.points if (p.metric, p.sampling) == (metric, sampling)]}
                        for metric, sampling in sorted({(p.metric, p.sampling) for p in valuations.points})]}
            return {"status": "qualified", "asset_id": asset_id, "rows": len(retained.market.bars),
                "actions": len(retained.market.actions), "requested_start": retained.market.requested_start.isoformat(),
                "first_date": retained.market.bars[0].date.isoformat(), "last_date": retained.market.bars[-1].date.isoformat(),
                "source_url": str(source.url), "source_hash": source.content_hash,
                "retrieved_at": source.retrieved_at.isoformat(), "fingerprint": retained.market.fingerprint,
                "return_method": retained.market.return_method,
                "return_windows": {row.period: row.reason or "available" for row in retained.market.returns},
                "valuations": valuation_report,
                "checkpoint_preserved": True, "cloud_excluded": True, "shareable_export_excluded": True,
                "scope": "Actual production retrieval/queue/admission/publication in a discarded in-memory test DB; no model, durable user-library write, PostgreSQL/native/UI qualification or public permission grant."}
    except Exception:
        return {"status": "blocked", "reason": "Production private retrieval could not be validated; no retry was made."}
    finally:
        if service is not None:
            await service.close()
        db.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--asset-id", default="")
    parser.add_argument("--packaged-worker", action="store_true")
    parser.add_argument("--require-valuations", action="store_true")
    args = parser.parse_args()
    if args.packaged_worker:
        executable = Path(__file__).resolve().parents[1] / "dist/ltt-service.exe"
        if not executable.is_file():
            raise SystemExit("Build the Windows sidecar before packaged market qualification")
        with patch("sys.frozen", True, create=True), patch("sys.executable", str(executable)):
            result = asyncio.run(check(live=args.live, asset_id=args.asset_id, require_valuations=args.require_valuations))
        result["worker"] = "frozen Windows sidecar; orchestration/test database run from source"
    else:
        result = asyncio.run(check(live=args.live, asset_id=args.asset_id, require_valuations=args.require_valuations))
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "qualified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
