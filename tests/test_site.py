import json
import shutil
from datetime import date

from aasm.site import build, timeline_by_item, vega_specs


def _root(tmp_path, curated_ok):
    root = tmp_path / "repo"
    shutil.copytree(curated_ok, root / "data" / "curated")
    (root / "data" / "derived").mkdir(parents=True)
    (root / "data" / "derived" / "coverage_by_requirement.csv").write_text(
        "req_id,article,title,as_of,n_deliverables,n_work_items,n_at_enquiry_or_later,n_published,n_harmonised,status\n"
        "R09,9,Risk management system,2026-10-01,1,1,1,0,0,in_progress\n"
        "R10,10,Data and data governance,2026-10-01,1,0,0,0,0,uncovered\n")
    (root / "data" / "derived" / "timeline.csv").write_text(
        "wi_ref,title,deliverable_id,stage_code,stage_name,stage_date,target_pub_date,deadline_id,"
        "deadline_date,days_target_to_deadline,late_vs_deadline\n"
        "prEN 1,Risk management,D01,40,enquiry,2026-03-01,2026-12-01,HR_ANNEX3,2026-08-02,-121,true\n")
    (root / "docs").mkdir()
    (root / "docs" / "quality.md").write_text("# Quality note\n")
    return root


def test_vega_specs_have_both_charts_with_inline_data():
    cov = [{"req_id": "R09", "article": "9", "title": "Risk", "status": "in_progress", "n_work_items": "1"}]
    tl = [{"wi_ref": "prEN 1", "stage_name": "enquiry", "target_pub_date": "2026-12-01",
           "deadline_date": "2026-08-02", "deadline_id": "HR_ANNEX3", "late_vs_deadline": "true"}]
    specs = vega_specs(cov, tl)
    assert set(specs) == {"coverage", "timeline"}
    assert specs["coverage"]["data"]["values"] == cov
    assert specs["timeline"]["data"]["values"] == tl
    json.dumps(specs)  # serialisable


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
    assert "vega-lite@5" in html and "vega@5" in html and "vega-embed@6" in html


def test_cdn_scripts_carry_subresource_integrity(tmp_path, curated_ok):
    out = build(_root(tmp_path, curated_ok), tmp_path / "_site", date(2026, 10, 1))
    html = (out / "index.html").read_text()
    scripts = [line for line in html.splitlines() if "cdn.jsdelivr.net" in line]
    assert len(scripts) == 3
    assert all('integrity="sha384-' in s and 'crossorigin="anonymous"' in s for s in scripts)


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


def test_coverage_article_is_sorted_numerically():
    specs = vega_specs([], [])
    assert specs["coverage"]["data"]["format"] == {"parse": {"article": "number"}}


def test_chart_containers_take_the_page_width(tmp_path, curated_ok):
    # vega-embed makes the container inline-block; with width "container" it collapses to 0 px
    build(_root(tmp_path, curated_ok), tmp_path / "site", date(2026, 10, 1))
    html = (tmp_path / "site" / "index.html").read_text()
    assert ".chart { width: 100%;" in html


def test_timeline_draws_one_point_per_work_item_against_the_first_deadline():
    tl = [{"wi_ref": "prEN 1", "deadline_id": "HR_ANNEX1", "deadline_date": "2028-08-02"},
          {"wi_ref": "prEN 1", "deadline_id": "HR_ANNEX3", "deadline_date": "2027-12-02"}]
    points = vega_specs([], tl)["timeline"]["layer"][1]
    assert points["transform"] == [{"filter": {"field": "deadline_id", "equal": "HR_ANNEX3"}}]
    assert "HR_ANNEX3" in points["encoding"]["color"]["title"]


def test_timeline_colours_a_passed_target():
    scale = vega_specs([], [])["timeline"]["layer"][1]["encoding"]["color"]["scale"]
    assert "target_passed" in scale["domain"] and len(scale["domain"]) == len(scale["range"])


def test_coverage_shows_the_note_of_a_judged_mapping(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    p = root / "data" / "curated" / "request_deliverables.csv"
    p.write_text(p.read_text().replace(",,https://ec.europa.eu/growth/tools-databases/enorm/mandate/593_en,Outside",
                                       ",R10,https://ec.europa.eu/growth/tools-databases/enorm/mandate/593_en,Outside"))
    build(root, tmp_path / "site", date(2026, 10, 1))
    html = (tmp_path / "site" / "index.html").read_text()
    assert "Article 10 (via D09): Outside the Articles 8-15 perimeter (Article 17)." in html


def test_timeline_axis_shows_the_year():
    x = vega_specs([], [])["timeline"]["layer"][1]["encoding"]["x"]
    assert x["axis"]["format"] == "%b %Y"


def test_coverage_labels_each_bar_with_its_status_so_a_zero_bar_still_shows_it():
    cov = [{"req_id": "R08", "article": "8", "title": "Compliance", "status": "uncovered",
            "n_work_items": "0"}]
    spec = vega_specs(cov, [])["coverage"]
    assert [layer["mark"]["type"] for layer in spec["layer"]] == ["bar", "text"]
    assert spec["layer"][1]["encoding"]["text"]["field"] == "status_label"
    # position and colour are shared by both layers, so the label sits at the bar's end in the status colour
    assert spec["encoding"]["x"]["field"] == "n_work_items"
    assert spec["encoding"]["color"]["scale"] == {
        "domain": ["uncovered", "in_progress", "published", "harmonised"],
        "range": ["#9b1c1c", "#8a5a00", "#1f4e79", "#1e6b3a"]}
    assert "encoding" not in spec["layer"][0]


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


def test_page_shows_a_work_item_once_with_a_column_per_deadline(tmp_path, curated_ok):
    html = (build(_two_deadline_root(tmp_path, curated_ok), tmp_path / "_site", date(2026, 10, 1))
            / "index.html").read_text()
    assert html.count(">prEN 1</td>") == 2  # once beside the chart, once in the full table
    assert "HR_ANNEX3" in html and "HR_ANNEX1" in html
    assert ">-121<" in html and ">244<" in html


def test_page_explains_each_deadline_with_its_curated_scope(tmp_path, curated_ok):
    out = build(_root(tmp_path, curated_ok), tmp_path / "_site", date(2026, 10, 1))
    html = (out / "index.html").read_text()
    assert "HR_ANNEX3 (2026-08-02): Annex III high-risk systems" in html


def test_coverage_chart_names_bars_by_article_and_statuses_in_plain_words():
    spec = vega_specs([], [])["coverage"]
    made = {t["as"]: t["calculate"] for t in spec["transform"]}
    assert made == {"article_label": "'Article ' + datum.article",
                    "status_label": "replace(datum.status, '_', ' ')"}
    assert spec["encoding"]["y"]["field"] == "article_label"


def test_timeline_chart_marks_the_as_of_date():
    spec = vega_specs([], [], as_of="2026-10-01")["timeline"]
    marks = [layer for layer in spec["layer"] if layer.get("data") == {"values": [{"as_of": "2026-10-01"}]}]
    assert marks and all(layer["encoding"]["x"]["field"] == "as_of" for layer in marks)


def _html(tmp_path, curated_ok, root=None):
    out = build(root or _root(tmp_path, curated_ok), tmp_path / "_site", date(2026, 10, 1))
    return out, (out / "index.html").read_text()


def test_page_opens_with_one_status_cell_per_requirement(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert html.count('class="sum-cell"') == 2
    assert "<b>Art. 9</b><span>in progress</span>" in html
    assert "<b>Art. 10</b><span>uncovered</span>" in html
    assert "0 harmonised · 0 published · 1 in progress · 1 uncovered, of 2 requirements." in html


def test_a_judged_mapping_is_flagged_where_the_status_is_first_shown(tmp_path, curated_ok):
    root = _root(tmp_path, curated_ok)
    p = root / "data" / "curated" / "request_deliverables.csv"
    p.write_text(p.read_text().replace(",,https://ec.europa.eu/growth/tools-databases/enorm/mandate/593_en,Outside",
                                       ",R10,https://ec.europa.eu/growth/tools-databases/enorm/mandate/593_en,Outside"))
    _, html = _html(tmp_path, curated_ok, root)
    assert "<b>Art. 10</b><span>uncovered *</span>" in html
    assert "<b>Art. 9</b><span>in progress</span>" in html  # no mark on a sourced mapping
    assert "A judgement, not a sourced fact." in html


def test_no_judgement_notice_without_a_judged_mapping(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "A judgement, not a sourced fact." not in html


def test_each_chart_has_a_short_table_beside_it_and_the_full_table_folded(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert html.count('<div class="fig">') == 2
    assert html.count("<details>") == 2
    assert "Days to HR_ANNEX3" in html


def test_chart_rows_and_side_table_rows_share_one_height(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    specs = vega_specs([], [])
    assert specs["coverage"]["height"] == {"step": 46} and specs["timeline"]["height"] == {"step": 46}
    assert "--row: 46px;" in html
    # nothing above the plot may push the chart rows down: no padding, no legend inside the chart
    assert specs["timeline"]["padding"]["top"] == 0 and specs["coverage"]["padding"]["top"] == 0
    points = specs["timeline"]["layer"][1]["encoding"]
    assert points["color"]["legend"] is None and points["shape"]["legend"] is None


def test_timeline_key_is_written_in_the_page(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    for label in ("target before the HR_ANNEX3 deadline", "target after the deadline",
                  "target date passed, not published"):
        assert label in html


def test_fonts_are_served_from_the_site_itself(tmp_path, curated_ok):
    out, html = _html(tmp_path, curated_ok)
    assert (out / "fonts" / "ibm-plex-sans-latin-400.woff2").stat().st_size > 10_000
    assert (out / "fonts" / "OFL.txt").exists()
    assert 'url("fonts/ibm-plex-sans-latin-400.woff2")' in html
    assert "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html


def test_header_states_date_version_and_counts(tmp_path, curated_ok):
    _, html = _html(tmp_path, curated_ok)
    assert "<dt>As of</dt><dd>2026-10-01</dd>" in html
    assert "<dt>Requirements</dt><dd>2</dd>" in html and "<dt>Work items</dt><dd>1</dd>" in html
