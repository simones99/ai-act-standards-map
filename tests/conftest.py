from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def curated_ok() -> Path:
    return FIXTURES / "curated_ok"


@pytest.fixture
def curated_copy(curated_ok, tmp_path) -> Path:
    """A writable copy of the valid fixture, to break one thing at a time."""
    import shutil

    dst = tmp_path / "curated"
    shutil.copytree(curated_ok, dst)
    return dst
