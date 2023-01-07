"""
    Dummy conftest.py for dcqc.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    - https://docs.pytest.org/en/stable/fixture.html
    - https://docs.pytest.org/en/stable/writing_plugins.html
"""

from pathlib import Path, PurePath, PurePosixPath
from uuid import uuid4

import pytest

CNFPATH = Path(__file__).resolve()
TESTDIR = CNFPATH.parent
DATADIR = TESTDIR / "data"

UUID = str(uuid4())


def pytest_configure():
    pytest.UUID = UUID  # type: ignore


@pytest.fixture
def get_data():
    def _get_data(filename: str, as_posix: bool = False) -> PurePath:
        path = DATADIR / filename
        if not path.exists():
            raise ValueError(f"Path ({path}) does not exist.")
        if as_posix:
            path = PurePosixPath(*path.parts)  # type: ignore
        return path

    yield _get_data
