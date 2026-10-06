import json

import pytest

from backend.app.runtime_base import RuntimeFailure, executable_command


def setup(tmp_path, monkeypatch, *, entry="bundle/gemini.js", local=False):
    modules = tmp_path / "node_modules"
    root = modules / "@google/gemini-cli"
    script = root / entry
    script.parent.mkdir(parents=True)
    script.write_text("// synthetic entry; never executed", encoding="utf-8")
    manifest = root / "package.json"
    manifest.write_text(json.dumps({"name": "@google/gemini-cli", "bin": {"gemini": entry}}), encoding="utf-8")
    shim = modules / ".bin/gemini.cmd" if local else tmp_path / "gemini.cmd"
    monkeypatch.setattr("backend.app.runtime_base.shutil.which", lambda name: str(shim) if name == "gemini" else "node.exe")
    return manifest, script


@pytest.mark.parametrize("entry", ["dist/index.js", "bundle/gemini.js"])
@pytest.mark.parametrize("local", [False, True])
def test_official_legacy_and_bundled_entries_resolve_without_a_shell(tmp_path, monkeypatch, entry, local):
    _, script = setup(tmp_path, monkeypatch, entry=entry, local=local)
    assert executable_command("gemini") == ["node.exe", str(script)]


@pytest.mark.parametrize("metadata", [
    {"name": "other", "bin": {"gemini": "bundle/gemini.js"}},
    {"name": "@google/gemini-cli", "bin": {"gemini": "../../outside.js"}},
    {"name": "@google/gemini-cli", "bin": {"gemini": "other.js"}},
    {"name": "@google/gemini-cli", "bin": "bundle/gemini.js"}, [], None,
])
def test_unknown_or_malformed_package_entries_fail_closed(tmp_path, monkeypatch, metadata):
    manifest, _ = setup(tmp_path, monkeypatch)
    manifest.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(RuntimeFailure, match="entry could not be verified"):
        executable_command("gemini")


def test_missing_oversized_and_broken_metadata_or_entry_fail(tmp_path, monkeypatch):
    manifest, script = setup(tmp_path, monkeypatch)
    valid = manifest.read_text()
    for content in ("{", " " * (64 * 1024 + 1)):
        manifest.write_text(content)
        with pytest.raises(RuntimeFailure):
            executable_command("gemini")
    manifest.write_text(valid)
    script.unlink()
    with pytest.raises(RuntimeFailure, match="compatible native executable"):
        executable_command("gemini")
    manifest.unlink()
    with pytest.raises(RuntimeFailure, match="entry could not be verified"):
        executable_command("gemini")


def test_native_executable_remains_direct_and_missing_runtime_stays_disabled(monkeypatch):
    monkeypatch.setattr("backend.app.runtime_base.shutil.which", lambda _: "C:/synthetic/gemini.exe")
    assert executable_command("gemini") == ["C:/synthetic/gemini.exe"]
    monkeypatch.setattr("backend.app.runtime_base.shutil.which", lambda _: None)
    with pytest.raises(RuntimeFailure, match="not installed"):
        executable_command("gemini")
