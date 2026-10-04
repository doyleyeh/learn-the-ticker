"""Ephemeral source selection; never a provider permission or an evidence verdict."""
import asyncio
from dataclasses import dataclass
from datetime import date, timedelta

from pydantic import AwareDatetime, Field, HttpUrl

from backend.app.contracts import Contract, SourcePolicy, now, uid
from backend.app.runtime_base import RuntimeFailure
from backend.app.source_registry import source_rule
from backend.app.market_rules import private_market_rule


class ReviewSource(Contract):
    id: str = Field(default_factory=uid)
    url: HttpUrl
    publisher: str
    policy: SourcePolicy
    rights_url: HttpUrl
    reviewed_at: date
    local_numeric_only: bool = False


class SourceReviewRequest(Contract):
    id: str = Field(default_factory=uid)
    run_id: str
    asset_id: str
    sources: list[ReviewSource] = Field(min_length=1, max_length=100)
    expires_at: AwareDatetime


class SourceReviewDecision(Contract):
    cancel: bool = False
    source_ids: list[str] = Field(default_factory=list, max_length=100)


@dataclass
class PendingReview:
    request: SourceReviewRequest
    future: asyncio.Future
    deadline: float


class SourceReviewBroker:
    def __init__(self, lifetime=120):
        self.lifetime = lifetime
        self.pending: dict[str, PendingReview] = {}

    def snapshot(self):
        at = asyncio.get_running_loop().time()
        return [item.request.model_copy(deep=True) for item in self.pending.values()
                if not item.future.done() and at < item.deadline]

    async def review(self, run_id, asset_id, rules):
        if len(self.pending) >= 20 or any(item.request.run_id == run_id for item in self.pending.values()):
            raise RuntimeFailure("Source review queue is full or this research already has a review.")
        loop = asyncio.get_running_loop()
        request = SourceReviewRequest(run_id=run_id, asset_id=asset_id,
            sources=[ReviewSource(url=url, publisher=rule.publisher, policy=rule.policy,
                rights_url=rule.rights_url, reviewed_at=rule.reviewed_at,
                local_numeric_only=rule.id.startswith("private-")) for url, rule in rules.items()],
            expires_at=now() + timedelta(seconds=self.lifetime))
        item = PendingReview(request, loop.create_future(), loop.time() + self.lifetime)
        self.pending[request.id] = item
        try:
            decision = await asyncio.wait_for(item.future, self.lifetime)
            if decision.cancel:
                raise asyncio.CancelledError()
            return {str(source.url) for source in request.sources if source.id in decision.source_ids}
        except TimeoutError:
            raise RuntimeFailure("Source review expired. No unanswered sources were approved; retry explicitly.") from None
        finally:
            self.pending.pop(request.id, None)

    def resolve(self, run_id, request_id, decision):
        item = self.pending.get(request_id)
        if not item or item.request.run_id != run_id or item.future.done() or asyncio.get_running_loop().time() >= item.deadline:
            raise ValueError("Source review expired or no longer belongs to this active research.")
        selected = set(decision.source_ids)
        if (len(selected) != len(decision.source_ids) or (decision.cancel and selected)
                or not selected <= {source.id for source in item.request.sources}):
            raise ValueError("Select only sources in this review; no source was approved.")
        item.future.set_result(decision.model_copy(deep=True))

    def cancel(self, run_id=None):
        for item in self.pending.values():
            if (run_id is None or item.request.run_id == run_id) and not item.future.done():
                item.future.cancel()


class SourceReviewScope:
    """Once enabled for a run, review cannot be silently removed by a settings toggle."""
    def __init__(self, service, run_id):
        self.service, self.run_id = service, run_id
        self.enabled = service.settings().manual_source_review
        self.accepted, self.considered = {}, set()
        self.private_urls = set()

    def active(self):
        self.enabled = self.enabled or self.service.settings().manual_source_review
        return self.enabled

    def allowed(self, url):
        if url in self.private_urls and not self.service.settings().experimental_yahoo_enabled:
            return False
        return not self.active() or (url in self.accepted and self.current_rule(url) == self.accepted[url])

    def current_rule(self, url):
        if url in self.private_urls:
            return private_market_rule(url) if self.service.settings().experimental_yahoo_enabled else None
        return source_rule(url)

    async def select(self, asset_id, urls, *, private_market=False):
        self.service.require_consent()
        urls = list(dict.fromkeys(urls))
        if private_market:
            if not self.service.settings().experimental_yahoo_enabled:
                return set()
            urls = [url for url in urls if private_market_rule(url)]
            self.private_urls.update(urls)
        if not self.active():
            return set(urls)
        rules = {url: self.current_rule(url) for url in urls if url not in self.considered}
        # Unknown/limited permissions never offer an override. No model metadata is trusted.
        rules = {url: rule for url, rule in rules.items() if rule and (rule.policy == SourcePolicy.full_text or (private_market and url in self.private_urls))}
        self.considered.update(urls)
        if rules:
            chosen = await self.service.source_reviews.review(self.run_id, asset_id, rules)
            self.service.require_consent()
            self.accepted.update({url: rules[url] for url in chosen if self.current_rule(url) == rules[url]})
        return {url for url in urls if self.allowed(url)}
