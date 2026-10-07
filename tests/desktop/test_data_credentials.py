import getpass
import io
import warnings

import pytest

from backend.app import data_credentials as credentials
from scripts import configure_data_sources as setup


KEY = "synthetic-test-data-key"


class Vault:
    def __init__(self):
        self.values = {}

    def get_password(self, service, account):
        return self.values.get((service, account))

    def set_password(self, service, account, value):
        self.values[service, account] = value


@pytest.fixture
def store():
    return credentials.DataCredentialStore(_vault=Vault())


@pytest.mark.parametrize("provider", credentials.PROVIDERS)
def test_separate_native_accounts_round_trip_without_repr_secret(store, provider):
    assert not store.configured(provider)
    store.save(provider, KEY, "free")
    result = store.load(provider)
    assert result.api_key == KEY and result.plan == "free"
    assert KEY not in repr(result)
    assert list(store._vault.values) == [(credentials.SERVICE, provider)]


@pytest.mark.parametrize("provider", ["openrouter", "database", "SEC_EDGAR_USER_AGENT", KEY])
def test_non_data_providers_cannot_reach_vault(store, provider):
    with pytest.raises(credentials.DataCredentialError, match="Unsupported"):
        store.save(provider, KEY)
    assert not store._vault.values


@pytest.mark.parametrize("key", ["", '"quoted"', "FMP_API_KEY=secret", "two words", "line\nbreak", "bad\rvalue", "x" * 1025, "https://secret.invalid", None])
def test_reject_non_key_inputs_without_storage(store, key):
    with pytest.raises(credentials.DataCredentialError):
        store.save("fmp", key)
    assert not store._vault.values


def test_unknown_platform_never_uses_generic_keyring_fallback(monkeypatch):
    monkeypatch.setattr(credentials.sys, "platform", "linux")
    with pytest.raises(credentials.DataCredentialError, match="native Windows"):
        credentials.DataCredentialStore()


@pytest.mark.parametrize("operation", ["get_password", "set_password"])
def test_native_failures_are_sanitized(store, operation):
    def fail(*args):
        raise RuntimeError(KEY)
    setattr(store._vault, operation, fail)
    with pytest.raises(credentials.DataCredentialError) as caught:
        store.save("fmp", KEY)
    assert KEY not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("payload", ['{"api_key":"synthetic-test-data-key","plan":"free","extra":1}', '"secret"', "x" * 8193, "not-json"])
def test_corrupt_vault_record_is_not_treated_as_configured(store, payload):
    store._vault.values[(credentials.SERVICE, "fmp")] = payload
    with pytest.raises(credentials.DataCredentialError, match="Could not read"):
        store.configured("fmp")


def test_readback_mismatch_does_not_report_success(store, monkeypatch):
    monkeypatch.setattr(store, "load", lambda provider: credentials.DataCredential("wrong"))
    with pytest.raises(credentials.DataCredentialError, match="Could not verify"):
        store.save("fmp", KEY)


@pytest.mark.parametrize("plan", ["bad\nplan", "x" * 101, None])
def test_invalid_plan_never_writes(store, plan):
    with pytest.raises(credentials.DataCredentialError):
        store.save("fmp", KEY, plan)
    assert not store._vault.values


def interactive(monkeypatch, store, answers):
    monkeypatch.setattr(setup, "DataCredentialStore", lambda: store)
    for stream in (setup.sys.stdin, setup.sys.stdout, setup.sys.stderr):
        monkeypatch.setattr(stream, "isatty", lambda: True)
    values = iter(answers)
    monkeypatch.setattr(setup, "hidden_key", lambda prompt: next(values))


def test_interactive_skip_preserves_old_key_and_saves_new_provider(store, monkeypatch, capsys):
    store.save("fmp", "previous-key", "paid")
    interactive(monkeypatch, store, ["", KEY, ""])
    assert setup.main(["--provider", "fmp", "--provider", "eodhd"]) == 0
    assert store.load("fmp").api_key == "previous-key"
    assert store.load("eodhd").api_key == KEY
    assert store.load("eodhd").plan == "unknown"
    output = capsys.readouterr()
    assert KEY not in output.out + output.err and "previous-key" not in output.out


def test_noninteractive_input_is_rejected_before_vault_or_prompt(monkeypatch, capsys):
    monkeypatch.setattr(setup.sys, "stdin", io.StringIO(KEY))
    monkeypatch.setattr(setup, "DataCredentialStore", lambda: pytest.fail("must not open vault"))
    assert setup.main([]) == 2
    assert KEY not in capsys.readouterr().out


def test_status_never_prints_key_or_plan(store, monkeypatch, capsys):
    store.save("eodhd", KEY, "private-label")
    monkeypatch.setattr(setup, "DataCredentialStore", lambda: store)
    assert setup.main(["--status", "--provider", "eodhd"]) == 0
    output = capsys.readouterr().out
    assert "eodhd: configured" in output
    assert KEY not in output and "private-label" not in output


@pytest.mark.parametrize("arguments", [["--api-key", KEY], ["--provider", KEY], [KEY]])
def test_argument_parser_never_echoes_rejected_secret(arguments, capsys):
    with pytest.raises(SystemExit) as caught:
        setup.main(arguments)
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert KEY not in output.out + output.err


def test_hidden_prompt_cannot_fall_back_to_echo(monkeypatch):
    def fallback(prompt):
        warnings.warn("fallback", getpass.GetPassWarning)
        pytest.fail("must stop before echoed fallback")
    monkeypatch.setattr(setup.getpass, "getpass", fallback)
    with pytest.raises(getpass.GetPassWarning):
        setup.hidden_key("Key: ")


def test_cancel_preserves_prior_saved_steps(store, monkeypatch, capsys):
    interactive(monkeypatch, store, [KEY, "free"])
    def prompt(prompt):
        raise KeyboardInterrupt
    store.save("fmp", KEY)
    monkeypatch.setattr(setup, "hidden_key", prompt)
    assert setup.main(["--provider", "eodhd"]) == 2
    assert store.load("fmp").api_key == KEY
    assert KEY not in capsys.readouterr().out
