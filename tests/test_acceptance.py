import json

from dcqc.parsers.csv_parser import CsvParser
from dcqc.suites.suite_abc import SuiteABC


def test_generate_a_qc_report(get_data):
    csv_path = get_data("files.csv")
    parser = CsvParser(csv_path)
    suites = []
    # For now, this only works for single-file targets
    for target in parser.iter_targets():
        first_file = target.files[0]
        file_type = first_file.get_file_type()
        suite_cls = SuiteABC.get_suite_by_file_type(file_type)
        suite = suite_cls(target)
        suite.compute_tests()
        suites.append(suite)
    report = [suite.to_dict() for suite in suites]
    with open("report.json", "w") as outfile:
        json.dump(report, outfile, indent=2)
