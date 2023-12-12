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
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from dcqc.file import File
from dcqc.suites.suite_abc import SuiteABC, SuiteStatus
from dcqc.target import SingleTarget

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
    date_path = get_data("test_contains_word_date.txt")
    ome_tiff_path = get_data("single-channel.ome.tif")
    jsonld_path = get_data("example.jsonld")
    tiff_path = get_data("circuit.tif")
    fastq1_path = get_data("fastq1.fastq")
    fastq2_path = get_data("fastq2.fastq.gz")
    syn_path = "syn://syn50555279"
    tiff_dirty_datetime_path = get_data("test_image_dirty_datetime.tif")
    tiff_date_in_tag_path = get_data("date_tag.tif")
    invalid_xml_ome_tiff_path = get_data("invalid_xml.ome.tif")
    invalid_xml_metadata = {
        "file_type": "tiff",
        "md5_checksum": "a2550a887091d51351d547c8beae8f0c",
    }
    good_metadata = {
        "file_type": "txt",
        "md5_checksum": "14758f1afd44c09b7992073ccf00b43d",
    }
    date_txt_metadata = {
        "file_type": "txt",
        "md5_checksum": "9cee1b0e8c4d051fabea82b62ae69404",
    }
    ome_tiff_metadata = {
        "file_type": "ome-tiff",
        "md5_checksum": "293e46687fa6543a2e8189f1698cc5d0",
    }
    bad_metadata = {
        "file_type": "tiff",
        "md5_checksum": "definitelynottherightmd5checksum",
    }
    jsonld_metadata = {
        "file_type": "JSON-LD",
        "md5_checksum": "56bb5f34da6d6df2ade3ac37e25586b7",
    }
    tiff_metadata = {
        "file_type": "tiff",
        "md5_checksum": "c7b08f6decb5e7572efbe6074926a843",
    }
    fastq_metadata = {"file_type": "fastq"}
    tiff_dirty_datetime_metadata = {
        "file_type": "tiff",
        "md5_checksum": "28a9ee7d0e994d494068ce8d6cda0268",
    }
    test_files = {
        "date_in_tag_tiff": File(tiff_date_in_tag_path.as_posix(), tiff_metadata),
        "good_txt": File(txt_path.as_posix(), good_metadata),
        "date_txt": File(date_path.as_posix(), date_txt_metadata),
        "good_ome_tiff": File(ome_tiff_path.as_posix(), ome_tiff_metadata),
        "invalid_xml_tiff": File(
            invalid_xml_ome_tiff_path.as_posix(), invalid_xml_metadata
        ),
        "bad_txt": File(txt_path.as_posix(), bad_metadata),
        "good_tiff": File(tiff_path.as_posix(), tiff_metadata),
        "good_fastq1": File(fastq1_path.as_posix(), fastq_metadata),
        "good_fastq2": File(fastq2_path.as_posix(), fastq_metadata),
        "jsonld": File(jsonld_path.as_posix(), jsonld_metadata),
        "synapse": File(syn_path, good_metadata),
        "tiff_dirty_datetime": File(
            tiff_dirty_datetime_path.as_posix(), tiff_dirty_datetime_metadata
        ),
    }

    # Create an in-memory remote file based on the good file
    remote_file = File(f"mem://{txt_path.name}", good_metadata)
    remote_file.fs.writetext(remote_file.fs_path, txt_path.read_text())
    test_files["remote"] = remote_file

    yield test_files


@pytest.fixture
def test_targets(test_files):
    test_targets = dict()
    for name, file in test_files.items():
        test_targets[name] = SingleTarget(file)
    yield test_targets


@pytest.fixture
def test_suites(test_targets):
    test_suites = dict()
    for name, target in test_targets.items():
        test_suites[name] = SuiteABC.from_target(target)
    yield test_suites


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


@pytest.fixture
def mocked_suites_single_targets():
    mock_dict_single = {
        "syn://syn51585496": SuiteStatus.GREEN,
        "syn://syn51585494": SuiteStatus.RED,
        "syn://syn51585495": SuiteStatus.AMBER,
        "syn://syn51585493": SuiteStatus.NONE,
    }
    mocked_suites = []
    for url, status in mock_dict_single.items():
        suite = MagicMock(cls=SuiteABC)
        suite.target.files[0].url = url
        suite.get_status.return_value = status
        mocked_suites.append(suite)
    return mocked_suites


# @pytest.fixture
# def mocked_suites_multi_targets():
#     mock_dict_multi = {
#         "syn://syn51585496": SuiteStatus.GREEN,
#         "syn://syn51585494": SuiteStatus.RED,
#         "syn://syn51585495": SuiteStatus.AMBER,
#     }
#     mocked_suites = []
#     for url, status in mock_dict_multi.items():
#         suite = MagicMock(cls=SuiteABC)
#         suite.target.files[0].url = url
#         suite.get_status.return_value = status
#         mocked_suites.append(suite)
#     return mocked_suites
