from datetime import date, datetime

import pytest

from backend.app.contracts import Claim
from backend.app.weekly import select_weekly, weekly_window
from tests.desktop.weekly_fixture import weekly_bundle


@pytest.mark.parametrize("instant,day,start,end,current", [
    ("2026-03-09T03:59:59+00:00", "2026-03-08", "2026-02-23", "2026-03-01", "2026-03-07"),
    ("2026-03-09T04:00:00+00:00", "2026-03-09", "2026-03-02", "2026-03-08", None),
    ("2026-11-02T04:59:59+00:00", "2026-11-01", "2026-10-19", "2026-10-25", "2026-10-31"),
    ("2026-11-02T05:00:00+00:00", "2026-11-02", "2026-10-26", "2026-11-01", None),
    ("2026-01-01T12:00:00+00:00", "2026-01-01", "2025-12-22", "2025-12-28", "2025-12-31"),
])
def test_eastern_windows_include_dst_monday_and_year_boundaries(instant, day, start, end, current):
    window = weekly_window(datetime.fromisoformat(instant))
    assert window.as_of.isoformat() == day
    assert window.previous_start.isoformat() == start and window.previous_end.isoformat() == end
    assert (window.current_end.isoformat() if window.current_end else None) == current
    assert (window.current_start is None) == (current is None)


def test_naive_timestamps_and_unparsed_strings_are_rejected():
    for value in (datetime(2026, 3, 9), "2026-03-09T00:00:00Z"):
        with pytest.raises(ValueError):
            weekly_window(value)


@pytest.mark.parametrize("count", [0, 1, 2, 3, 4])
def test_sparse_and_analysis_thresholds_never_count_earlier_context(count):
    bundle = weekly_bundle(["2026-09-30"] * count + ["2026-09-17"])
    focus = select_weekly(bundle, as_of=date(2026, 10, 4))
    assert len(focus.weekly) == count
    assert focus.analysis_available == (count >= 2)
    assert focus.earlier_requested == (count < 3)
    assert len(focus.earlier) == (1 if count < 3 else 0)
    assert all(item.bucket != "earlier_context" for item in focus.weekly)


def test_inclusive_thirty_day_bounds_today_excluded_and_reporting_date_is_not_event_date():
    bundle = weekly_bundle(["2026-09-03", "2026-09-04", "2026-09-20", "2026-09-21", "2026-09-28", "2026-10-04"])
    focus = select_weekly(bundle, as_of=date(2026, 10, 4))
    assert [str(item.published) for item in focus.weekly] == ["2026-09-28", "2026-09-21"]
    assert [str(item.published) for item in focus.earlier] == ["2026-09-20", "2026-09-04"]
    bundle.sources[-2].filing_publication.report_date = date(2025, 1, 1)
    bundle.sources[-2].as_of = date(2025, 1, 1)
    assert select_weekly(bundle, as_of=date(2026, 10, 4)).weekly[0].published == date(2026, 9, 28)


def test_duplicate_accessions_and_identical_source_bodies_do_not_inflate_counts():
    bundle = weekly_bundle()
    duplicate = bundle.sources[-3].model_copy(update={"id": "duplicate"})
    bundle.sources.append(duplicate)
    bundle.sources[-2].content_hash = bundle.sources[-3].content_hash
    focus = select_weekly(bundle, as_of=date(2026, 10, 4))
    assert len(focus.weekly) == 2 and not focus.earlier
    bundle.sources[-3].content_hash = bundle.sources[-4].content_hash
    assert len(select_weekly(bundle, as_of=date(2026, 10, 4)).weekly) == 1


def test_model_dates_notes_and_unverified_weekly_sections_cannot_become_events():
    bundle = weekly_bundle()
    for source in bundle.sources:
        source.filing_publication = None
    bundle.notes.append(Claim(asset_id=bundle.asset.id, section="weekly_news", text="Unverified new event.", as_of=date(2026, 10, 1)))
    focus = select_weekly(bundle, as_of=date(2026, 10, 4))
    assert focus.weekly == focus.earlier == [] and not focus.analysis_available


@pytest.mark.parametrize("mutation", [
    lambda b: b.update(identity_verification=None),
    lambda b: b["asset"].update(name="Wrong issuer"),
    lambda b: b["sources"][-1].update(policy="link_only", excerpt=""),
    lambda b: b["sources"][-1].update(asset_id="other"),
    lambda b: b["sources"][-1]["filing_publication"].update(filed="2030-01-01"),
])
def test_wrong_identity_rights_and_date_proofs_fail_before_selection(mutation):
    payload = weekly_bundle().model_dump(mode="json")
    mutation(payload)
    with pytest.raises(ValueError):
        select_weekly(payload, as_of=date(2026, 10, 4))


def test_deterministic_official_only_selection_and_no_input_mutation():
    bundle = weekly_bundle(["2026-09-30"] * 10)
    original = bundle.model_dump(mode="json")
    selected = select_weekly(bundle, as_of=date(2026, 10, 4))
    assert len(selected.weekly) == 8 and all(item.title == "8-K filing" for item in selected.weekly)
    assert bundle.model_dump(mode="json") == original
    bundle.sources.reverse()
    assert select_weekly(bundle, as_of=date(2026, 10, 4)) == selected
