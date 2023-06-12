import csv

from unittest.mock import MagicMock

from dcqc.updaters import CsvUpdater
from pathlib import Path
from dcqc.suites.suite_abc import SuiteABC


class TestCsvUpdater:
    mock_dict = {
        "syn://syn51585496": "GREEN",
        "syn://syn51585494": "RED",
        "syn://syn51585495": "AMBER",
    }

    def __init__(self):
        self.mocked_suites = []
        for url, status in self.mock_dict.items():
            suite = MagicMock(SuiteABC)
            suite.target.files[0].url = url
            suite.get_status.return_value = status
            self.mocked_suites.append(suite)

    def get_dcqc_status_list_from_file(self, filename):
        with open(filename, "r") as file:
            reader = csv.DictReader(file)
            status_list = [row["dcqc_status"] for row in reader]
        return status_list

    def test_that_csv_updater_updates_csv_as_expected(self, get_data):
        input_file = get_data("input.csv")
        output_file = get_data("output.csv")
        updater = CsvUpdater(input_file, output_file)
        updater.update(self.mocked_suites)
        status_list = self.get_dcqc_status_list_from_file(output_file)
        assert status_list == ["GREEN", "RED", "AMBER"]
