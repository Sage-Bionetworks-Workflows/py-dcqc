import csv

import pytest

from dcqc.updaters import CsvUpdater


def get_dcqc_status_list_from_file(filename):
    with open(filename, "r") as file:
        reader = csv.DictReader(file)
        status_list = [row["dcqc_status"] for row in reader]
    return status_list


def test_that_csv_updater_updates_csv_as_expected_with_single_targets(
    get_data, mocked_suites_single_targets
):
    input_file = get_data("test_input.csv")
    output_file = get_data("test_output.csv")
    updater = CsvUpdater(input_file, output_file)
    updater.update(mocked_suites_single_targets)
    status_list = get_dcqc_status_list_from_file(output_file)
    assert status_list == ["GREEN", "RED", "AMBER", "NONE"]


def test_that_empty_input_manifest_raises_error(get_data, mocked_suites_single_targets):
    with pytest.raises(ValueError):
        empty_updater = CsvUpdater(
            get_data("empty_input.csv"), get_data("test_output.csv")
        )
        empty_updater.update(mocked_suites_single_targets)


# def test_that_csv_updater_updates_csv_as_expected_with_multi_targets(
#     get_data, mocked_suites_multi_targets
# ):
#     input_file = get_data("input.csv")
#     output_file = get_data("output.csv")
#     updater = CsvUpdater(input_file, output_file)
#     updater.update(mocked_suites_multi_targets)
#     status_list = get_dcqc_status_list_from_file(output_file)
#     assert status_list == ["GREEN", "RED", "AMBER"]
