from csv import DictWriter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from dcqc.parsers import CsvParser
from dcqc.suites.suite_abc import SuiteABC
from dcqc.tests.base_test import TestStatus


@dataclass
class CsvUpdater:
    """Updates the CSV manifest file with DCQC results.

    The output is the input manifest with five columns appended,
    dcqc_status, dcqc_required_tests, dcqc_skipped_tests, dcqc_failed_tests
    and dcqc_errored_tests. The four list columns are comma-joined into a
    single cell.

    Attributes:
        input_path: Location of the input CSV manifest.
        output_path: Location to write the updated CSV manifest.
        parser: Reader for the input manifest. It is the single source of
            the URL of a row, so that the update method matches a suite to
            a row on the same string that CsvParser gave the suite.
    """

    input_path: Path
    output_path: Path
    parser: CsvParser

    def __init__(self, input_path: Path, output_path: Path):
        """Initialize a CSV manifest updater.

        Args:
            input_path: Location of the input CSV manifest.
            output_path: Location to write the updated CSV manifest.
        """
        self.output_path = output_path
        self.input_path = input_path
        self.parser = CsvParser(input_path)

    def update(self, suites: List[SuiteABC]) -> None:
        """Write the input manifest with the results of the given suites.

        Each suite is matched to a manifest row by the URL of its target.
        Only the first file of a multi-file target is read, so a multi-file
        target collapses to that file.

        Both sides of this match use the URL that CsvParser computes for a
        row, so a relative local path matches whatever the work directory is.

        Args:
            suites: The test suites, one for each row of the manifest.

        Raises:
            KeyError: If a manifest row has no suite with the same URL.
            ValueError: If the input manifest has no rows.
        """
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
        for index, csv_data, file in self.parser.list_rows_and_files():
            if file.url not in suite_dict:
                message = (
                    f"Row {index} of the input CSV ({self.input_path!s}) has "
                    f"no matching suite for its URL ({file.url})."
                )
                raise KeyError(message)
            suite_data = suite_dict[file.url]
            csv_data["dcqc_status"] = suite_data["status"]
            csv_data["dcqc_required_tests"] = ",".join(suite_data["required_tests"])
            csv_data["dcqc_skipped_tests"] = ",".join(suite_data["skipped_tests"])
            csv_data["dcqc_failed_tests"] = ",".join(suite_data["failed_tests"])
            csv_data["dcqc_errored_tests"] = ",".join(suite_data["errored_tests"])
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
