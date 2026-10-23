from pathlib import Path

from aasm.curated import check_tables, load_table

REAL = Path(__file__).resolve().parents[1] / "data" / "curated"


def test_real_curated_tables_pass_check():
    assert check_tables(REAL) == []


def test_requirements_cover_articles_8_to_15():
    articles = sorted(int(r["article"]) for r in load_table(REAL, "requirements"))
    assert articles == list(range(8, 16))


def test_annex3_has_eight_areas():
    assert [r["area_id"] for r in load_table(REAL, "annex3_areas")] == [str(i) for i in range(1, 9)]


def test_request_has_ten_deliverables():
    assert len(load_table(REAL, "request_deliverables")) == 10


def test_every_in_perimeter_requirement_is_covered_by_a_deliverable():
    covered = set()
    for d in load_table(REAL, "request_deliverables"):
        covered |= {x for x in d["covers_req_ids"].split("|") if x}
    assert covered == {f"R{n:02d}" for n in range(9, 16)}  # Article 8 is the umbrella clause


def test_every_deliverable_has_at_least_one_work_item_or_a_note():
    standards = load_table(REAL, "standards")
    deliverables = load_table(REAL, "request_deliverables")
    with_wi = {s["deliverable_id"] for s in standards}
    for d in deliverables:
        assert d["deliverable_id"] in with_wi or "no work item" in d["note"].lower(), d["deliverable_id"]


def test_standards_have_a_recent_retrieved_at():
    from datetime import date
    for s in load_table(REAL, "standards"):
        assert date.fromisoformat(s["retrieved_at"]) >= date(2026, 10, 1), s["wi_ref"]
