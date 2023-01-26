import shutil
from typing import Any

import pytest
from click.testing import Result
from typer.testing import CliRunner

from dcqc.main import app


# Using a test class to mark all tests as "integration"
@pytest.mark.integration
class TestCLI:
    def run_command(self, arguments: list[Any]):
        runner = CliRunner()
        str_arguments = [str(arg) for arg in arguments]
        result = runner.invoke(app, str_arguments)
        return result

    def check_command_result(self, result: Result):
        assert result.exit_code == 0

    def test_create_targets(self, get_data, get_output):
        input_csv = get_data("small.csv")
        output_dir = get_output("create_targets")
        shutil.rmtree(output_dir, ignore_errors=True)

        assert not output_dir.exists()
        args = ["create-targets", input_csv, output_dir]
        result = self.run_command(args)
        self.check_command_result(result)
        assert len(list(output_dir.iterdir())) > 0

    def test_stage_target(self, get_data, get_output):
        input_json = get_data("target.json")
        output_json = get_output("stage_target/target.staged.json")
        output_dir = get_output("stage_target/targets")
        output_json.unlink(missing_ok=True)
        shutil.rmtree(output_dir, ignore_errors=True)

        assert not output_dir.exists()
        args = ["stage-target", "-prt", ".", input_json, output_json, output_dir]
        result = self.run_command(args)
        self.check_command_result(result)
        assert len(list(output_dir.iterdir())) > 0

    def test_create_tests(self, get_data, get_output):
        input_json = get_data("target.json")
        output_dir = get_output("create_tests")
        shutil.rmtree(output_dir, ignore_errors=True)

        assert not output_dir.exists()
        args = ["create-tests", "-rt", "Md5ChecksumTest", input_json, output_dir]
        result = self.run_command(args)
        self.check_command_result(result)
        assert len(list(output_dir.iterdir())) > 0

    def test_create_process(self, get_data, get_output):
        input_json = get_data("test.external.json")
        output_path = get_output("create_process") / "process.json"
        output_path.unlink(missing_ok=True)

        assert not output_path.exists()
        args = ["create-process", input_json, output_path]
        result = self.run_command(args)
        self.check_command_result(result)
        assert output_path.exists()

    def test_compute_test(self, get_data, get_output):
        input_json = get_data("test.internal.json")
        output_path = get_output("compute_test") / "test.json"
        output_path.unlink(missing_ok=True)

        assert not output_path.exists()
        args = ["compute-test", input_json, output_path]
        result = self.run_command(args)
        self.check_command_result(result)
        assert output_path.exists()

    def test_create_suite(self, get_data, get_output):
        input_json = get_data("test.computed.json")
        output_path = get_output("create_suite") / "suite.json"
        output_path.unlink(missing_ok=True)

        args = ["create-suite", output_path, input_json, input_json, input_json]
        result = self.run_command(args)
        self.check_command_result(result)
        assert output_path.exists()

    def test_combine_suites(self, get_data, get_output):
        input_json = get_data("suite.json")
        output_path = get_output("combine_suites") / "suites.json"
        output_path.unlink(missing_ok=True)

        args = ["combine-suites", output_path, input_json, input_json, input_json]
        result = self.run_command(args)
        self.check_command_result(result)
        assert output_path.exists()

    def test_list_tests(self):
        args = ["list-tests"]
        result = self.run_command(args)
        self.check_command_result(result)
