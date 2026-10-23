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
    assert "cff-version" in text and "title" in text and "version: 0.1.0" in text


def test_results_are_dated():
    import re
    text = (ROOT / "docs" / "results.md").read_text()
    assert re.search(r"As of \d{4}-\d{2}-\d{2}", text)
