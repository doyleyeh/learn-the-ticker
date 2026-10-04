import pytest


@pytest.fixture(autouse=True)
def no_live_sec_contact(monkeypatch):
    # A developer's configured live contact must not activate retrieval in normal CI.
    monkeypatch.delenv("LTT_SEC_USER_AGENT", raising=False)
