from datetime import date

from aasm.derive import coverage_by_requirement, timeline

REQ = [
    {"req_id": "R09", "article": "9", "paragraph": "", "title": "Risk", "summary": "s", "source_url": "https://x"},
    {"req_id": "R10", "article": "10", "paragraph": "", "title": "Data", "summary": "s", "source_url": "https://x"},
    {"req_id": "R11", "article": "11", "paragraph": "", "title": "Docs", "summary": "s", "source_url": "https://x"},
]
DEL = [
    {"deliverable_id": "D01", "title": "RM", "request_ref": "M", "due_date": "2025-04-30",
     "covers_req_ids": "R09", "source_url": "https://x", "note": ""},
    {"deliverable_id": "D02", "title": "Data", "request_ref": "M", "due_date": "2025-04-30",
     "covers_req_ids": "R10", "source_url": "https://x", "note": ""},
    {"deliverable_id": "D09", "title": "QMS", "request_ref": "M", "due_date": "2025-04-30",
     "covers_req_ids": "", "source_url": "https://x", "note": "outside"},
]


def std(wi, dlv, stage, stage_date, target="", cited="false", ojeu=""):
    return {"wi_ref": wi, "title": wi, "deliverable_id": dlv, "stage_code": stage, "stage_date": stage_date,
            "target_pub_date": target, "ojeu_cited": cited, "ojeu_date": ojeu, "source_url": "https://x",
            "retrieved_at": "2026-10-01", "note": ""}


DEAD = [{"deadline_id": "HR", "date": "2026-08-02", "scope": "Annex III", "source_url": "https://x",
         "note": ""}]


def tables(standards):
    return {"requirements": REQ, "annex3_areas": [], "request_deliverables": DEL, "standards": standards,
            "deadlines": DEAD}


def by_req(rows):
    return {r["req_id"]: r for r in rows}


def test_uncovered_when_no_work_item():
    cov = by_req(coverage_by_requirement(tables([]), date(2026, 10, 1)))
    assert cov["R09"]["status"] == "uncovered"
    assert cov["R09"]["n_deliverables"] == 1 and cov["R09"]["n_work_items"] == 0


def test_requirement_without_deliverable_is_uncovered_with_zero_deliverables():
    cov = by_req(coverage_by_requirement(tables([]), date(2026, 10, 1)))
    assert cov["R11"]["status"] == "uncovered" and cov["R11"]["n_deliverables"] == 0


def test_in_progress_published_and_harmonised():
    s = [
        std("A", "D01", "40", "2026-01-01"),
        std("B", "D02", "60", "2026-02-01", cited="true", ojeu="2026-05-01"),
    ]
    cov = by_req(coverage_by_requirement(tables(s), date(2026, 10, 1)))
    assert cov["R09"]["status"] == "in_progress" and cov["R09"]["n_at_enquiry_or_later"] == 1
    assert cov["R10"]["status"] == "harmonised"
    assert cov["R10"]["n_published"] == 1 and cov["R10"]["n_harmonised"] == 1


def test_published_but_not_cited_is_published():
    cov = by_req(coverage_by_requirement(tables([std("B", "D02", "60", "2026-02-01")]), date(2026, 10, 1)))
    assert cov["R10"]["status"] == "published"


def test_future_stage_is_ignored_at_as_of():
    s = [std("B", "D02", "60", "2026-12-01")]  # publication after as_of
    cov = by_req(coverage_by_requirement(tables(s), date(2026, 10, 1)))
    assert cov["R10"]["status"] == "uncovered" and cov["R10"]["n_work_items"] == 0


def test_citation_after_as_of_counts_as_published_only():
    s = [std("B", "D02", "60", "2026-02-01", cited="true", ojeu="2026-12-01")]
    cov = by_req(coverage_by_requirement(tables(s), date(2026, 10, 1)))
    assert cov["R10"]["status"] == "published"


def test_deliverable_with_empty_covers_does_not_break_or_count():
    s = [std("Q", "D09", "60", "2026-01-01")]
    cov = by_req(coverage_by_requirement(tables(s), date(2026, 10, 1)))
    assert all(r["n_work_items"] == 0 for r in cov.values())


def test_as_of_is_written_on_every_row():
    rows = coverage_by_requirement(tables([]), date(2026, 10, 1))
    assert {r["as_of"] for r in rows} == {"2026-10-01"}


def test_timeline_days_and_lateness():
    s = [std("A", "D01", "40", "2026-01-01", target="2026-06-01"),
         std("B", "D02", "50", "2026-01-01", target="2026-09-01")]
    rows = {r["wi_ref"]: r for r in timeline(tables(s), date(2026, 5, 1))}
    assert rows["A"]["deadline_id"] == "HR" and rows["A"]["days_target_to_deadline"] == 62
    assert rows["A"]["late_vs_deadline"] == "false"
    assert rows["B"]["days_target_to_deadline"] == -30 and rows["B"]["late_vs_deadline"] == "true"
    assert rows["A"]["stage_name"] == "enquiry"


def test_timeline_without_target_date_leaves_days_empty():
    rows = timeline(tables([std("A", "D01", "20", "2026-01-01")]), date(2026, 10, 1))
    assert rows[0]["days_target_to_deadline"] == "" and rows[0]["late_vs_deadline"] == "unknown"


def test_withdrawn_stage_95_does_not_count_as_published_or_enquiry():
    withdrawn = tables([std("prEN 1", "D01", "95", "2026-01-01")])
    rows = by_req(coverage_by_requirement(withdrawn, date(2026, 10, 1)))
    assert rows["R09"]["n_published"] == 0 and rows["R09"]["n_at_enquiry_or_later"] == 0
    assert rows["R09"]["status"] == "in_progress"


def test_timeline_marks_a_passed_target_of_an_unpublished_item():
    s = [std("A", "D01", "50", "2026-01-01", target="2026-07-29"),
         std("P", "D01", "60", "2026-07-22", target="2026-07-22")]
    rows = {r["wi_ref"]: r for r in timeline(tables(s), date(2026, 10, 23))}
    assert rows["A"]["late_vs_deadline"] == "target_passed" and rows["A"]["days_target_to_deadline"] == ""
    assert rows["P"]["late_vs_deadline"] == "false" and rows["P"]["days_target_to_deadline"] == 11


def test_timeline_gives_unknown_for_a_withdrawn_item():
    s = [std("W", "D01", "95", "2026-01-01", target="2026-07-29"),
         std("V", "D01", "95", "2026-01-01", target="2027-07-29")]
    rows = {r["wi_ref"]: r for r in timeline(tables(s), date(2026, 10, 23))}
    assert rows["W"]["late_vs_deadline"] == "unknown" and rows["W"]["days_target_to_deadline"] == ""
    assert rows["V"]["late_vs_deadline"] == "unknown" and rows["V"]["days_target_to_deadline"] == ""


def test_timeline_leaves_out_an_item_whose_stage_is_after_as_of():
    s = [std("A", "D01", "40", "2026-01-01", target="2026-06-01"),
         std("B", "D02", "60", "2026-12-01", target="2026-12-01")]  # stage reached after as_of
    rows = timeline(tables(s), date(2026, 10, 1))
    assert [r["wi_ref"] for r in rows] == ["A"]


# --- two statuses: on public sources alone, and counting the links drawn by this project ---------

def judged_tables(standards):
    """D09 is linked to Article 11 by this project's judgement, as in the real data."""
    t = tables(standards)
    t["request_deliverables"] = [dict(d, covers_req_ids="R11", link_basis="judged")
                                 if d["deliverable_id"] == "D09" else d for d in DEL]
    return t


def test_status_rests_on_public_sources_and_leaves_out_a_judged_deliverable():
    s = [std("Q", "D09", "60", "2026-07-22", cited="true", ojeu="2026-09-14")]
    r11 = by_req(coverage_by_requirement(judged_tables(s), date(2026, 10, 1)))["R11"]
    assert r11["status"] == "uncovered"
    assert r11["status_with_judged"] == "harmonised"


def test_n_judged_counts_the_work_items_reached_through_a_judged_link():
    s = [std("Q", "D09", "60", "2026-07-22", cited="true", ojeu="2026-09-14")]
    r11 = by_req(coverage_by_requirement(judged_tables(s), date(2026, 10, 1)))["R11"]
    assert r11["n_judged"] == 1 and r11["n_work_items"] == 1 and r11["n_harmonised"] == 1


def test_status_leaves_out_a_work_item_whose_own_link_is_judged():
    s = [dict(std("B", "D02", "40", "2026-01-01"), link_basis="judged")]
    r10 = by_req(coverage_by_requirement(tables(s), date(2026, 10, 1)))["R10"]
    assert (r10["status"], r10["status_with_judged"], r10["n_judged"]) == ("uncovered", "in_progress", 1)


def test_a_judged_work_item_beside_a_sourced_one_changes_no_status():
    s = [std("A", "D02", "20", "2026-01-01"),
         dict(std("B", "D02", "40", "2026-01-01"), link_basis="judged")]
    r10 = by_req(coverage_by_requirement(tables(s), date(2026, 10, 1)))["R10"]
    assert (r10["status"], r10["status_with_judged"]) == ("in_progress", "in_progress")
    assert r10["n_judged"] == 1 and r10["n_work_items"] == 2


def test_without_a_judged_link_the_two_statuses_agree():
    s = [std("B", "D02", "60", "2026-02-01", cited="true", ojeu="2026-05-01")]
    r10 = by_req(coverage_by_requirement(tables(s), date(2026, 10, 1)))["R10"]
    assert (r10["status"], r10["status_with_judged"], r10["n_judged"]) == ("harmonised", "harmonised", 0)


def test_coverage_file_has_the_two_status_columns_and_the_judged_count(tmp_path):
    import csv

    from aasm.derive import write_derived

    write_derived(tables([]), date(2026, 10, 1), tmp_path)
    with (tmp_path / "coverage_by_requirement.csv").open(newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert header[-4:] == ["n_harmonised", "n_judged", "status", "status_with_judged"]
