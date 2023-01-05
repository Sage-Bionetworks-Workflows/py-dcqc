"""
    Dummy conftest.py for dcqc.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    - https://docs.pytest.org/en/stable/fixture.html
    - https://docs.pytest.org/en/stable/writing_plugins.html
"""

from pathlib import Path, PurePath, PurePosixPath

import pytest

from dcqc.file import File

CNFPATH = Path(__file__).resolve()
TESTDIR = CNFPATH.parent
DATADIR = TESTDIR / "data"


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


@pytest.fixture
def test_files(get_data):
    txt_path = get_data("test.txt", as_posix=True)
    tiff_path = get_data("circuit.tif", as_posix=True)
    good_metadata = {
        "file_type": "txt",
        "md5_checksum": "14758f1afd44c09b7992073ccf00b43d",
    }
    bad_metadata = {
        "file_type": "tiff",
        "md5_checksum": "definitelynottherightmd5checksum",
    }
    tiff_metadata = {
        "file_type": "tiff",
        "md5_checksum": "c7b08f6decb5e7572efbe6074926a843",
    }
    test_files = {
        "good": File(txt_path, good_metadata),
        "bad": File(txt_path, bad_metadata),
        "tiff": File(tiff_path, tiff_metadata),
    }
    yield test_files
