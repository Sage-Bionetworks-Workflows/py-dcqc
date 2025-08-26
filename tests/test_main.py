import shutil
from subprocess import check_output
from typing import Any

import pytest
from click.testing import Result
from typer.testing import CliRunner

import dcqc
from dcqc.main import app
from dcqc.parsers import JsonParser
from dcqc.suites.suite_abc import SuiteABC


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


@pytest.mark.slow
def test_that_the_module_cli_behaves_the_same_as_the_plain_cli():
    module_cli = check_output(["python", "-m", "dcqc", "--help"])
    plain_cli = check_output(["dcqc", "--help"])
    assert module_cli == plain_cli


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
