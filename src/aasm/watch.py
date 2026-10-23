"""Weekly watch of the public pages behind standards.csv. Detects change; a human confirms it."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests

from aasm.curated import load_table

HISTORY_COLUMNS = ("wi_ref", "stage_code", "observed_at")
_SCRIPT_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_DRAFT_PREFIX = re.compile(r"^f?pr", re.I)


def visible_text(page: str) -> str:
    text = _SCRIPT_STYLE.sub(" ", page)
    text = html.unescape(_TAGS.sub(" ", text))
    return _WS.sub(" ", text).strip().lower()


def fingerprint(page: str) -> str:
    return hashlib.sha256(visible_text(page).encode("utf-8")).hexdigest()


def names_work_item(page: str, wi_ref: str) -> bool:
    """An error page served with 200 does not name the work item. "prEN 1" also matches "EN 1:2027"."""
    core = _DRAFT_PREFIX.sub("", wi_ref).split(":")[0].lower()
    return core in visible_text(page)


def append_history(history_path: Path, standards: list[dict], today: date) -> int:
    last: dict[str, str] = {}
    if history_path.exists():
        for r in csv.DictReader(history_path.open(encoding="utf-8", newline="")):
            last[r["wi_ref"]] = r["stage_code"]
    new = [{"wi_ref": s["wi_ref"], "stage_code": s["stage_code"], "observed_at": today.isoformat()}
           for s in standards if last.get(s["wi_ref"]) != s["stage_code"]]
    history_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not history_path.exists()
    with history_path.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HISTORY_COLUMNS, lineterminator="\n")
        if write_header:
            w.writeheader()
        w.writerows(new)
    return len(new)


@dataclass
class WatchResult:
    changed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    appended: int = 0


Notify = Callable[[tuple[str, str]], None]


def open_issue(title: str, body: str, run=subprocess.run) -> None:
    run(["gh", "issue", "create", "--title", title, "--body", body, "--label", "needs-review"], check=True)


def _notify_with_gh(item: tuple[str, str]) -> None:
    open_issue(*item)


def run(curated_dir: Path, state_path: Path, history_path: Path, today: date,
        get=requests.get, notify: Notify = _notify_with_gh) -> WatchResult:
    standards = load_table(curated_dir, "standards")
    state: dict = json.loads(state_path.read_text()) if state_path.exists() else {}
    result = WatchResult()
    previous: dict[str, dict] = {}
    for s in standards:
        wi = s["wi_ref"]
        try:
            resp = get(s["source_url"], timeout=60)
            resp.raise_for_status()
            final_url = getattr(resp, "url", None) or s["source_url"]
            old_host, new_host = urlparse(s["source_url"]).netloc, urlparse(final_url).netloc
            if old_host != new_host:
                raise RuntimeError(f"host changed: {old_host} -> {new_host}")
            if not names_work_item(resp.text, wi):
                raise RuntimeError(f"page does not name {wi}")
            fp = fingerprint(resp.text)
        except Exception as exc:  # noqa: BLE001 - one bad page must not stop the others
            result.failed.append(wi)
            s["_error"] = str(exc)
            continue
        if wi in state and state[wi]["sha256"] != fp:
            result.changed.append(wi)
            previous[wi] = state[wi]
        state[wi] = {"sha256": fp, "checked_at": today.isoformat(), "url": s["source_url"]}
    fetch_failed = list(result.failed)
    result.appended = append_history(history_path, standards, today)
    for wi in result.changed:
        s = next(x for x in standards if x["wi_ref"] == wi)
        try:
            notify((f"Check {wi}: its public page changed ({today.isoformat()})",
                    f"The page behind `{wi}` changed since the last check.\n\nURL: {s['source_url']}\n"
                    f"Recorded stage: {s['stage_code']} ({s['stage_date']}).\n\n"
                    "Open the page, update `data/curated/standards.csv` if the stage or dates moved, "
                    "and close this issue."))
        except Exception as exc:  # noqa: BLE001 - keep the old fingerprint so the change is re-detected next run
            print(f"watch-standards: notification for {wi} failed: {exc}", file=sys.stderr)
            result.failed.append(wi)
            state[wi] = previous[wi]
    if fetch_failed:
        lines = "\n".join(f"- `{wi}`: {next(x for x in standards if x['wi_ref'] == wi).get('_error', '')}"
                          for wi in fetch_failed)
        try:
            notify((f"watch-standards: {len(fetch_failed)} page(s) failed ({today.isoformat()})",
                    f"These pages could not be fetched:\n\n{lines}\n\n"
                    "Check the URLs in `data/curated/standards.csv`."))
        except Exception as exc:  # noqa: BLE001 - the pages are already in result.failed
            print(f"watch-standards: failure notification failed: {exc}", file=sys.stderr)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
