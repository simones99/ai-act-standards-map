from aasm.curated import check_tables, load_table
from aasm.schema import TABLES


def _rewrite(path, text):
    path.write_text(text, encoding="utf-8")


def test_schema_lists_five_tables():
    assert set(TABLES) == {"requirements", "annex3_areas", "request_deliverables", "standards", "deadlines"}


def test_valid_fixture_has_no_errors(curated_ok):
    assert check_tables(curated_ok) == []


def test_load_table_returns_rows_as_dicts(curated_ok):
    rows = load_table(curated_ok, "requirements")
    assert rows[0]["req_id"] == "R09"
    assert rows[0]["paragraph"] == ""


def test_missing_file_is_reported(curated_copy):
    (curated_copy / "deadlines.csv").unlink()
    errors = check_tables(curated_copy)
    assert any("deadlines.csv" in e and "missing" in e for e in errors)


def test_wrong_header_is_reported(curated_copy):
    _rewrite(curated_copy / "deadlines.csv", "id,date\nX,2026-01-01\n")
    errors = check_tables(curated_copy)
    assert any("deadlines.csv" in e and "header" in e for e in errors)


def test_bom_and_semicolon_are_rejected(curated_copy):
    text = "﻿deadline_id;date;scope;source_url;note\nX;2026-01-01;s;https://a;\n"
    _rewrite(curated_copy / "deadlines.csv", text)
    errors = check_tables(curated_copy)
    assert any("deadlines.csv" in e and ("BOM" in e or "header" in e) for e in errors)


def test_duplicate_key_is_reported(curated_copy):
    p = curated_copy / "requirements.csv"
    _rewrite(p, p.read_text() + "R09,9,,Dup,Dup.,https://eur-lex.europa.eu/x\n")
    assert any("duplicate" in e and "R09" in e for e in check_tables(curated_copy))


def test_required_column_empty_is_reported(curated_copy):
    p = curated_copy / "requirements.csv"
    _rewrite(p, p.read_text().replace("Risk management system,A continuous", ",A continuous"))
    assert any("requirements.csv" in e and "title" in e and "empty" in e for e in check_tables(curated_copy))


def test_source_url_must_be_https(curated_copy):
    p = curated_copy / "deadlines.csv"
    _rewrite(p, p.read_text().replace("https://eur-lex", "http://eur-lex"))
    assert any("source_url" in e for e in check_tables(curated_copy))


def test_bad_stage_code_is_reported(curated_copy):
    p = curated_copy / "standards.csv"
    _rewrite(p, p.read_text().replace(",40,", ",45,"))
    assert any("stage_code" in e and "45" in e for e in check_tables(curated_copy))


def test_bad_date_is_reported(curated_copy):
    p = curated_copy / "standards.csv"
    _rewrite(p, p.read_text().replace("2026-03-01", "01/03/2026"))
    assert any("stage_date" in e for e in check_tables(curated_copy))


def test_bool_column_accepts_only_true_false(curated_copy):
    p = curated_copy / "standards.csv"
    _rewrite(p, p.read_text().replace(",false,", ",no,"))
    assert any("ojeu_cited" in e for e in check_tables(curated_copy))


def test_unknown_deliverable_in_standards_is_reported(curated_copy):
    p = curated_copy / "standards.csv"
    _rewrite(p, p.read_text().replace(",D01,", ",D99,"))
    assert any("D99" in e and "request_deliverables" in e for e in check_tables(curated_copy))


def test_unknown_requirement_in_deliverable_is_reported(curated_copy):
    p = curated_copy / "request_deliverables.csv"
    _rewrite(p, p.read_text().replace(",R09,", ",R09|R99,"))
    assert any("R99" in e and "requirements" in e for e in check_tables(curated_copy))


def test_empty_covers_req_ids_is_allowed(curated_ok):
    # D09 covers nothing inside the perimeter and that is fine
    assert check_tables(curated_ok) == []
