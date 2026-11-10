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


def test_deliverables_follow_c_2025_3871():
    for d in load_table(REAL, "request_deliverables"):
        assert (d["request_ref"], d["due_date"]) == ("C(2025) 3871", "2025-08-31"), d["deliverable_id"]


def test_deadlines_are_those_in_force_after_the_digital_omnibus():
    dates = {d["deadline_id"]: d["date"] for d in load_table(REAL, "deadlines")}
    assert dates == {"HR_ANNEX3": "2027-12-02", "HR_ANNEX1": "2028-08-02"}


def test_article_11_is_mapped_to_the_quality_management_deliverable():
    d09 = next(d for d in load_table(REAL, "request_deliverables") if d["deliverable_id"] == "D09")
    assert "R11" in d09["covers_req_ids"].split("|")


def test_en_18286_is_recorded_as_cited():
    en = next(s for s in load_table(REAL, "standards") if s["wi_ref"] == "EN 18286:2026")
    assert (en["ojeu_cited"], en["ojeu_date"]) == ("true", "2026-10-14")


def test_the_one_work_item_linked_by_judgement_is_recorded_as_such():
    judged = [s["wi_ref"] for s in load_table(REAL, "standards") if s["link_basis"] == "judged"]
    assert judged == ["prEN 18283"]


def test_the_one_deliverable_linked_to_a_requirement_by_judgement_is_recorded_as_such():
    deliverables = load_table(REAL, "request_deliverables")
    judged = [d["deliverable_id"] for d in deliverables if d["link_basis"] == "judged"]
    assert judged == ["D09"]


def _derived_coverage():
    import csv

    path = REAL.parent / "derived" / "coverage_by_requirement.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_article_11_is_uncovered_on_public_sources_and_harmonised_only_with_the_judged_link():
    # read at the date of the published file, so a stage that moves later cannot change the past
    r11 = next(r for r in _derived_coverage() if r["article"] == "11")
    assert (r11["status"], r11["status_with_judged"], r11["n_judged"]) == ("uncovered", "harmonised", "1")


def test_the_published_coverage_file_follows_the_rule_on_the_curated_tables():
    from datetime import date

    from aasm.curated import load_all
    from aasm.derive import COVERAGE_COLUMNS, coverage_by_requirement

    rows = _derived_coverage()
    assert tuple(rows[0]) == COVERAGE_COLUMNS
    expected = coverage_by_requirement(load_all(REAL), date.fromisoformat(rows[0]["as_of"]))
    assert rows == [{k: str(v) for k, v in r.items()} for r in expected]
