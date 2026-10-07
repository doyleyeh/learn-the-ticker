from contextlib import contextmanager
import ctypes as C
from types import SimpleNamespace

import pytest

from scripts.windows_codex_filter import Blob, GuardError, MARKER, NativeStore, check, manage


class Store:
    def __init__(self, states=("absent",) * 3):
        self.states = states
        self.changes = []
        self.abort = False

    @contextmanager
    def transaction(self):
        original = self.states
        try:
            yield
        except BaseException:
            self.states, self.abort = original, True
            raise

    def inspect(self): return self.states
    def install(self): self.states = ("matched",) * 3; self.changes.append("install")
    def remove(self): self.states = ("absent",) * 3; self.changes.append("remove")


def test_guard_install_inspect_idempotence_and_exact_removal():
    store = Store()
    assert manage(store) == "absent" and store.changes == []
    assert manage(store, "apply") == "installed"
    assert manage(store, "apply") == "installed" and store.changes == ["install"]
    assert manage(store) == "installed"
    assert manage(store, "remove") == "absent"
    assert manage(store, "remove") == "absent" and store.changes == ["install", "remove"]


@pytest.mark.parametrize("states", [("matched", "absent", "absent"), ("conflict",) * 3])
@pytest.mark.parametrize("action", ["apply", "remove"])
def test_partial_or_foreign_policy_never_overwritten_or_removed(states, action):
    store = Store(states)
    with pytest.raises(GuardError): manage(store, action)
    assert store.states == states and store.abort and not store.changes


@pytest.mark.parametrize("failure", ["exception", "readback"])
def test_failed_install_aborts_complete_transaction(failure):
    store = Store()
    def install():
        store.states = ("matched", "absent", "absent")
        if failure == "exception": raise OSError("synthetic native failure")
    store.install = install
    with pytest.raises((OSError, GuardError)): manage(store, "apply")
    assert store.states == ("absent",) * 3 and store.abort


def synthetic_native_store():
    # No Windows API, account lookup or host mutation in normal tests.
    store = object.__new__(NativeStore)
    store.metadata = C.create_string_buffer(MARKER)
    store.metadata_blob = Blob(len(MARKER), C.cast(store.metadata, C.c_void_p))
    store.descriptor = C.create_string_buffer(b"synthetic scoped descriptor")
    store.descriptor_blob = Blob(len(store.descriptor), C.cast(store.descriptor, C.c_void_p))
    return store


@pytest.mark.parametrize("changed", ["action", "account", "loopback", "layer", "metadata", "persistence", "weight", "count"])
def test_native_readback_rejects_changed_security_scope(changed):
    store = synthetic_native_store()
    expected, actual = store._filter(0), store._filter(0)
    assert store._matches(actual, expected)
    if changed == "action": actual.action.type = 0x1002
    elif changed == "account": actual.conditions[0].value.value.ptr = None
    elif changed == "loopback": actual.conditions[1].value.value.uint32 = 0
    elif changed == "layer": actual.layer = store._filter(1).layer
    elif changed == "metadata": actual.provider_data = Blob(0, None)
    elif changed == "persistence": actual.flags = 0
    elif changed == "weight": actual.weight.type = 3
    else: actual.count = 0
    try:
        assert not store._matches(actual, expected)
    except GuardError:
        assert changed == "metadata"


def test_native_transaction_aborts_if_commit_fails():
    calls = []
    store = object.__new__(NativeStore)
    store.handle = None
    store.fw = SimpleNamespace(FwpmTransactionBegin0=lambda *_: 0,
                              FwpmTransactionCommit0=lambda *_: 1,
                              FwpmTransactionAbort0=lambda *_: calls.append("abort"))
    with pytest.raises(GuardError):
        with store.transaction(): pass
    assert calls == ["abort"]


@pytest.mark.parametrize("weight,valid", [(0xFFFF, True), (0xFFFC, True), (0xFF00, True), (0xFEFF, False), (0, False)])
def test_sublayer_accepts_bfe_nearest_available_weight_only_in_required_range(weight, valid):
    store = synthetic_native_store()
    actual, expected = store._sublayer(), store._sublayer()
    actual.weight = weight
    assert store._matches(actual, expected) == valid


def test_cli_inspection_is_readonly_and_mutation_requires_interactive_elevation(monkeypatch, capsys):
    from scripts import repair_codex_sandbox
    store = Store()
    @contextmanager
    def factory(): yield store
    monkeypatch.setattr(repair_codex_sandbox, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(repair_codex_sandbox, "NativeStore", factory)
    assert repair_codex_sandbox.main([]) == 2
    assert not store.changes and '"status": "absent"' in capsys.readouterr().out
    monkeypatch.setattr(repair_codex_sandbox.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert repair_codex_sandbox.main(["--apply"]) == 2
    assert not store.changes and "elevated interactive" in capsys.readouterr().out


def test_native_access_denial_explains_elevation_without_raw_diagnostics():
    with pytest.raises(GuardError, match="elevated terminal"):
        check(5)
