import csv
import shutil
from pathlib import Path
from typing import Any

from click.testing import Result
from typer.testing import CliRunner

import dcqc
from dcqc.main import app
from dcqc.parsers import JsonParser
from dcqc.reports import JsonReport
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import PairedTarget
from dcqc.tests.base_test import BaseTest


def run_command(arguments: list[Any]):
    runner = CliRunner()
    str_arguments = [str(arg) for arg in arguments]
    result = runner.invoke(app, str_arguments)
    return result


def check_command_result(result: Result):
    if result.exit_code != 0:
        print(result.stdout)
        try:
            print(result.stderr)
        except ValueError:
            pass
    assert result.exit_code == 0


# TODO: Fix this test: https://sagebionetworks.jira.com/browse/ORCA-349
"""
@pytest.mark.slow
def test_that_the_module_cli_behaves_the_same_as_the_plain_cli():
    module_cli = check_output(["python", "-m", "dcqc", "--help"])
    plain_cli = check_output(["dcqc", "--help"])
    assert module_cli == plain_cli
"""


def test_that_the_package_version_can_be_printed():
    args = ["--version"]
    result = run_command(args)
    check_command_result(result)
    assert dcqc.__version__ in result.output


def test_create_targets(get_data, get_output):
    input_csv = get_data("small.csv")
    output_dir = get_output("create_targets")
    shutil.rmtree(output_dir, ignore_errors=True)

    assert not output_dir.exists()
    args = ["create-targets", input_csv, output_dir]
    result = run_command(args)
    check_command_result(result)
    assert len(list(output_dir.iterdir())) > 0


def test_create_tests(get_data, get_output):
    input_json = get_data("target.json")
    output_dir = get_output("create_tests")
    shutil.rmtree(output_dir, ignore_errors=True)

    assert not output_dir.exists()
    args = ["create-tests", "-r", "Md5ChecksumTest", input_json, output_dir]
    result = run_command(args)
    check_command_result(result)
    assert len(list(output_dir.iterdir())) > 0


def test_create_tests_with_paired_target(test_files, get_output):
    # GIVEN a target JSON file for a pair of FASTQ files
    output_dir = get_output("create_tests_with_paired_target")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True)

    files = [test_files["good_fastq"], test_files["good_compressed_fastq"]]
    input_json = output_dir / "target.json"
    JsonReport().save(PairedTarget(files), input_json.as_posix())

    # WHEN I run create-tests on the paired target
    tests_dir = output_dir / "tests"
    args = ["create-tests", input_json, tests_dir]
    result = run_command(args)
    # THEN the command succeeds and writes the paired FASTQ test
    check_command_result(result)
    assert (tests_dir / "target.PairedFastqParityTest.json").exists()


def test_create_process(get_data, get_output):
    input_json = get_data("test.external.json")
    output_path = get_output("create_process") / "process.json"
    output_path.unlink(missing_ok=True)

    assert not output_path.exists()
    args = ["create-process", input_json, output_path]
    result = run_command(args)
    check_command_result(result)
    assert output_path.exists()


def test_compute_test(get_data, get_output):
    input_json = get_data("test.internal.json")
    output_path = get_output("compute_test") / "test.json"
    output_path.unlink(missing_ok=True)

    assert not output_path.exists()
    args = ["compute-test", input_json, output_path]
    result = run_command(args)
    check_command_result(result)
    assert output_path.exists()


def test_create_suite(get_data, get_output):
    input_json = get_data("test.computed.json")
    output_path = get_output("create_suite") / "suite.json"
    output_path.unlink(missing_ok=True)

    args = ["create-suite", output_path, input_json, input_json, input_json]
    result = run_command(args)
    check_command_result(result)
    assert output_path.exists()

    suite = JsonParser.parse_object(output_path, SuiteABC)
    assert len(suite.required_tests) > 0


def test_combine_suites(get_data, get_output):
    input_json = get_data("suite.json")
    output_path = get_output("combine_suites") / "suites.json"
    output_path.unlink(missing_ok=True)

    args = ["combine-suites", output_path, input_json, input_json, input_json]
    result = run_command(args)
    check_command_result(result)
    assert output_path.exists()


def test_list_tests():
    args = ["list-tests"]
    result = run_command(args)
    check_command_result(result)


def test_qc_file(get_data):
    tiff_path = get_data("circuit.tif")
    args = [
        "qc-file",
        "-t",
        "TIFF",
        "-m",
        '{"md5_checksum": "c7b08f6decb5e7572efbe6074926a843"}',
        tiff_path,
    ]
    result = run_command(args)
    check_command_result(result)


def test_qc_file_with_skipped_tests(get_data):
    tiff_path = get_data("circuit.tif")
    result = run_command(
        [
            "qc-file",
            "-t",
            "TIFF",
            "-m",
            '{"md5_checksum": "c7b08f6decb5e7572efbe6074926a843"}',
            "--skipped-tests",
            "Md5ChecksumTest",
            tiff_path,
        ]
    )
    check_command_result(result)


def test_qc_file_with_required_tests(get_data):
    tiff_path = get_data("circuit.tif")
    result = run_command(
        [
            "qc-file",
            "-t",
            "TIFF",
            "-m",
            '{"md5_checksum": "c7b08f6decb5e7572efbe6074926a843"}',
            "--required-tests",
            "Md5ChecksumTest",
            tiff_path,
        ]
    )
    check_command_result(result)


def test_qc_file_h5ad(get_data):
    h5ad_path = get_data("example.h5ad")
    args = [
        "qc-file",
        "-t",
        "h5ad",
        "-m",
        '{"md5_checksum": "0202e65ddc114d97f0794366503d574f"}',
        h5ad_path,
    ]
    result = run_command(args)
    check_command_result(result)


def run_pipeline(input_csv: Path, output_dir: Path) -> list[dict[str, str]]:
    """Run every CLI step in order, and give the rows of the updated CSV.

    Each step reads the JSON files that the step before it wrote. The
    external tests are skipped, because only nf-dcqc can run them.
    """
    shutil.rmtree(output_dir, ignore_errors=True)
    external_tests = [
        test.__name__ for test in BaseTest.list_subclasses() if test.is_external_test
    ]
    skip_args = [arg for name in external_tests for arg in ("-s", name)]

    targets_dir = output_dir / "targets"
    result = run_command(["create-targets", input_csv, targets_dir])
    check_command_result(result)

    suite_paths = []
    for target_json in sorted(targets_dir.iterdir()):
        tests_dir = output_dir / "tests" / target_json.stem
        args = ["create-tests", *skip_args, target_json, tests_dir]
        check_command_result(run_command(args))

        computed_paths = []
        for test_json in sorted(tests_dir.iterdir()):
            computed_path = output_dir / "computed" / target_json.stem / test_json.name
            args = ["compute-test", test_json, computed_path]
            check_command_result(run_command(args))
            computed_paths.append(computed_path)

        suite_path = output_dir / "suites" / f"{target_json.stem}.json"
        args = ["create-suite", *skip_args, suite_path, *computed_paths]
        check_command_result(run_command(args))
        suite_paths.append(suite_path)

    suites_path = output_dir / "suites.json"
    args = ["combine-suites", suites_path, *suite_paths]
    check_command_result(run_command(args))

    output_csv = output_dir / "output.csv"
    args = ["update-csv", suites_path, input_csv, output_csv]
    check_command_result(run_command(args))

    with output_csv.open(newline="") as file:
        return list(csv.DictReader(file))


def split_cell(cell: str) -> set[str]:
    """Split a comma-joined list cell, whose order is not stable."""
    return set(cell.split(",")) if cell else set()


def test_pipeline_with_single_targets(get_data, get_output):
    # GIVEN a manifest of five local files with no grouping
    input_csv = get_data("pipeline_single.csv")
    output_dir = get_output("pipeline_single")
    # WHEN I run every CLI step on the manifest
    rows = run_pipeline(input_csv, output_dir)

    # THEN each row is one target and gets the status of its own suite
    assert len(list((output_dir / "targets").iterdir())) == 5
    assert [row["url"] for row in rows] == [
        "test.txt",
        "circuit.tif",
        "example.jsonld",
        "example.tsv",
        "example.bam",
    ]
    statuses = {row["url"]: row["dcqc_status"] for row in rows}
    assert statuses == {
        "test.txt": "GREEN",
        "circuit.tif": "GREEN",
        "example.jsonld": "GREEN",
        "example.tsv": "GREEN",
        "example.bam": "RED",
    }
    bam_row = rows[4]
    assert split_cell(bam_row["dcqc_failed_tests"]) == {"Md5ChecksumTest"}
    tiff_row = rows[1]
    assert "LibTiffInfoTest" in split_cell(tiff_row["dcqc_skipped_tests"])


def test_pipeline_with_grouped_targets(get_data, get_output):
    # GIVEN a manifest where two FASTQ rows share a grouping value
    input_csv = get_data("pipeline_grouped.csv")
    output_dir = get_output("pipeline_grouped")
    # WHEN I run every CLI step on the manifest
    rows = run_pipeline(input_csv, output_dir)

    # THEN the two FASTQ rows are one target and both get its results
    # Three single-file targets and one PairedTarget for the two FASTQ rows
    assert len(list((output_dir / "targets").iterdir())) == 4
    assert [row["url"] for row in rows] == [
        "test.txt",
        "fastq1.fastq",
        "circuit.tif",
        "fastq2.fastq.gz",
        "example.bam",
    ]
    statuses = {row["url"]: row["dcqc_status"] for row in rows}
    assert statuses == {
        "test.txt": "GREEN",
        "fastq1.fastq": "RED",
        "circuit.tif": "GREEN",
        "fastq2.fastq.gz": "RED",
        "example.bam": "RED",
    }
    # Both rows of the pair get the results of the same suite. The two
    # FASTQ files do not have the same number of lines.
    fastq_rows = [rows[1], rows[3]]
    for row in fastq_rows:
        assert "PairedFastqParityTest" in split_cell(row["dcqc_required_tests"])
        assert split_cell(row["dcqc_failed_tests"]) == {"PairedFastqParityTest"}
        assert row["dcqc_grouping"] == "fastq_pair"


def test_update_csv(get_data, get_output):
    suites_path = get_data("suites.json")
    input_path = get_data("input.csv")
    output_path = get_output("update_csv") / "output.csv"
    output_path.unlink(missing_ok=True)

    args = [
        "update-csv",
        suites_path,
        input_path,
        output_path,
    ]
    result = run_command(args)
    check_command_result(result)
    assert output_path.exists()
