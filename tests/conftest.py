"""
    Dummy conftest.py for dcqc.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    - https://docs.pytest.org/en/stable/fixture.html
    - https://docs.pytest.org/en/stable/writing_plugins.html
"""

from pathlib import Path

import pytest

CNFPATH = Path(__file__).resolve()
TESTDIR = CNFPATH.parent
DATADIR = TESTDIR / "data"


@pytest.fixture
def get_data():
    def _get_data(filename: str) -> Path:
        return DATADIR / filename

    yield _get_data
