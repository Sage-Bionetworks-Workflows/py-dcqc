import csv
from unittest.mock import MagicMock

from dcqc.suites.suite_abc import SuiteABC
from dcqc.updaters import CsvUpdater


def generate_mocked_suites(mock_dict):
    mocked_suites = []
    for url, status in mock_dict.items():
        suite = MagicMock(SuiteABC)
        suite.target.files[0].url = url
        suite.get_status.return_value = status
        mocked_suites.append(suite)
        return mocked_suites


class TestCsvUpdater:
    mock_dict_single = {
        "syn://syn51585496": "GREEN",
        "syn://syn51585494": "RED",
        "syn://syn51585495": "AMBER",
    }
    mock_dict_multi = {
        "syn://syn51585496": "GREEN",
        "syn://syn51585494": "GREEN",
        "syn://syn51585494": "RED",
        "syn://syn51585495": "GREEN",
        "syn://syn51585495": "AMBER",
    }

    def __init__(self, get_data):
        self.mocked_suites_single = generate_mocked_suites(self.mock_dict_single)
        self.mocked_suites_multi = generate_mocked_suites(self.mock_dict_multi)
        self.input_file = get_data("input.csv")
        self.output_file = get_data("output.csv")
        self.updater = CsvUpdater(self.input_file, self.output_file)

    def get_dcqc_status_list_from_file(self, filename):
        with open(filename, "r") as file:
            reader = csv.DictReader(file)
            status_list = [row["dcqc_status"] for row in reader]
        return status_list

    def test_that_csv_updater_updates_csv_as_expected_with_single_targets(self):
        self.updater.update(self.mocked_suites_single)
        status_list = self.get_dcqc_status_list_from_file(self.output_file)
        assert status_list == ["GREEN", "RED", "AMBER"]

    def test_that_csv_updater_updates_csv_as_expected_with_multi_targets(self):
        self.updater.update(self.mocked_suites_multi)
        status_list = self.get_dcqc_status_list_from_file(self.output_file)
        assert status_list == ["GREEN", "RED", "AMBER"]
