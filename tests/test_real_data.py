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
