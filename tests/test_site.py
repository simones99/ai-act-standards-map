import shutil
from datetime import date

from aasm import __version__
from aasm.site import (
    anchor,
    build,
    by_target_date,
    deadline_label,
    report_url,
    requirement_when,
    stage_track,
    step_of,
    timeline_by_item,
    timeline_plot,
    watch_summary,
)


def _root(tmp_path, curated_ok):
    root = tmp_path / "repo"
    shutil.copytree(curated_ok, root / "data" / "curated")
    (root / "data" / "derived").mkdir(parents=True)
    (root / "data" / "derived" / "coverage_by_requirement.csv").write_text(
        "req_id,article,title,as_of,n_deliverables,n_work_items,n_at_enquiry_or_later,n_published,n_harmonised,"
        "n_judged,status,status_with_judged\n"
        "R09,9,Risk management system,2026-10-01,1,1,1,0,0,0,in_progress,in_progress\n"
        "R10,10,Data and data governance,2026-10-01,1,0,0,0,0,0,uncovered,uncovered\n")
    (root / "data" / "derived" / "timeline.csv").write_text(
        "wi_ref,title,deliverable_id,stage_code,stage_name,stage_date,target_pub_date,deadline_id,"
        "deadline_date,days_target_to_deadline,late_vs_deadline\n"
        "prEN 1,Risk management,D01,40,enquiry,2026-03-01,2026-12-01,HR_ANNEX3,2026-08-02,-121,true\n")
    (root / "docs").mkdir()
    (root / "docs" / "quality.md").write_text("# Quality note\n")
    return root


def test_build_writes_page_data_and_quality(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    out = build(root, tmp_path / "_site", date(2026, 10, 1))
    html = (out / "index.html").read_text()
    assert "<title>AI Act standards map</title>" in html
    assert "prEN 1" in html and "Risk management system" in html
    assert "2026-10-01" in html
    assert "CC BY 4.0" in html and "Source: Eurostat" in html
    assert "describes, it does not interpret" in html
    assert (out / "data" / "coverage_by_requirement.csv").exists()
    assert (out / "data" / "standards.csv").exists()
    assert (out / "quality.md").exists()
    assert str(root) not in html  # no local absolute paths leak into the page


def test_csv_text_is_html_escaped(tmp_path, curated_ok):
    import csv

    root = _root(tmp_path, curated_ok)
    path = root / "data" / "derived" / "timeline.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        columns = reader.fieldnames
    rows[0]["title"] = 'A<b>&"x"'
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    html = (build(root, tmp_path / "_site", date(2026, 10, 1)) / "index.html").read_text()
    assert "A&lt;b&gt;&amp;" in html
    assert "A<b>" not in html


def test_page_links_only_the_data_files_that_were_copied(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)  # no standards_history.csv, no adoption.csv
    html = (build(root, tmp_path / "_site", date(2026, 10, 1)) / "index.html").read_text()
    assert 'href="data/timeline.csv"' in html
    assert "standards_history.csv" not in html and "adoption.csv" not in html


def test_page_links_history_and_adoption_when_they_exist(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    (root / "data" / "derived" / "standards_history.csv").write_text("wi_ref\n")
    (root / "data" / "fetched").mkdir()
    (root / "data" / "fetched" / "adoption.csv").write_text("geo\n")
    html = (build(root, tmp_path / "_site", date(2026, 10, 1)) / "index.html").read_text()
    assert 'href="data/standards_history.csv"' in html and 'href="data/adoption.csv"' in html


def test_timeline_by_item_gives_one_row_per_work_item_with_its_days_to_each_deadline():
    tl = [{"wi_ref": "prEN 1", "title": "RM", "deadline_id": "HR_ANNEX1", "deadline_date": "2028-08-02",
           "days_target_to_deadline": "503", "late_vs_deadline": "false"},
          {"wi_ref": "prEN 1", "title": "RM", "deadline_id": "HR_ANNEX3", "deadline_date": "2027-12-02",
           "days_target_to_deadline": "259", "late_vs_deadline": "false"},
          {"wi_ref": "prEN 2", "title": "Data", "deadline_id": "HR_ANNEX3", "deadline_date": "2027-12-02",
           "days_target_to_deadline": "", "late_vs_deadline": "target_passed"}]
    deadlines, items = timeline_by_item(tl)
    assert deadlines == [{"deadline_id": "HR_ANNEX3", "deadline_date": "2027-12-02"},
                         {"deadline_id": "HR_ANNEX1", "deadline_date": "2028-08-02"}]  # earliest first
    assert [i["wi_ref"] for i in items] == ["prEN 1", "prEN 2"]
    assert items[0]["title"] == "RM"
    assert items[0]["days"] == {"HR_ANNEX3": {"days": "259", "late": "false"},
                                "HR_ANNEX1": {"days": "503", "late": "false"}}
    assert items[1]["days"] == {"HR_ANNEX3": {"days": "", "late": "target_passed"}}


def _two_deadline_root(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    path = root / "data" / "derived" / "timeline.csv"
    path.write_text(path.read_text() + "prEN 1,Risk management,D01,40,enquiry,2026-03-01,2026-12-01,"
                                       "HR_ANNEX1,2027-08-02,244,false\n")
    return root


def _restatus(root):
    """Write into the coverage file the statuses `aasm derive` gives for the curated tables as they are now:
    a test changes a curated table and leaves the other columns of the file as it wrote them."""
    import csv

    from aasm.curated import load_all
    from aasm.derive import COVERAGE_COLUMNS, coverage_by_requirement, write_csv

    path = root / "data" / "derived" / "coverage_by_requirement.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    derived = {r["req_id"]: r for r in coverage_by_requirement(load_all(root / "data" / "curated"),
                                                               date.fromisoformat(rows[0]["as_of"]))}
    for row in rows:
        for column in ("n_judged", "status", "status_with_judged"):
            row[column] = derived[row["req_id"]][column]
    write_csv(path, rows, COVERAGE_COLUMNS)


def _html(tmp_path, curated_ok, root=None):
    root = root or _root(tmp_path, curated_ok)
    _restatus(root)
    out = build(root, tmp_path / "_site", date(2026, 10, 1))
    return out, (out / "index.html").read_text()


def test_fonts_are_served_from_the_site_itself(tmp_path, curated_ok):
    out, html = _html(tmp_path, curated_ok)
    assert (out / "fonts" / "ibm-plex-sans-latin-400.woff2").stat().st_size > 10_000
    assert (out / "fonts" / "OFL.txt").exists()
    assert 'url("fonts/ibm-plex-sans-latin-400.woff2")' in html
    assert "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html



MANDATE = "https://ec.europa.eu/growth/tools-databases/enorm/mandate/593_en"
JUDGED = (f",,{MANDATE},sourced,Outside", f",R10,{MANDATE},judged,Outside")
NOTED = (f",,{MANDATE},sourced,Outside", f",R10,{MANDATE},sourced,Outside")


def _judged_root(tmp_path, curated_ok):
    """Article 10 is covered only through D09, whose link to it is recorded as judged."""
    root = _root(tmp_path, curated_ok)
    p = root / "data" / "curated" / "request_deliverables.csv"
    assert JUDGED[0] in p.read_text()
    p.write_text(p.read_text().replace(*JUDGED))
    return root


# --- the stage track: where each work item of a requirement stands -------------------------------

def _std(ref, code, **over):
    return {"wi_ref": ref, "title": ref, "deliverable_id": "D01", "stage_code": code,
            "stage_date": "2026-01-01", "ojeu_cited": "false", "ojeu_date": "", "source_url": "u", **over}


def test_step_of_orders_drafting_enquiry_approval_published_cited():
    as_of = "2026-10-01"
    assert [step_of(_std("a", c), as_of) for c in ("00", "20", "30", "40", "50", "60", "90")] == [
        0, 0, 0, 1, 2, 3, 3]
    assert step_of(_std("a", "60", ojeu_cited="true", ojeu_date="2026-09-30"), as_of) == 4


def test_step_of_ignores_a_citation_dated_after_as_of():
    assert step_of(_std("a", "60", ojeu_cited="true", ojeu_date="2026-10-02"), "2026-10-01") == 3


def test_stage_track_puts_each_work_item_of_a_requirement_at_its_step():
    cov = [{"req_id": "R15", "article": "15", "status": "in_progress", "as_of": "2026-10-01"}]
    dlv = [{"deliverable_id": "D06", "covers_req_ids": "R15", "note": ""},
           {"deliverable_id": "D08", "covers_req_ids": "R15|R09", "note": ""},
           {"deliverable_id": "D01", "covers_req_ids": "R09", "note": ""}]
    stds = [_std("prEN 4", "20", deliverable_id="D06"), _std("prEN 5", "20", deliverable_id="D06"),
            _std("prEN 8", "50", deliverable_id="D08"), _std("prEN 1", "40")]
    (row,) = stage_track(cov, dlv, stds)
    refs = [[i["wi_ref"] for i in step] for step in row["steps"]]
    assert refs == [["prEN 4", "prEN 5"], [], ["prEN 8"], [], []]
    assert row["article"] == "15" and row["judged"] is False
    assert not any(i["judged"] for step in row["steps"] for i in step)


def test_stage_track_flags_only_the_work_item_whose_own_link_is_judged():
    cov = [{"req_id": "R10", "article": "10", "status": "in_progress", "as_of": "2026-10-01"}]
    dlv = [{"deliverable_id": "D02", "covers_req_ids": "R10", "note": ""}]
    stds = [_std("prEN 84", "20", deliverable_id="D02", link_basis="sourced"),
            _std("prEN 83", "40", deliverable_id="D02", link_basis="judged")]
    (row,) = stage_track(cov, dlv, stds)
    assert row["judged"] is False  # the status would stand on the sourced work item alone
    marks = {i["wi_ref"]: i["judged"] for step in row["steps"] for i in step}
    assert marks == {"prEN 84": False, "prEN 83": True}


def test_stage_track_leaves_every_step_empty_for_a_requirement_with_no_work_item():
    cov = [{"req_id": "R08", "article": "8", "status": "uncovered", "as_of": "2026-10-01"}]
    (row,) = stage_track(cov, [], [_std("prEN 1", "40")])
    assert row["steps"] == [[], [], [], [], []]


def test_stage_track_ignores_a_stage_dated_after_as_of_as_the_coverage_does():
    cov = [{"req_id": "R09", "article": "9", "status": "uncovered", "as_of": "2026-10-01"}]
    dlv = [{"deliverable_id": "D01", "covers_req_ids": "R09", "note": ""}]
    (row,) = stage_track(cov, dlv, [_std("prEN 1", "40", stage_date="2026-10-02")])
    assert row["steps"] == [[], [], [], [], []]


def test_stage_track_does_not_take_a_note_on_a_deliverable_for_a_judgement():
    cov = [{"req_id": "R09", "article": "9", "status": "in_progress", "as_of": "2026-10-01"}]
    dlv = [{"deliverable_id": "D01", "covers_req_ids": "R09", "link_basis": "sourced",
            "note": "Due date moved."}]
    (row,) = stage_track(cov, dlv, [_std("prEN 1", "40")])
    assert row["judged"] is False and row["steps"][1][0]["judged"] is False


def test_stage_track_marks_only_the_work_items_of_the_judged_deliverable_when_a_sourced_one_covers_too():
    cov = [{"req_id": "R09", "article": "9", "status": "in_progress", "as_of": "2026-10-01"}]
    dlv = [{"deliverable_id": "D01", "covers_req_ids": "R09", "link_basis": "sourced", "note": ""},
           {"deliverable_id": "D09", "covers_req_ids": "R09", "link_basis": "judged", "note": "Read so."}]
    stds = [_std("prEN 1", "40"), _std("EN 9", "60", deliverable_id="D09")]
    (row,) = stage_track(cov, dlv, stds)
    marks = {i["wi_ref"]: i["judged"] for step in row["steps"] for i in step}
    assert marks == {"prEN 1": False, "EN 9": True}  # as `aasm derive` counts them
    assert row["judged"] is True  # the requirement is still reached through a judged deliverable


def test_stage_track_flags_a_requirement_reached_through_a_judged_deliverable():
    cov = [{"req_id": "R11", "article": "11", "status": "harmonised", "as_of": "2026-10-01"}]
    dlv = [{"deliverable_id": "D09", "covers_req_ids": "R11", "link_basis": "judged",
            "note": "The link is this project's."}]
    (row,) = stage_track(cov, dlv, [_std("EN 9", "60", deliverable_id="D09")])
    assert row["judged"] is True
    assert row["steps"][3][0]["judged"] is True  # every work item reached through that deliverable


def test_by_target_date_orders_work_items_by_target_and_puts_those_without_one_last():
    items = [_item("c", "2027-07-21"), _item("none", ""), _item("a", "2026-07-15"), _item("b", "2026-07-15")]
    assert [i["wi_ref"] for i in by_target_date(items)] == ["a", "b", "c", "none"]


# --- the timeline plot ---------------------------------------------------------------------------

def _item(ref, target, code="40", late="false"):
    return {"wi_ref": ref, "target_pub_date": target, "stage_code": code,
            "days": {"HR_ANNEX3": {"days": "", "late": late}}}


DEADLINES = [{"deadline_id": "HR_ANNEX3", "deadline_date": "2027-12-02"},
             {"deadline_id": "HR_ANNEX1", "deadline_date": "2028-08-02"}]


def test_timeline_plot_places_marks_left_to_right_by_target_date():
    plot = timeline_plot([_item("a", "2026-07-15"), _item("b", "2027-07-21")], DEADLINES, "2026-11-06")
    xs = [m["x"] for m in plot["marks"]]
    assert 0 < xs[0] < xs[1] < 100


def test_timeline_plot_keeps_a_work_item_without_target_date_off_the_axis():
    plot = timeline_plot([_item("a", "", late="unknown")], DEADLINES, "2026-11-06")
    assert plot["marks"] == [{"x": None, "state": "unknown"}]


def test_timeline_plot_tells_a_published_standard_from_a_forecast():
    items = [_item("a", "2026-07-22", code="60"), _item("b", "2027-03-01")]
    plot = timeline_plot(items, DEADLINES, "2026-11-06")
    assert [m["state"] for m in plot["marks"]] == ["published", "false"]


def test_timeline_plot_takes_the_state_of_a_forecast_from_the_first_deadline():
    plot = timeline_plot([_item("a", "2026-09-30", code="50", late="target_passed"),
                          _item("b", "2028-01-01", late="true")], DEADLINES, "2026-11-06")
    assert [m["state"] for m in plot["marks"]] == ["target_passed", "true"]


def test_timeline_plot_draws_a_rule_for_each_deadline_and_for_the_as_of_date():
    plot = timeline_plot([_item("a", "2026-07-15")], DEADLINES, "2026-11-06")
    assert [(r["kind"], r["date"]) for r in plot["rules"]] == [
        ("deadline", "2027-12-02"), ("deadline", "2028-08-02"), ("as_of", "2026-11-06")]
    xs = [r["x"] for r in plot["rules"]]
    assert xs[2] < xs[0] < xs[1]


def test_timeline_plot_turns_a_rule_label_towards_the_side_with_room():
    plot = timeline_plot([_item("a", "2026-07-15")], DEADLINES, "2026-08-01")
    assert [r["side"] for r in plot["rules"]] == ["left", "left", "right"]  # text sits left of a late rule


def test_timeline_plot_ticks_name_the_month_and_the_year():
    plot = timeline_plot([_item("a", "2026-07-15")], DEADLINES, "2026-11-06")
    assert [t["label"] for t in plot["ticks"]] == ["Oct 2026", "Jan 2027", "Apr 2027", "Jul 2027", "Oct 2027",
                                                  "Jan 2028", "Apr 2028", "Jul 2028"]
    assert [t["minor"] for t in plot["ticks"]] == [True, False] * 4  # a phone keeps January and July
    assert all(0 < t["x"] < 100 for t in plot["ticks"])


def test_deadline_label_is_in_plain_words_and_falls_back_to_the_id():
    assert deadline_label("HR_ANNEX3") == "Annex III application date"
    assert deadline_label("HR_ANNEX1") == "Annex I application date"
    assert deadline_label("OTHER") == "OTHER"


# --- the page ------------------------------------------------------------------------------------

def test_page_opens_with_one_status_cell_per_requirement_linked_to_its_row(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert html.count('class="sum-cell') == 2
    assert '<a class="sum-cell" href="#art-9"' in html and ('<b>Art. 9</b> <span class="t">Risk management'
            ' system</span> <span>in progress</span>') in html
    assert '<b>Art. 10</b> <span class="t">Data and data governance</span> <span>uncovered</span>' in html
    assert 'id="art-9"' in html and 'id="art-10"' in html
    assert ("Of 2 requirements, by public sources: 0 harmonised"
            " · 0 published · 1 in progress · 1 uncovered.") in html
    assert "Through a judged link" not in html


def test_a_judged_mapping_is_not_drawn_or_counted_as_a_sourced_one(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _judged_root(tmp_path, curated_ok))
    assert '<a class="sum-cell judged" href="#art-10"' in html
    assert ('<b>Art. 10</b> <span class="t">Data and data governance</span> <span>uncovered</span>'
            ' <span class="judge">a judged link, no work item yet</span>') in html
    assert '<a class="sum-cell" href="#art-9"' in html  # no mark on a sourced mapping
    assert "1 in progress · 1 uncovered." in html and "Through a judged link" not in html


def test_the_judgement_is_explained_once_under_the_track_and_pointed_to_from_above(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _judged_root(tmp_path, curated_ok))
    assert html.count("A judgement, not a sourced fact.") == 1
    assert "Article 10, through deliverable D09 (Quality management system for providers)." in html
    assert "Outside the Articles 8-15 perimeter (Article 17)." in html
    assert html.count('href="#judged"') == 3 and html.count('id="judged"') == 1  # top, row, How to read


def _standard(root, old, new):
    p = root / "data" / "curated" / "standards.csv"
    assert old in p.read_text()
    p.write_text(p.read_text().replace(old, new))
    return root


def test_a_work_item_linked_by_judgement_is_marked_on_its_own_mark(tmp_path, curated_ok):
    root = _standard(_root(tmp_path, curated_ok), ",sourced,", ",judged,Risk is read as data governance.")
    _, html = _html(tmp_path, curated_ok, root)
    assert '<span class="wi judged"><a href="https://standards.cencenelec.eu/x/1">prEN 1</a>' in html
    # the only work item is judged: what public sources support comes first, the judgement second
    assert '<a class="sum-cell judged" href="#art-9"' in html
    assert ('<b>Art. 9</b> <span class="t">Risk management system</span> <span>uncovered</span>'
            ' <span class="judge">in progress by a judged link</span>') in html
    assert "prEN 1, under deliverable D01 (Risk management system for AI systems)." in html
    assert "Risk is read as data governance." in html
    assert "work item linked by this project" in html  # the key says what the dashed mark means


def test_no_dashed_mark_in_the_key_without_a_judged_link(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "work item linked by a public source" in html and "step not reached" in html
    assert "work item linked by this project" not in html


def test_a_cited_standard_shows_the_date_of_its_citation(tmp_path, curated_ok):
    root = _standard(_root(tmp_path, curated_ok), ",40,2026-03-01,2026-12-01,false,,",
                     ",60,2026-03-01,2026-12-01,true,2026-09-01,")
    _, html = _html(tmp_path, curated_ok, root)
    assert '<span class="sub">cited 2026-09-01</span>' in html


def test_a_requirement_with_no_deliverable_says_so_beside_its_status(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    p = root / "data" / "derived" / "coverage_by_requirement.csv"
    p.write_text(p.read_text().replace("2026-10-01,1,0,0,0,0,0,uncovered",
                                       "2026-10-01,0,0,0,0,0,0,uncovered"))
    _, html = _html(tmp_path, curated_ok, root)
    assert html.count("no deliverable in the request") == 2  # in the strip and in the track
    assert '<b>Art. 9</b> <span class="t">Risk management system</span> <span>in progress</span>' in html


def test_empty_steps_say_not_reached_to_a_screen_reader(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert html.count('<span class="vh">not reached</span>') == 9  # 2 requirements x 5 steps, one mark


def test_articles_link_to_their_source_in_the_track_and_in_the_full_table(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert html.count('<a href="https://eur-lex.europa.eu/eli/reg/2024/1689/oj">Article 9</a>') == 2


def test_each_application_date_links_to_its_source_and_carries_its_curated_note(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    url = "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"
    assert (f'<dt><a href="{url}">Annex III application date</a> (2026-08-02)</dt>'
            '<dd>Annex III high-risk systems</dd>') in html
    assert '<details class="note"><summary>How these dates were set</summary>' in html
    assert "<b>Annex III application date.</b> Article 113" in html


def test_timeline_table_names_the_article_and_the_step_of_each_work_item(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<span class="sub"><a href="#art-9">Art. 9</a></span>' in html
    assert html.count(">Enquiry</td>") == 1 and "Enquiry<span class=\"sub\">stage 40 enquiry</span>" in html
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    assert len(re.findall(r"Days from target to the\s+Annex III application date", text)) == 2  # one wording


def test_sources_checked_is_a_range_when_work_items_were_checked_on_several_days(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    p = root / "data" / "curated" / "standards.csv"
    p.write_text(p.read_text() + "prEN 2,Data,D01,20,2026-03-01,,false,,https://standards.cencenelec.eu/x/2,"
                                 "2026-09-15,sourced,\n")
    _, html = _html(tmp_path, curated_ok, root)
    assert "<dt>Sources checked</dt><dd>2026-09-15 to 2026-10-01</dd>" in html


def test_footer_is_a_page_landmark_outside_main(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert html.index("</main>") < html.index("<footer>")
    assert "<header>" not in html  # the title block is content, inside main, where the skip link lands


def test_a_note_on_a_deliverable_alone_does_not_make_its_requirement_a_judged_link(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    p = root / "data" / "curated" / "request_deliverables.csv"
    assert NOTED[0] in p.read_text()
    p.write_text(p.read_text().replace(*NOTED))  # D09 covers Article 10 and has a note, but is sourced
    _, html = _html(tmp_path, curated_ok, root)
    assert "A judgement, not a sourced fact." not in html and "judged link" not in html


def test_no_judgement_notice_without_a_judged_mapping(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "A judgement, not a sourced fact." not in html and "judged link" not in html


def test_page_defines_the_four_statuses(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    for status in ("uncovered", "in progress", "published", "harmonised"):
        assert f"<dt>{status}</dt>" in html


def test_page_draws_no_chart_with_a_script_and_loads_none_from_elsewhere(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    # one inline script, last in the body, that only adds to a page already complete without it
    assert html.count("<script") == 1 and "<script src" not in html and "cdn.jsdelivr.net" not in html
    script = html.index("<script")
    assert html.index('class="pt"') < script and html.index("</footer>") < script


def test_stage_track_is_a_table_with_one_column_per_step(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<table class="track">' in html
    for step in ("Drafting", "Enquiry", "Approval", "Published", "Cited in the Official Journal"):
        assert f'<th scope="col">{step} <span class="sub">' in html


def test_timeline_has_a_plot_with_a_short_table_beside_it_and_full_tables_folded(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert html.count('<div class="fig">') == 1 and html.count("<details>") == 2
    assert html.count('class="pt"') == 1 and html.count('class="mk mk-true"') == 2  # plot, key
    assert "--row: 46px;" in html


def test_every_work_item_links_to_its_public_page(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    # in the track, beside the plot, in the full table
    assert html.count('<a href="https://standards.cencenelec.eu/x/1">prEN 1</a>') == 3


def test_page_shows_a_work_item_once_with_a_column_per_deadline(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _two_deadline_root(tmp_path, curated_ok))
    assert html.count(">prEN 1</a>") == 3
    assert ">-121<" in html and ">244<" in html
    assert "Annex III application date" in html and "Annex I application date" in html


def test_page_names_deadlines_in_plain_words_never_by_their_id(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "HR_ANNEX" not in html
    assert "Annex III application date" in html


def test_timeline_key_names_only_the_states_drawn(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "target after the Annex III application date" in html
    assert "target date passed, not published" not in html


def test_a_work_item_under_a_deliverable_that_covers_no_requirement_is_flagged(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    path = root / "data" / "derived" / "timeline.csv"
    path.write_text(path.read_text() + "prEN 9,Quality,D09,20,preparatory,2026-03-01,2026-12-01,"
                                       "HR_ANNEX3,2026-08-02,-121,true\n")
    _, html = _html(tmp_path, curated_ok, root)
    assert html.count("no Article 8–15 requirement") == 2  # beside the plot and in the full table


def test_header_tells_the_data_date_from_the_source_check_and_the_build(tmp_path, curated_ok):
    out = build(_root(tmp_path, curated_ok), tmp_path / "_site", date(2026, 10, 5))
    html = (out / "index.html").read_text()
    assert "<dt>Data as of</dt><dd>2026-10-01</dd>" in html
    assert "<dt>Sources checked</dt><dd>2026-10-01</dd>" in html
    assert f"<dt>Version</dt><dd>{__version__}, built 2026-10-05</dd>" in html


def test_page_says_how_to_cite_it(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert (f"Cite as: Mezzabotta, S. (2026). AI Act standards map, version {__version__}, "
            "data as of 2026-10-01.") in html


def test_page_can_be_reached_by_keyboard_and_printed(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<a class="skip" href="#main">' in html and '<nav class="bar"' in html
    assert "@media print" in html and "prefers-reduced-motion" in html
    assert html.count("<caption") == 4


# --- step 1: a judged link is marked wherever it is shown ----------------------------------------

def _judged_item_root(tmp_path, curated_ok):
    """prEN 1 is linked to its deliverable by this project's judgement."""
    return _standard(_root(tmp_path, curated_ok), ",sourced,", ",judged,Risk is read as data governance.")


def test_a_judged_work_item_says_so_to_a_screen_reader_in_the_track(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _judged_item_root(tmp_path, curated_ok))
    assert ('<span class="wi judged"><a href="https://standards.cencenelec.eu/x/1">prEN 1</a>'
            '<span class="vh"> (judged link)</span>') in html


def test_a_judged_work_item_is_ringed_in_the_plot_and_named_so_in_both_timeline_tables(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _judged_item_root(tmp_path, curated_ok))
    assert html.count('class="pt judged"') == 1
    assert html.count("(judged link)</span>") >= 2  # beside the plot and in the full table
    assert "linked by this project's judgement" in html  # the timeline key names the ring


def test_a_work_item_under_a_judged_deliverable_is_judged_in_the_timeline(tmp_path, curated_ok):
    root = _judged_root(tmp_path, curated_ok)
    path = root / "data" / "derived" / "timeline.csv"
    path.write_text(path.read_text() + "prEN 9,Quality,D09,20,preparatory,2026-03-01,2026-12-01,"
                                       "HR_ANNEX3,2026-08-02,-121,true\n")
    _, html = _html(tmp_path, curated_ok, root)
    assert html.count('class="pt judged"') == 1  # prEN 9 only; prEN 1 is sourced


def test_no_ring_in_the_timeline_without_a_judged_work_item(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert 'class="pt judged"' not in html and 'class="pt"' in html


# --- step 2: what public sources support comes first; the judgement is said beside it ------------

def test_a_judged_status_is_counted_apart_and_pointed_to_from_its_row(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _judged_item_root(tmp_path, curated_ok))
    assert ("Of 2 requirements, by public sources: 0 harmonised"
            " · 0 published · 0 in progress · 2 uncovered.") in html
    assert "Through a judged link: Art. 9 in progress." in html
    assert ('<td class="status status-neutral">uncovered<span class="sub judge"><a'
            ' href="#judged">in progress by a judged link</a>'
            '<span class="d">prEN 1, target <span class="nowrap">2026-12-01</span></span></span>') in html


def test_page_defines_harmonised_as_the_last_step_and_the_judged_annotation(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _judged_item_root(tmp_path, curated_ok))
    assert "the last step of the track, Cited in the Official Journal" in html
    assert "<dt>by a judged link</dt>" in html
    _, plain = _html(tmp_path / "plain", curated_ok)
    assert "<dt>by a judged link</dt>" not in plain


def test_step_headers_say_which_stage_codes_they_hold(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<th scope="col">Enquiry <span class="sub">stage 40, vote and comments</span></th>' in html


def test_abbreviations_are_spelled_out(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<abbr title="draft European Standard">prEN</abbr>' in html
    assert '<abbr title="Joint Technical Committee 21, Artificial Intelligence">JTC 21</abbr>' in html


# --- step 3: a status colour never means two things; a passed target still says how late ---------

def _css_vars(html):
    import re
    root = re.search(r":root \{(.*?)\}", html, re.S).group(1)
    return dict(re.findall(r"--([\w-]+):\s*([^;]+);", root))


def test_timeline_colours_are_not_status_colours(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    v = _css_vars(html)
    resolve = lambda x: v.get(x[6:-1], x) if x.startswith("var(") else x  # noqa: E731
    status = {v[k] for k in ("uncovered", "in_progress", "published", "harmonised")}
    assert resolve(v["late"]) not in status and resolve(v["passed"]) not in status


def _passed_root(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    path = root / "data" / "derived" / "timeline.csv"
    path.write_text(path.read_text().replace("2026-12-01,HR_ANNEX3,2026-08-02,-121,true",
                                             "2026-09-01,HR_ANNEX3,2026-08-02,,target_passed"))
    return root


def test_a_passed_target_says_how_many_days_ago_it_passed(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _passed_root(tmp_path, curated_ok))
    assert ('<td class="num passed" data-sort="-100030">target passed'
            '<span class="sub">30 days ago</span></td>') in html


def test_a_published_work_item_says_so_beside_its_days(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    path = root / "data" / "derived" / "timeline.csv"
    path.write_text(path.read_text().replace(",40,enquiry,", ",60,publication,"))
    _, html = _html(tmp_path, curated_ok, root)
    assert '<td class="num late">-121<span class="sub">published</span></td>' in html


# --- step 4: each requirement says when, beside its status ---------------------------------------

def _when_row(*items):
    steps = [[] for _ in range(5)]
    for step, extra in items:
        steps[step].append({"wi_ref": "prEN 1", "judged": False, "target_pub_date": "", "stage_date": "",
                            "ojeu_date": "", **extra})
    return {"steps": steps}


DL = {"deadline_date": "2027-12-02", "label": "Annex III application date"}


def test_requirement_when_gives_the_earliest_target_of_a_draft_and_its_days_to_the_first_date():
    row = _when_row((1, {"target_pub_date": "2027-07-01", "wi_ref": "prEN 2"}),
                    (1, {"target_pub_date": "2027-03-18"}))
    assert requirement_when(row, "2026-11-06", DL) == {
        "short": "target 2027-03-18", "detail": "259 days before the Annex III application date",
        "wi_ref": "prEN 1"}


def test_requirement_when_says_a_target_has_passed_or_falls_after_the_date():
    passed = requirement_when(_when_row((2, {"target_pub_date": "2026-09-30"})), "2026-11-06", DL)
    after = requirement_when(_when_row((0, {"target_pub_date": "2028-01-01"})), "2026-11-06", DL)
    assert passed["short"] == "target 2026-09-30, passed" and passed["detail"] == "not published"
    assert after["detail"] == "30 days after the Annex III application date"


def test_requirement_when_dates_a_publication_and_a_citation_and_skips_judged_items():
    assert requirement_when(_when_row((3, {"stage_date": "2026-07-22"})), "2026-11-06", DL)["short"] == (
        "published 2026-07-22")
    assert requirement_when(_when_row((4, {"ojeu_date": "2026-10-14"})), "2026-11-06", DL)["short"] == (
        "cited 2026-10-14")
    judged = _when_row((4, {"ojeu_date": "2026-10-14", "judged": True}))
    assert requirement_when(judged, "2026-11-06", DL) is None
    assert requirement_when(_when_row((1, {})), "2026-11-06", DL)["short"] == "no target date"


def test_strip_and_track_say_when_each_requirement_may_be_covered(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<span class="when">target <span class="nowrap">2026-12-01</span></span>' in html  # the strip
    # the track
    assert ('target <span class="nowrap">2026-12-01</span></a>'
            '<span class="d">121 days after the Annex III application date') in html


def test_judgements_are_one_line_each_with_the_reason_folded(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _judged_root(tmp_path, curated_ok))
    assert ('<details class="note"><summary>Article 10, through deliverable D09 '
            '(Quality management system for providers).</summary>') in html


def test_licence_is_stated_once_and_no_style_is_inline(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "<dt>Licence</dt>" not in html and "CC BY 4.0" in html
    assert 'style="margin' not in html


def test_the_strip_can_be_pointed_to_and_abbreviations_never_break_at_their_hyphen(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<div class="sum" id="summary">' in html
    assert "abbr { white-space: nowrap;" in html


# --- step 5: landing on a row keeps its headers in view; the two views point to each other --------

def test_anchor_turns_a_work_item_reference_into_a_fragment():
    assert anchor("prEN 18229-1") == "wi-prEN-18229-1"
    assert anchor("EN 18286:2026") == "wi-EN-18286-2026"


def test_timeline_rows_can_be_landed_on_and_the_track_points_to_them(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<tr id="wi-prEN-1">' in html
    assert ('<span class="sub when"><a href="#wi-prEN-1">target <span class="nowrap">2026-12-01</span></a>'
            '<span class="d">121 days after') in html


def test_a_row_landed_on_is_outlined_and_lands_below_its_headers(tmp_path, curated_ok):
    import re
    _, html = _html(tmp_path, curated_ok)
    assert "tr:target > * { box-shadow: inset 0 2px var(--ink)" in html
    margin = re.search(r"\.track tbody tr \{ scroll-margin-top: (\d+)px", html).group(1)
    assert int(margin) >= 110  # the bar and the two-line step headers


def test_the_bar_marks_the_section_in_view_and_each_section_leads_back_to_the_summary(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "IntersectionObserver" in html and ".bar a[aria-current]" in html
    assert html.count('<a class="back" href="#summary">Back to the summary</a>') >= 2


# --- step 6: narrow screens -----------------------------------------------------------------------

def test_scroll_hint_shows_only_where_the_track_is_wider_than_the_screen(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    narrow = html.split("@media (max-width: 868px)")[1].split("@media")[0]
    assert "p.scroll-hint { display: block;" in narrow
    assert "scrollWidth" in html  # the script also drops the hint, and the tab stop, where nothing scrolls


def test_on_a_phone_the_bar_stays_and_the_track_keeps_the_requirement_titles(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert ".bar { position: static; }" not in html
    assert ".track tbody th .sub { display: none; }" not in html


def test_the_plot_label_does_not_say_where_the_table_is(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "The table next to it gives the same data" not in html
    assert "A table with each work item gives the same data." in html


# --- step 7: how to read the page, by the questions people bring to it ---------------------------

def test_page_answers_how_to_read_it_by_task(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    section = html.split('<section id="read">')[1].split("</section>")[0]
    assert "<h2>How to read this page</h2>" in section
    assert section.count("<h3>") == 4  # no question on the dashed mark where none is drawn
    _, judged = _html(tmp_path / "j", curated_ok, _judged_root(tmp_path / "j", curated_ok))
    assert judged.split('<section id="read">')[1].split("</section>")[0].count("<h3>") == 5
    assert "Does an article have a harmonised standard?" in section
    assert "to the extent that those standards cover those requirements" in section  # Article 40(1), quoted
    assert ('href="https://github.com/simones99/ai-act-standar'
            'ds-map/blob/main/docs/methodology.md#stage-codes"') in section
    assert '<a href="#read">How to read</a>' in html  # in the bar
    assert html.index('id="tl"') < html.index('id="read"') < html.index('id="data"')


# --- step 8: a wrong or stale fact can be seen and reported ---------------------------------------

def test_report_url_opens_a_review_issue_that_names_the_row_and_its_source():
    url = report_url("Article 9", "https://eur-lex.europa.eu/x?a=1&b=2")
    assert url.startswith("https://github.com/simones99/ai-act-standards-map/issues/new?")
    assert "labels=needs-review" in url and "title=Correction%3A+Article+9" in url
    assert "https%3A%2F%2Feur-lex.europa.eu%2Fx%3Fa%3D1%26b%3D2" in url


def test_every_row_of_the_full_tables_can_be_reported(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert html.count(">Report</a></td>") == 3  # 2 requirements, 1 work item
    assert "title=Correction%3A+prEN+1" in html and ">Report a correction</a>" in html


def test_a_stale_page_says_so_at_build_and_a_fresh_one_keeps_the_notice_hidden(tmp_path, curated_ok):
    out = build(_root(tmp_path, curated_ok), tmp_path / "_site", date(2026, 10, 20))
    stale = (out / "index.html").read_text()
    assert '<p class="stale" id="stale" data-as-of="2026-10-01">' in stale and "<span>19</span> days" in stale
    out = build(_root(tmp_path / "fresh", curated_ok), tmp_path / "_site2", date(2026, 10, 5))
    assert '<p class="stale" id="stale" data-as-of="2026-10-01" hidden>' in (out / "index.html").read_text()


def test_watch_summary_names_the_pages_not_reached_at_the_last_check():
    state = {"prEN 1": {"checked_at": "2026-10-01"}, "prEN 2": {"checked_at": "2026-09-24"}}
    stds = [{"wi_ref": "prEN 1"}, {"wi_ref": "prEN 2"}, {"wi_ref": "prEN 3"}]
    assert watch_summary(state, stds) == {"n": 3, "latest": "2026-10-01", "missing": ["prEN 2", "prEN 3"]}
    assert watch_summary({}, stds) is None


def test_page_says_how_many_pages_answered_the_last_check(tmp_path, curated_ok):
    import json
    root = _root(tmp_path, curated_ok)
    (root / "data" / "watch_state.json").write_text(json.dumps({"prEN 1": {"checked_at": "2026-10-01"}}))
    _, html = _html(tmp_path, curated_ok, root)
    assert "<dt>Pages watched</dt><dd>1, all reached on 2026-10-01</dd>" in html


def test_a_step_reached_in_the_last_week_is_marked_new(tmp_path, curated_ok):
    root = _standard(_root(tmp_path, curated_ok), ",40,2026-03-01,", ",40,2026-09-28,")
    _, html = _html(tmp_path, curated_ok, root)
    assert '<span class="sub new">new this week</span>' in html  # the track
    assert '<span class="new">a step reached this week</span>' in html  # the strip
    _, old = _html(tmp_path / "old", curated_ok)
    assert "this week" not in old


# --- step 9: shortcuts for the people who come back -----------------------------------------------

def test_each_view_links_its_own_table_for_download(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert html.count('href="data/coverage_by_requirement.csv"') == 2  # under the track, in Data and method
    assert html.count('href="data/timeline.csv"') == 2


def test_each_requirement_row_has_a_link_to_itself_that_can_be_copied(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<a class="perma" href="#art-9" aria-label="Link to the Article 9 row">link</a>' in html
    assert "navigator.clipboard" in html and 'aria-live="polite"' in html


def test_full_tables_can_be_sorted_by_any_column_but_the_correction_link(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "aria-sort" in html and "table.full" in html
    assert html.count("<th scope=\"col\" data-nosort>Correction</th>") == 2


def test_uncovered_is_defined_on_public_sources(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "<dt>uncovered</dt><dd>No work item is linked to the requirement by a public source.</dd>" in html


def test_where_the_track_fits_its_step_headers_stay_under_the_bar(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    wide = html.split("@media (min-width: 869px)")[1].split("@media")[0]
    assert ".track-wrap { overflow: visible; }" in wide
    assert ".track thead th { position: sticky; top: var(--bar);" in wide
    assert 'class="table-wrap track-wrap"' in html


def test_on_a_phone_the_last_section_link_is_short_enough_for_the_bar(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<a href="#data">Data<span class="long"> and method</span></a>' in html
    assert ".bar .long { display: none; }" in html.split("@media (max-width: 600px)")[1]


def test_no_attribute_written_by_the_template_is_escaped_into_text(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "&#34;" not in html
    assert '<span class="minor" style="left:' in html


def test_back_at_the_top_no_section_is_marked_current(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert 'seen.observe(document.querySelector(".top"))' in html  # the lede clears the mark


# --- critique 2, P1: the plot cannot drift from the table beside it -------------------------------

def test_the_side_table_never_wraps_so_its_rows_keep_the_plot_row_height(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert ".fig td { white-space: nowrap; }" in html
    assert ".fig { display: grid; grid-template-columns: minmax(0, 1fr) auto;" in html
    assert "Days from target to the<br>Annex III application date" in html  # two short lines


def test_the_side_table_names_the_last_step_short(tmp_path, curated_ok):
    root = _standard(_root(tmp_path, curated_ok), ",40,2026-03-01,2026-12-01,false,,",
                     ",60,2026-03-01,2026-12-01,true,2026-09-01,")
    _, html = _html(tmp_path, curated_ok, root)
    assert "<td>Cited in the OJ</td>" in html


def test_the_script_keeps_plot_rows_level_with_table_rows_and_marks_the_row_landed_on(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "plot-row" in html.split("<script>")[1] and "offsetHeight" in html
    assert ".plot-row.on" in html and "hashchange" in html


# --- critique 2, P1: a judged status names the standard it rests on --------------------------------

def _cited_judged_root(tmp_path, curated_ok):
    """Article 9's only work item is cited in the Official Journal, through a judged link."""
    root = _standard(_root(tmp_path, curated_ok), ",40,2026-03-01,2026-12-01,false,,",
                     ",60,2026-03-01,2026-12-01,true,2026-09-01,")
    cov = root / "data" / "derived" / "coverage_by_requirement.csv"
    cov.write_text(cov.read_text().replace("2026-10-01,1,1,1,0,0,0,in_progress,in_progress",
                                           "2026-10-01,1,1,1,1,1,0,harmonised,harmonised"))
    return _standard(root, ",sourced,", ",judged,Read as risk management.")


def test_a_judged_status_names_its_standard_and_date_in_the_strip_and_the_track(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _cited_judged_root(tmp_path, curated_ok))
    assert ('<span class="judge">harmonised by a judged link</span> '
            '<span class="when">prEN 1, cited <span class="nowrap">2026-09-01</span></span>') in html
    assert '<span class="d">prEN 1, cited <span class="nowrap">2026-09-01</span></span>' in html


def test_a_judged_link_that_changes_nothing_is_said_with_also(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    p = root / "data" / "curated" / "standards.csv"
    p.write_text(p.read_text() + "prEN 2,Data,D01,20,2026-03-01,2027-01-01,false,,"
                                 "https://standards.cencenelec.eu/x/2,2026-10-01,judged,Read as risk.\n")
    _, html = _html(tmp_path, curated_ok, root)
    assert '<span class="judge">in progress also by a judged link</span>' in html


def test_the_full_table_says_when_its_counts_include_a_judged_link(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _cited_judged_root(tmp_path, curated_ok))
    assert '<td>Risk management system<span class="sub">counts include a judged link</span></td>' in html


# --- critique 2, P2: focus, the phone, the words ---------------------------------------------------

def test_a_focused_link_in_the_track_is_never_under_the_sticky_step_headers(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    wide = html.split("@media (min-width: 869px)")[1].split("@media")[0]
    assert ".track :is(a, button) { scroll-margin-top: 70px; }" in wide


def test_the_status_comes_right_after_the_requirement(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<th scope="col">Requirement</th><th scope="col">Status</th><th scope="col">Drafting' in html
    row = html.split('<tr id="art-9">')[1].split("</tr>")[0]
    assert row.index('class="status') < row.index('class="step')


def test_the_track_terms_are_defined_above_it_and_the_lede_spells_out_the_committee(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    key = html.split('<dl class="defs status-key">')[1].split("</dl>")[0]
    assert "<dt>work item</dt>" in key and "<dt>deliverable</dt>" in key
    lede = html.split('<div class="lede">')[1].split("</div>")[0]
    import re
    text = re.sub(r"<[^>]+>", "", lede)  # the words in the text, not only in a title
    assert "Joint Technical Committee 21 on artificial intelligence" in text
    notes = html.split('<div class="sum-notes">')[1].split("</div>")[0]
    assert '<a href="#read">How to read this page</a>' in notes


def test_faq_lines_stay_short_and_headings_are_balanced(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert ".faq { max-width: 36em; }" in html
    assert "h2, h3 { text-wrap: balance; }" in html


# --- critique 2, extras: sorting that reads, an honest copy link, a plainer stale notice ------------

def test_status_sorts_in_track_order_and_a_passed_target_sorts_first(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _passed_root(tmp_path, curated_ok))
    assert '<td class="status status-uncovered" data-sort="0">' in html
    assert '<td class="num passed" data-sort="-100030">' in html  # 30 days ago: before every count
    assert "dataset.sort" in html


def test_the_default_order_of_each_full_table_is_marked_sorted(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '<th scope="col" aria-sort="ascending">Article</th>' in html
    assert '<th scope="col" aria-sort="ascending">Target publication</th>' in html


def test_the_row_link_says_it_copies_and_a_landed_row_is_framed_in_every_cell(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert '"copy link"' in html
    assert "tr:target > * { box-shadow:" in html


def test_the_stale_notice_says_what_it_means_for_the_data(tmp_path, curated_ok):
    out = build(_root(tmp_path, curated_ok), tmp_path / "_site", date(2026, 10, 20))
    html = (out / "index.html").read_text()
    assert "a step reached since then is not shown yet" in html


def test_minor_tick_names_hide_by_the_width_of_the_plot_not_of_the_screen(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert ".plot { container-type: inline-size; }" in html
    assert "@container (max-width: 640px) { .plot-axis span.minor { display: none; } }" in html


def test_the_date_under_a_status_note_sits_on_its_own_line(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert ".status .d { display: block; }" in html
    assert ".perma { font-size: .75rem; font-weight: 400;" in html


# --- a status that a judgement would change is drawn in neutral ink, so neither reads as the verdict ----

def test_a_status_a_judgement_would_change_is_neutral_in_strip_track_and_full_table(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _judged_item_root(tmp_path, curated_ok))
    assert '<a class="sum-cell judged" href="#art-9" style="--c: var(--neutral)">' in html
    assert html.count('<td class="status status-neutral"') == 2  # the track and the full table
    v = _css_vars(html)
    assert v["neutral"] == "var(--muted)" and ".status-neutral { color: var(--neutral); }" in html
    assert "drawn in grey" in html  # the key says why


def test_a_judged_link_that_changes_no_status_keeps_the_status_colour(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok, _judged_root(tmp_path, curated_ok))
    assert '<a class="sum-cell judged" href="#art-10" style="--c: var(--uncovered)">' in html
    assert "status-neutral" not in html.split("<body>")[1]


def test_strip_styles_reach_only_its_own_lines_not_a_date_kept_inside_one(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert ".sum-cell > span { display: block;" in html and ".sum-cell span {" not in html


def test_the_as_of_date_in_running_text_never_breaks(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert 'the furthest step it has reached on <span class="nowrap">2026-10-01</span>.' in html



# --- each step is defined in the words of a public CEN page, and links to it ------------------------

BOSS = "https://boss.cen.eu/developingdeliverables/pages/en/pages/"


def test_each_step_is_defined_from_a_public_cen_page_that_it_links(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    steps = html.split("<h3>What do the five steps mean?</h3>")[1].split("</dl>")[0]
    for page in ("entoenq/", "enq/", "fv/", "finalization/"):
        assert f'href="{BOSS}{page}"' in steps
    assert "vote and comment within 12 weeks" in steps
    assert "confirm that the draft was made available for public comment" in steps
    assert "Formal Vote" in steps and "date of availability" in steps
    assert "for public comment." not in steps.split("<dt>Enquiry</dt>")[1].split("</dd>")[0][:60]
    assert "committee draft" not in steps  # no source read says so


# --- the two statuses come from the coverage file: one rule, in derive -----------------------------

def test_the_page_shows_the_two_statuses_of_the_coverage_file_without_recomputing_them(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    p = root / "data" / "derived" / "coverage_by_requirement.csv"
    assert "0,uncovered,uncovered" in p.read_text()
    p.write_text(p.read_text().replace("0,uncovered,uncovered", "0,published,harmonised"))
    html = (build(root, tmp_path / "_site", date(2026, 10, 1)) / "index.html").read_text()
    assert '<b>Art. 10</b> <span class="t">Data and data governance</span> <span>published</span>' in html
    assert "Through a judged link: Art. 10 harmonised." in html


def test_a_sourced_work_item_keeps_its_mark_beside_a_judged_deliverable(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    p = root / "data" / "curated" / "request_deliverables.csv"
    assert JUDGED[0] in p.read_text()
    p.write_text(p.read_text().replace(JUDGED[0], f",R09,{MANDATE},judged,Outside"))
    p = root / "data" / "curated" / "standards.csv"
    p.write_text(p.read_text() + "EN 9,Quality management,D09,60,2026-03-01,2026-03-01,false,,"
                                 "https://standards.cencenelec.eu/x/9,2026-10-01,sourced,\n")
    _, html = _html(tmp_path, curated_ok, root)
    assert '<span class="wi"><a href="https://standards.cencenelec.eu/x/1">prEN 1</a>' in html
    assert '<span class="wi judged"><a href="https://standards.cencenelec.eu/x/9">EN 9</a>' in html
    assert ('<b>Art. 9</b> <span class="t">Risk management system</span> <span>in progress</span>'
            ' <span class="judge">published by a judged link</span>') in html
