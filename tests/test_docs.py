from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_states_the_perimeter_and_the_two_rules():
    text = (ROOT / "README.md").read_text()
    for needle in ("Articles 8–15", "Annex III", "describes, it does not interpret", "public sources",
                   "aasm check", "CC BY 4.0", "MIT"):
        assert needle in text, needle


def test_methodology_defines_the_four_statuses():
    text = (ROOT / "docs" / "methodology.md").read_text()
    for s in ("uncovered", "in_progress", "published", "harmonised", "stage_date", "as_of"):
        assert s in text, s


def test_citation_file_is_valid_enough():
    text = (ROOT / "CITATION.cff").read_text()
    assert "cff-version" in text and "title" in text and "version: 0.1.2" in text


def test_results_are_dated():
    import re
    text = (ROOT / "docs" / "results.md").read_text()
    assert re.search(r"As of \d{4}-\d{2}-\d{2}", text)


def test_methodology_points_to_the_l_series_for_citations():
    text = (ROOT / "docs" / "methodology.md").read_text()
    assert "L series" in text and "C series" not in text


def test_no_document_claims_a_uni_catalogue_source():
    for path in ("README.md", "docs/methodology.md", "site/templates/index.html.j2"):
        assert "UNI" not in (ROOT / path).read_text().replace("UNIQUE", ""), path


def test_readme_and_methodology_state_the_two_statuses_and_the_columns_that_hold_them():
    for path in ("README.md", "docs/methodology.md"):
        text = (ROOT / path).read_text(encoding="utf-8")
        for needle in ("`status`", "`status_with_judged`", "public sources alone"):
            assert needle in text, (path, needle)
    assert "`n_judged`" in (ROOT / "docs" / "methodology.md").read_text(encoding="utf-8")


def _results_sections():
    text = (ROOT / "docs" / "results.md").read_text(encoding="utf-8")
    return {part.split("\n", 1)[0].strip(): part for part in text.split("\n## As of ")[1:]}


def test_latest_results_come_first_and_are_dated_2026_11_10():
    assert list(_results_sections())[:2] == ["2026-11-10", "2026-11-06"]


def test_results_of_2026_11_10_give_article_11_its_two_statuses_side_by_side():
    section = _results_sections()["2026-11-10"]
    assert "| On public sources alone | Counting judged links |" in section
    assert "| 11 | Technical documentation | 1 | 1 | 1 | 1 | 1 | uncovered | harmonised |" in section
    assert "0 read `harmonised`, 6 read `in_progress` and 2 read `uncovered`" in section


def test_results_of_2026_11_06_say_they_follow_the_earlier_single_status():
    section = _results_sections()["2026-11-06"]
    assert "status_with_judged" in section and "before version 0.1.2" in section
