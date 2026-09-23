import csv
import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

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


def test_that_csv_updater_writes_test_metrics_keyed_by_test_name(
    get_data: Callable[[str], Path],
    mocked_suites_single_targets: list[MagicMock],
    tmp_path: Path,
) -> None:
    """Test that only tests with metrics are written to dcqc_metrics."""
    # GIVEN a suite with one test that has metrics and one test that has none
    test_with_metrics = MagicMock()
    test_with_metrics.type = "NewTest"
    test_with_metrics.metrics = {"metric1": 1, "metric2": "A"}
    test_without_metrics = MagicMock()
    test_without_metrics.type = "Md5ChecksumTest"
    test_without_metrics.metrics = {}
    mocked_suites_single_targets[0].tests = [test_with_metrics, test_without_metrics]
    input_file = get_data("test_input.csv")
    output_file = tmp_path / "test_output.csv"
    updater = CsvUpdater(input_file, output_file)

    # WHEN I update the CSV with the suites
    updater.update(mocked_suites_single_targets)

    # THEN only the test with metrics is written, keyed by its test name
    with open(output_file, "r") as file:
        metrics_list = [json.loads(row["dcqc_metrics"]) for row in csv.DictReader(file)]
    assert metrics_list == [{"NewTest": {"metric1": 1, "metric2": "A"}}, {}, {}, {}]


def write_paired_manifest(tmp_path: Path) -> Path:
    """Write a two-row FASTQ manifest for a paired target and return its path."""
    input_file = tmp_path / "paired_input.csv"
    with open(input_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["url", "file_type"])
        writer.writerow(["syn://R1", "FASTQ"])
        writer.writerow(["syn://R2", "FASTQ"])
    return input_file


def mock_paired_suite() -> MagicMock:
    """Create a GREEN suite mock for a paired target with R1 and R2 files."""
    paired_test = MagicMock()
    paired_test.type = "PairedFastqParityTest"
    paired_test.metrics = {"line_counts": [8, 8]}
    file_1 = MagicMock()
    file_1.url = "syn://R1"
    file_2 = MagicMock()
    file_2.url = "syn://R2"
    suite = MagicMock()
    suite.get_status.return_value.value = "GREEN"
    suite.target.files = [file_1, file_2]
    suite.tests = [paired_test]
    return suite


# CsvUpdater keys each suite by files[0] only (see the TODO in updaters.py).
# These tests pin that behaviour for paired targets.
def test_that_paired_target_metrics_are_written_only_to_first_file_row(
    tmp_path: Path,
) -> None:
    """Test that paired target metrics are written only to the first file row."""
    # GIVEN a paired suite for R1 and R2, and a single-file suite for R2
    single_suite = MagicMock()
    single_suite.get_status.return_value.value = "GREEN"
    single_suite.target.files[0].url = "syn://R2"
    input_file = write_paired_manifest(tmp_path)
    output_file = tmp_path / "paired_output.csv"
    updater = CsvUpdater(input_file, output_file)

    # WHEN I update the CSV with both suites
    updater.update([mock_paired_suite(), single_suite])

    # THEN the paired metrics are written only to the R1 row
    with open(output_file, "r") as file:
        metrics_list = [json.loads(row["dcqc_metrics"]) for row in csv.DictReader(file)]
    assert metrics_list == [{"PairedFastqParityTest": {"line_counts": [8, 8]}}, {}]


def test_that_second_file_of_paired_target_without_own_suite_raises_error(
    tmp_path: Path,
) -> None:
    """Test that a second paired file with no suite of its own raises KeyError."""
    # GIVEN a paired manifest and only the paired suite, with no suite for R2
    input_file = write_paired_manifest(tmp_path)
    output_file = tmp_path / "paired_output.csv"
    updater = CsvUpdater(input_file, output_file)

    # WHEN I update the CSV with the paired suite
    # THEN a KeyError is raised for the R2 row
    with pytest.raises(KeyError):
        updater.update([mock_paired_suite()])


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
