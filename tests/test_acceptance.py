import json

import pytest

from dcqc.parsers import CsvParser
from dcqc.reports import JsonReport
from dcqc.tests.test_abc import TestABC


@pytest.mark.integration
def test_json_report_generation(get_data, get_output):
    # GIVEN a list of external tests
    all_tests = TestABC.list_tests()
    external_tests = [test.__name__ for test in all_tests if test.is_external_test]

    # AND a list of suites configured to skip external tests
    #     and require the Md5ChecksumTest
    csv_path = get_data("files.csv")
    parser = CsvParser(csv_path)
    suites = parser.create_suites(
        required_tests=["Md5ChecksumTest"],
        skipped_tests=external_tests,
    )

    # WHEN I save those suites as a JSON report
    report_path = get_output("report.json")
    report_url = report_path.as_posix()
    report = JsonReport(report_url, overwrite=True)
    report.save(items=suites)

    # THEN the file exists and can be loaded as a JSON file
    assert report_path.exists()
    with report_path.open() as infile:
        json.load(infile)
