"""
    Dummy conftest.py for dcqc.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    - https://docs.pytest.org/en/stable/fixture.html
    - https://docs.pytest.org/en/stable/writing_plugins.html
"""

from datetime import datetime
from getpass import getuser
from pathlib import Path
from uuid import uuid4

import pytest

from dcqc.file import File

CNFPATH = Path(__file__).resolve()
TESTDIR = CNFPATH.parent
DATADIR = TESTDIR / "data"
OUTDIR = TESTDIR / "outputs"

OUTDIR.mkdir(exist_ok=True)

UUID = str(uuid4())
USER = getuser()
UTCTIME = datetime.now().isoformat(" ", "seconds").replace(":", ".")
RUN_ID = f"{USER} - {UTCTIME} - {UUID}"  # Valid characters: [A-Za-z0-9 .+'()_-]


# Track the list of output files to avoid clashes between tests
outputs = set()


@pytest.fixture
def run_id():
    return RUN_ID


@pytest.fixture
def get_data():
    def _get_data(filename: str) -> Path:
        path = DATADIR / filename
        if not path.exists():
            raise ValueError(f"Path ({path}) does not exist.")
        return path

    yield _get_data


@pytest.fixture
def test_files(get_data):
    txt_path = get_data("test.txt")
    tiff_path = get_data("circuit.tif")
    syn_path = "syn://syn50555279"
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
        "good": File(txt_path.as_posix(), good_metadata),
        "bad": File(txt_path.as_posix(), bad_metadata),
        "tiff": File(tiff_path.as_posix(), tiff_metadata),
        "synapse": File(syn_path, good_metadata),
    }

    # Create an in-memory remote file based on the good file
    remote_file = File(f"mem://{txt_path.name}", good_metadata)
    remote_file.fs.writetext(remote_file.fs_path, txt_path.read_text())
    test_files["remote"] = remote_file

    yield test_files


@pytest.fixture
def get_output():
    def _get_output(filename: str) -> Path:
        output = OUTDIR / filename
        if output in outputs:
            message = f"Output ({output}) has already been used in another test."
            raise ValueError(message)
        outputs.add(output)
        return output

    yield _get_output
