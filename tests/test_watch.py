import csv
import json
from datetime import date
from pathlib import Path

from aasm.watch import append_history, fingerprint, names_work_item, open_issue, run

PAGE = (Path(__file__).parent / "fixtures" / "page_a.html").read_text()


def test_fingerprint_ignores_scripts_and_whitespace():
    a = fingerprint(PAGE)
    b = fingerprint(PAGE.replace("Date.now()", "Date.now()+1").replace("<p>", "<p>\n   "))
    assert a == b and len(a) == 64


def test_fingerprint_changes_when_visible_text_changes():
    assert fingerprint(PAGE) != fingerprint(PAGE.replace("40.20 Enquiry", "50.20 Approval"))


def test_append_history_adds_only_changed_stages(tmp_path):
    hist = tmp_path / "standards_history.csv"
    std = [{"wi_ref": "prEN 1", "stage_code": "40"}, {"wi_ref": "prEN 2", "stage_code": "20"}]
    assert append_history(hist, std, date(2026, 10, 1)) == 2
    assert append_history(hist, std, date(2026, 10, 8)) == 0
    std[0]["stage_code"] = "50"
    assert append_history(hist, std, date(2026, 10, 15)) == 1
    rows = list(csv.DictReader(hist.open()))
    assert [(r["wi_ref"], r["stage_code"], r["observed_at"]) for r in rows] == [
        ("prEN 1", "40", "2026-10-01"), ("prEN 2", "20", "2026-10-01"), ("prEN 1", "50", "2026-10-15")]


class Resp:
    def __init__(self, text, status=200, url=None):
        self.text, self.status_code = text, status
        if url is not None:
            self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_run_records_state_and_reports_changes(curated_ok, tmp_path):
    state, hist = tmp_path / "state.json", tmp_path / "hist.csv"
    notes = []
    first = run(curated_ok, state, hist, date(2026, 10, 1),
                get=lambda url, timeout: Resp(PAGE), notify=notes.append)
    assert first.changed == [] and first.failed == [] and first.appended == 1
    assert json.loads(state.read_text())["prEN 1"]["sha256"] == fingerprint(PAGE)
    second = run(curated_ok, state, hist, date(2026, 10, 8),
                 get=lambda url, timeout: Resp(PAGE.replace("40.20", "50.20")), notify=notes.append)
    assert second.changed == ["prEN 1"]
    assert len(notes) == 1 and "prEN 1" in notes[0][0]


def test_run_keeps_going_after_a_failure_and_notifies_once(curated_copy, tmp_path):
    p = curated_copy / "standards.csv"
    p.write_text(p.read_text() + "prEN 2,Other,D01,20,2026-01-01,,false,,https://standards.cencenelec.eu/x/2,2026-10-01,\n")
    notes = []

    def get(url, timeout):
        return Resp("gone", 404) if url.endswith("/2") else Resp(PAGE)

    res = run(curated_copy, tmp_path / "s.json", tmp_path / "h.csv", date(2026, 10, 1),
              get=get, notify=notes.append)
    assert res.failed == ["prEN 2"] and res.changed == []
    assert json.loads((tmp_path / "s.json").read_text()).keys() == {"prEN 1"}
    assert len(notes) == 1 and "failed" in notes[0][0].lower()


def test_open_issue_calls_gh(tmp_path):
    calls = []
    open_issue("Title", "Body", run=lambda cmd, check: calls.append(cmd))
    assert calls[0][:3] == ["gh", "issue", "create"] and "--title" in calls[0] and "Title" in calls[0]


def test_run_marks_changed_host_as_failed(curated_ok, tmp_path):
    notes = []
    res = run(curated_ok, tmp_path / "s.json", tmp_path / "h.csv", date(2026, 10, 1),
              get=lambda url, timeout: Resp(PAGE, 200, url="https://example.org/moved"), notify=notes.append)
    assert res.failed == ["prEN 1"] and res.changed == []
    assert len(notes) == 1 and "host changed" in notes[0][1]


def test_notify_failure_is_reported_and_state_for_that_page_is_not_saved(curated_ok, tmp_path):
    state, hist = tmp_path / "state.json", tmp_path / "hist.csv"
    run(curated_ok, state, hist, date(2026, 10, 1),
        get=lambda url, timeout: Resp(PAGE), notify=lambda i: None)
    old = json.loads(state.read_text())["prEN 1"]

    def boom(item):
        raise RuntimeError("gh failed")

    res = run(curated_ok, state, hist, date(2026, 10, 8),
              get=lambda url, timeout: Resp(PAGE.replace("40.20", "50.20")), notify=boom)
    assert res.changed == ["prEN 1"] and "prEN 1" in res.failed
    assert json.loads(state.read_text())["prEN 1"] == old


APEX_ERROR = ("<html><body><h1>Sorry, this page isn't available</h1><p>Session state protection violation: "
              "This may be caused by manual alteration of a URL containing a checksum.</p></body></html>")


def test_run_marks_a_page_that_does_not_name_the_work_item_as_failed(curated_ok, tmp_path):
    notes = []
    res = run(curated_ok, tmp_path / "s.json", tmp_path / "h.csv", date(2026, 10, 1),
              get=lambda url, timeout: Resp(APEX_ERROR), notify=notes.append)
    assert res.failed == ["prEN 1"] and res.changed == []
    assert not (tmp_path / "s.json").exists() or "prEN 1" not in json.loads((tmp_path / "s.json").read_text())
    assert len(notes) == 1 and "does not name" in notes[0][1]


def test_run_accepts_the_page_once_the_draft_is_published(curated_ok, tmp_path):
    published = PAGE.replace("prEN 1", "EN 1:2027")
    res = run(curated_ok, tmp_path / "s.json", tmp_path / "h.csv", date(2026, 10, 1),
              get=lambda url, timeout: Resp(published), notify=lambda i: None)
    assert res.failed == []


def test_notify_failure_is_printed_to_stderr(curated_ok, tmp_path, capsys):
    def boom(item):
        raise RuntimeError("gh failed: missing label")

    run(curated_ok, tmp_path / "s.json", tmp_path / "h.csv", date(2026, 10, 1),
        get=lambda url, timeout: Resp(APEX_ERROR), notify=boom)
    assert "gh failed: missing label" in capsys.readouterr().err


def test_names_work_item_needs_the_whole_reference():
    assert not names_work_item("<p>prEN 18229-10 Robustness</p>", "prEN 18229-1")
    assert not names_work_item("<p>Seen 1 time</p>", "prEN 1")
    assert names_work_item("<p>prEN 18229-1 Logging</p>", "prEN 18229-1")
    assert names_work_item("<p>EN 18229-1:2027 Logging</p>", "prEN 18229-1")
    assert names_work_item("<p>EN 18286:2026</p>", "EN 18286:2026")
