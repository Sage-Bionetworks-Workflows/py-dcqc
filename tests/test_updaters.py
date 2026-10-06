import csv
import re
from unittest.mock import MagicMock

import pytest

from dcqc.parsers import CsvParser
from dcqc.suites.suite_abc import SuiteABC, SuiteStatus
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


def test_that_csv_updater_joins_relative_absolute_and_remote_urls(
    relative_manifest, tmp_path
):
    """Every kind of URL must survive the join of a suite to its row.

    CsvParser rebases only a relative local URL to the manifest directory.
    An absolute local URL and a remote URL are not changed. CsvUpdater must
    match each suite to its row in all three cases, and must write the url
    column as it is in the input manifest.
    """
    # GIVEN a manifest with a relative, an absolute and a remote URL
    input_urls = [row["url"] for _, row in CsvParser(relative_manifest).list_rows()]

    # AND one suite for each row, with the URL that CsvParser gives the suite
    statuses = [SuiteStatus.GREEN, SuiteStatus.RED, SuiteStatus.AMBER]
    suites = []
    for (_, file), status in zip(CsvParser(relative_manifest).create_files(), statuses):
        suite = MagicMock()
        suite.cls = SuiteABC
        suite.target.files[0].url = file.url
        suite.get_status.return_value = status
        suites.append(suite)

    # WHEN I update the manifest with the suites in reverse order
    output_file = tmp_path / "output.csv"
    CsvUpdater(relative_manifest, output_file).update(suites[::-1])

    # THEN I expect each row to get the status of its own suite
    assert get_dcqc_status_list_from_file(output_file) == ["GREEN", "RED", "AMBER"]

    # AND I expect the url column to be the same as in the input manifest
    with open(output_file, "r") as file:
        output_urls = [row["url"] for row in csv.DictReader(file)]
    assert output_urls == input_urls


def test_for_an_error_when_a_manifest_row_has_no_matching_suite(
    relative_manifest, tmp_path
):
    """A row without a suite must raise KeyError that names the row and URL.

    The suite for the first row has the URL as it is written in the manifest,
    not the URL that CsvParser rebases to the manifest directory. That is the
    key that CsvUpdater used before the fix, so the two must not match.
    """
    # GIVEN the files that CsvParser makes from the manifest
    files = [file for _, file in CsvParser(relative_manifest).create_files()]

    # AND suites where the first suite has the raw relative URL
    urls = ["test.txt"] + [file.url for file in files[1:]]
    suites = []
    for url in urls:
        suite = MagicMock()
        suite.cls = SuiteABC
        suite.target.files[0].url = url
        suite.get_status.return_value = SuiteStatus.GREEN
        suites.append(suite)

    # WHEN I update the manifest
    # THEN I expect a KeyError that names the first row and its rebased URL
    output_file = tmp_path / "output.csv"
    message = (
        f"Row 1 of the input CSV ({relative_manifest!s}) has "
        f"no matching suite for its URL ({files[0].url})."
    )
    with pytest.raises(KeyError, match=re.escape(message)):
        CsvUpdater(relative_manifest, output_file).update(suites)

    # AND I expect no output manifest to be written
    assert not output_file.exists()


# def test_that_csv_updater_updates_csv_as_expected_with_multi_targets(
#     get_data, mocked_suites_multi_targets
# ):
#     input_file = get_data("input.csv")
#     output_file = get_data("output.csv")
#     updater = CsvUpdater(input_file, output_file)
#     updater.update(mocked_suites_multi_targets)
#     status_list = get_dcqc_status_list_from_file(output_file)
#     assert status_list == ["GREEN", "RED", "AMBER"]
