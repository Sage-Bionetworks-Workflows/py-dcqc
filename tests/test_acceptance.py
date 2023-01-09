import json

from dcqc.parsers import CsvParser
from dcqc.reports import JsonReport


def test_json_report_generation(get_data):
    # GIVEN a list of suites
    csv_path = get_data("files.csv")
    parser = CsvParser(csv_path)
    suites = parser.list_suites()

    # WHEN I save those suites as a JSON report
    report_name = "report.json"
    report = JsonReport(f"mem://{report_name}")
    report.save(items=suites)

    # THEN the file exists and can be loaded as a JSON file
    fs = report._get_fs()
    assert fs.exists(report_name)
    with fs.open(report_name) as infile:
        json.load(infile)
