import json

import pytest

from dcqc.parsers import CsvParser
from dcqc.reports import JsonReport
from dcqc.tests.test_abc import TestABC


@pytest.mark.integration
def test_json_report_generation(get_data, get_output):
    # GIVEN a list of external tests to skip (to remain self-contained)
    all_tests = TestABC.list_tests()
    skipped_tests = [test.__name__ for test in all_tests if test.is_external_test]

    # AND a subset of internal tests to be required (to verify suite status behavior)
    required_tests = ["Md5ChecksumTest"]

    # AND a CSV file of TXT and TIFF files
    csv_path = get_data("files.csv")

    # AND a destination for the JSON report
    report_path = get_output("report.json")
    report_url = report_path.as_posix()

    # WHEN the CSV file is parsed to generate the relevant QC suites
    parser = CsvParser(csv_path)
    suites = parser.create_suites(required_tests, skipped_tests)

    # AND those suites are used to generate a JSON report
    report = JsonReport(report_url, overwrite=True)
    report.save(suites)

    # THEN the file exists
    assert report_path.exists()

    # AND the file can be loaded by the `json` module
    # TODO: Replace with step to recreate the suites from the JSON report
    with report_path.open() as infile:
        json.load(infile)
