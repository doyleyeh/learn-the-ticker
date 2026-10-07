import pytest

from backend.app.contracts import Claim
from backend.app.evidence import VisibleText, admit_bundle, fetch_public_text, verify_candidate
from tests.desktop.test_application import IDENTITY, source


@pytest.mark.parametrize("html,expected", [
    ('<p>The <b>Company</b>\u2019s report<span>ing</span> changed.</p>', 'The Company\u2019s reporting changed.'),
    ('<p>First.</p><p>Second<br>line.</p>', 'First. Second line.'),
    ('<table><tr><td>One</td><td>Two</td></tr><tr><td>Three</td></tr></table>', 'One Two Three'),
    ('<p>A&nbsp;&amp; B <i>continued</i>.</p>', 'A & B continued.'),
    ('<p>Safe<script>unsafe();</script><style>unsafe{}</style><noscript>unsafe</noscript> text.</p>', 'Safe text.'),
])
def test_text_preserves_inline_words_punctuation_and_structural_spacing(html, expected):
    parser = VisibleText()
    parser.feed(html)
    assert parser.text() == expected


def test_real_fetch_parser_allows_exact_quote_without_relaxing_support(monkeypatch):
    html = '<p>Synthetic Example Company (the <b>\u201cCompany</b>\u201d) changed its report<span>ing</span> structure.</p>'
    monkeypatch.setattr('backend.app.evidence.fetch_public_bytes', lambda _: html.encode())
    verified = verify_candidate(source(), IDENTITY, fetch_public_text)
    exact = 'Synthetic Example Company (the \u201cCompany\u201d) changed its reporting structure.'
    claims = [Claim(asset_id=IDENTITY.id, kind='fact', text=text, source_ids=[verified.id])
              for text in (exact, exact.replace('changed', 'did not change'), exact.replace('reporting', 'report ing'))]
    bundle = admit_bundle(IDENTITY, [verified], claims)
    assert [claim.text for claim in bundle.claims] == [exact]
    assert len(bundle.notes) == 2
