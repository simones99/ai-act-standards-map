import json
import shutil
from datetime import date

from aasm.site import build, vega_specs


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
