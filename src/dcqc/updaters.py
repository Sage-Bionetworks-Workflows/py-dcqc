from csv import DictWriter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from dcqc.parsers import CsvParser
from dcqc.suites.suite_abc import SuiteABC
from dcqc.tests.base_test import TestStatus


@dataclass
class CsvUpdater:
    """Updates the CSV manifest file with DCQC results."""

    input_path: Path
    output_path: Path
    parser: CsvParser

    def __init__(self, input_path: Path, output_path: Path):
        self.output_path = output_path
        self.input_path = input_path

    def update(self, suites: List[SuiteABC]) -> None:
        suite_dict: dict[str, dict[str, Any]] = {}
        # TODO add support for suites with multiple files in them (multi)
        for suite in suites:
            url = suite.target.files[0].url
            suite_dict[url] = {
                "status": suite.get_status().value,
                "required_tests": suite.required_tests,
                "skipped_tests": suite.skipped_tests,
                "failed_tests": [],
                "errored_tests": [],
            }
            for test in suite.tests:
                if test._status == TestStatus.FAIL:
                    suite_dict[url]["failed_tests"].append(test.type)
                if test._status == TestStatus.ERROR:
                    suite_dict[url]["errored_tests"].append(test.type)

        # Create CSV data structure
        row_list = []
        parser = CsvParser(self.input_path)
        for _, csv_data in parser.list_rows():
            csv_data["dcqc_status"] = suite_dict[csv_data["url"]]["status"]
            csv_data["dcqc_required_tests"] = ",".join(
                suite_dict[csv_data["url"]]["required_tests"]
            )
            csv_data["dcqc_skipped_tests"] = ",".join(
                suite_dict[csv_data["url"]]["skipped_tests"]
            )
            csv_data["dcqc_failed_tests"] = ",".join(
                suite_dict[csv_data["url"]]["failed_tests"]
            )
            csv_data["dcqc_errored_tests"] = ",".join(
                suite_dict[csv_data["url"]]["errored_tests"]
            )
            row_list.append(csv_data)

        if row_list:
            keys = row_list[0].keys()
            # Export updated CSV
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(
                str(self.output_path), "w+", newline="", encoding="utf-8"
            ) as output_file:
                dict_writer = DictWriter(output_file, keys)
                dict_writer.writeheader()
                dict_writer.writerows(row_list)
        else:
            raise ValueError("No rows found in input CSV")
