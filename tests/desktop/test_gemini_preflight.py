import copy
import shutil
import subprocess

import pytest

from scripts import qualify_gemini as probe
from backend.app.runtime_base import provider_environment


@pytest.mark.parametrize("scenario", ["preflight", "onboarding"])
def test_preflight_behavior_without_provider_account_vault_or_network(scenario):
    result = subprocess.run(
        [shutil.which("node") or "node", str(probe.ROOT / f"tests/desktop/gemini_{scenario}_scenarios.mjs")],
        capture_output=True, timeout=20, env=provider_environment(),
    )
    assert result.returncode == 0, "Synthetic account/transport/usage scenario failed"
    assert result.stdout == f"{scenario}_scenarios_passed\n".encode()
    assert result.stderr == b""


def test_no_implicit_live_access():
    with pytest.raises(SystemExit) as exc:
        probe.main([])
    assert exc.value.code == 2


def report():
    return {"status": "metadata_verified", "generation_qualified": False, "inference_requested": False,
            "credits_enabled": False, "tier": "standard-tier", "paid_tier_present": True,
            "quota_models": [{"model": "gemini-2.5-flash", "remaining_fraction": 0.5, "reset_at": "2026-10-07T00:00:00Z"}]}


def test_bounded_summary_preserves_unqualified_state():
    assert probe.validate_report(report()) == report()


@pytest.mark.parametrize("patch", [
    {"generation_qualified": True}, {"inference_requested": True}, {"credits_enabled": True},
    {"project": "private"}, {"account": "private"}, {"phase": "private diagnostic"}, {"tier": "unknown"},
    {"paid_tier_present": "true"}, {"quota_models": []}, {"status": "private diagnostic"},
])
def test_unsafe_report_never_printed(patch):
    with pytest.raises(ValueError):
        probe.validate_report({**report(), **patch})


@pytest.mark.parametrize("patch", [
    {"model": "private diagnostic /"}, {"model": "auto"}, {"remaining_fraction": True},
    {"remaining_fraction": -1}, {"remaining_fraction": float("nan")}, {"reset_at": "private"}, {"tokens": "private"},
])
def test_nested_private_or_invalid_metadata_rejected(patch):
    value = copy.deepcopy(report())
    value["quota_models"][0].update(patch)
    with pytest.raises(ValueError):
        probe.validate_report(value)
