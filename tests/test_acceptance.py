import json

import pytest
from fs import open_fs

from dcqc.parsers import CsvParser
from dcqc.reports import JsonReport
from dcqc.tests.base_test import BaseTest
from dcqc.utils import open_parent_fs

PARENT_FOLDER_URL = "syn://syn50696607"


@pytest.fixture
def acceptance_test_folder_url(run_id):
    """Create a run-specific subfolder under parent folder.

    This is done to avoid clashes between concurrent tests.
    """
    fs = open_fs(PARENT_FOLDER_URL)
    fs.makedir(run_id)
    yield f"{PARENT_FOLDER_URL}/{run_id}"
    fs.removetree(run_id)


@pytest.mark.slow
def test_json_report_generation(get_data, acceptance_test_folder_url):
    # GIVEN a list of external tests to skip (to remain self-contained)
    all_tests = BaseTest.list_subclasses()
    skipped_tests = [test.__name__ for test in all_tests if test.is_external_test]

    # AND a subset of internal tests to be required (to verify suite status behavior)
    required_tests = ["Md5ChecksumTest"]

    # AND a CSV file of TXT and TIFF files
    csv_path = get_data("files.csv")

    # AND a remote destination for the JSON report
    report_url = f"{acceptance_test_folder_url}/report.json"

    # WHEN the CSV file is parsed to generate the relevant QC suites
    parser = CsvParser(csv_path)
    suites = parser.create_suites(required_tests, skipped_tests)

    # AND those suites are used to generate a JSON report
    report = JsonReport()
    report.save(suites, report_url, overwrite=True)

    # THEN the file exists
    fs, basename = open_parent_fs(report_url)
    assert fs.exists(basename)

    # AND the file can be loaded by the `json` module
    with fs.open(basename) as infile:
        contents = json.load(infile)
    assert contents
