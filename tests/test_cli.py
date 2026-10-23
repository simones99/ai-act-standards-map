from pathlib import Path

from aasm import __version__
from aasm.cli import main


def test_version_flag_prints_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"aasm {__version__}"


def test_check_command_exit_code(curated_ok, curated_copy, capsys):
    assert main(["check", "--curated", str(curated_ok)]) == 0
    (curated_copy / "deadlines.csv").unlink()
    assert main(["check", "--curated", str(curated_copy)]) == 1
    assert "deadlines.csv: missing" in capsys.readouterr().out


def test_fetch_eurostat_offline(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "isoc_eb_ain2.json"
    assert main(["fetch-eurostat", "--out", str(tmp_path), "--from-file", str(fixture)]) == 0
    assert (tmp_path / "adoption.csv").exists() and (tmp_path / "lineage.json").exists()


def test_derive_writes_two_files(curated_ok, tmp_path):
    args = ["derive", "--curated", str(curated_ok), "--out", str(tmp_path), "--as-of", "2026-10-01"]
    assert main(args) == 0
    assert (tmp_path / "coverage_by_requirement.csv").exists() and (tmp_path / "timeline.csv").exists()


def test_watch_standards_exit_code_is_1_on_failure(curated_copy, tmp_path, monkeypatch):
    import aasm.watch as watch

    class Gone:
        status_code = 404
        text = ""

        def raise_for_status(self):
            raise RuntimeError("HTTP 404")

    monkeypatch.setattr(watch.requests, "get", lambda url, timeout: Gone())
    monkeypatch.setattr(watch, "_notify_with_gh", lambda item: None)
    args = ["watch-standards", "--curated", str(curated_copy), "--state", str(tmp_path / "s.json"),
            "--history", str(tmp_path / "h.csv")]
    assert main(args) == 1
