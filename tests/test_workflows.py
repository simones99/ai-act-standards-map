import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _job(workflow: str, name: str) -> str:
    """Text of one job: from its `  name:` line to the next job or the end of the file."""
    lines = (ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8").splitlines()
    start = lines.index(f"  {name}:")
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"  \S", lines[i])), len(lines))
    return "\n".join(lines[start:end])


def test_publish_runs_only_when_switched_on():
    # a gate on github.event.repository.private is open when the event payload has no repository object
    assert "if: ${{ vars.PUBLISH_PAGES == 'true' }}" in _job("weekly.yml", "publish")
