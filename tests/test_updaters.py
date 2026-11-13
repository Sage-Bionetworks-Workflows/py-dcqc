import csv
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from dcqc.parsers import CsvParser
from dcqc.suites.suite_abc import SuiteABC, SuiteStatus
from dcqc.tests.base_test import TestStatus
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
    mocked_suites_single_targets: list[Any],
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
    _, _, file = next(iter(CsvParser(manifest).list_rows_and_files()))
    suite = MagicMock()
    suite.cls = SuiteABC
    suite.target.files = [file]
    suite.get_status.return_value = SuiteStatus.GREEN

    output_file = tmp_path / "output.csv"
    updater = CsvUpdater(manifest, output_file)
    updater.update([suite])

    assert get_dcqc_status_list_from_file(output_file) == ["GREEN"]


def test_that_csv_updater_writes_the_same_results_to_both_rows_of_a_pair(
    tmp_path: Path,
) -> None:
    """Test that every file of a paired target gets the results of its suite."""
    # GIVEN a manifest with one pair of grouped rows and one single row
    manifest = tmp_path / "input.csv"
    manifest.write_text(
        "url,file_type,dcqc_grouping\n"
        "syn://syn51585496,FASTQ,pair\n"
        "syn://syn51585494,FASTQ,pair\n"
        "syn://syn51585495,TXT,\n"
    )
    failed_test = MagicMock(type="PairedFastqParityTest", metrics={"lines": 4})
    failed_test._status = TestStatus.FAIL
    paired_suite = MagicMock()
    paired_suite.target.files = [
        MagicMock(url="syn://syn51585496"),
        MagicMock(url="syn://syn51585494"),
    ]
    paired_suite.get_status.return_value = SuiteStatus.RED
    paired_suite.required_tests = ["PairedFastqParityTest"]
    paired_suite.skipped_tests = []
    paired_suite.tests = [failed_test]
    single_suite = MagicMock()
    single_suite.target.files = [MagicMock(url="syn://syn51585495")]
    single_suite.get_status.return_value = SuiteStatus.GREEN
    single_suite.required_tests = []
    single_suite.skipped_tests = []
    single_suite.tests = []
    output_file = tmp_path / "output.csv"
    updater = CsvUpdater(manifest, output_file)

    # WHEN I update the CSV with the suites
    updater.update([paired_suite, single_suite])

    # THEN both rows of the pair get the same dcqc values
    with open(output_file, "r") as file:
        rows = list(csv.DictReader(file))
    dcqc_columns = [key for key in rows[0] if key.startswith("dcqc_")]
    dcqc_rows = [{key: row[key] for key in dcqc_columns} for row in rows]
    assert dcqc_rows[0] == dcqc_rows[1]
    assert dcqc_rows[0]["dcqc_status"] == "RED"
    assert dcqc_rows[0]["dcqc_failed_tests"] == "PairedFastqParityTest"
    assert json.loads(dcqc_rows[0]["dcqc_metrics"]) == {
        "PairedFastqParityTest": {"lines": 4}
    }
    # AND the single row gets the results of its own suite
    assert dcqc_rows[2]["dcqc_status"] == "GREEN"
