from datetime import date

from aasm.curated import load_all
from aasm.report import quality_note


def test_quality_note_has_the_ess_sections_and_key_numbers(curated_ok):
    tables = load_all(curated_ok)
    coverage = [{"req_id": "R09", "status": "in_progress"}, {"req_id": "R10", "status": "uncovered"}]
    lineage = {
        "retrieved_at": "2026-10-01T06:00:00Z",
        "rows": 120,
        "eurostat_updated": "2026-06-15T11:00:00+0200",
    }
    note = quality_note(tables, lineage, coverage, history=[], state={}, today=date(2026, 10, 1))
    for section in ("## Relevance", "## Accuracy", "## Timeliness", "## Coherence", "## Accessibility"):
        assert section in note
    assert "1 of 2 requirements" in note          # covered by at least one work item
    assert "Articles 8" in note
    assert "2026-10-01" in note                    # retrieved_at of standards
    assert "120 rows" in note


def test_quality_note_flags_stale_rows_and_missing_lineage(curated_ok):
    tables = load_all(curated_ok)
    note = quality_note(tables, None, [], history=[], state={}, today=date(2027, 2, 1))
    assert "older than 90 days: 1" in note
    assert "Eurostat: not fetched" in note


def test_quality_note_lists_deliverables_without_work_items(curated_ok):
    tables = load_all(curated_ok)
    note = quality_note(tables, None, [], history=[], state={}, today=date(2026, 10, 1))
    assert "D09" in note
