import csv
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


def test_that_csv_updater_joins_a_manifest_of_relative_local_paths(tmp_path):
    """A manifest of relative local paths must survive the join to its rows.

    CsvParser rewrites a relative local URL to be relative to the manifest
    directory (parsers.py:81 -> file.py:247), but CsvUpdater looks up the raw
    column value (updaters.py:45). The two keys diverge when the manifest is
    in a directory other than the working directory, and the lookup raises
    KeyError.
    """
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    (manifest_dir / "test.txt").write_text("Hello world!\n")
    manifest = manifest_dir / "input.csv"
    manifest.write_text("url,file_type\ntest.txt,TXT\n")

    # Build the suite URL the way the pipeline does, through CsvParser.
    _, file = next(iter(CsvParser(manifest).create_files()))
    suite = MagicMock()
    suite.cls = SuiteABC
    suite.target.files[0].url = file.url
    suite.get_status.return_value = SuiteStatus.GREEN

    output_file = tmp_path / "output.csv"
    updater = CsvUpdater(manifest, output_file)
    updater.update([suite])

    assert get_dcqc_status_list_from_file(output_file) == ["GREEN"]


# def test_that_csv_updater_updates_csv_as_expected_with_multi_targets(
#     get_data, mocked_suites_multi_targets
# ):
#     input_file = get_data("input.csv")
#     output_file = get_data("output.csv")
#     updater = CsvUpdater(input_file, output_file)
#     updater.update(mocked_suites_multi_targets)
#     status_list = get_dcqc_status_list_from_file(output_file)
#     assert status_list == ["GREEN", "RED", "AMBER"]
