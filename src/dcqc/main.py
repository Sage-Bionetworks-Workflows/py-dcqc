import os
import sys
from csv import DictWriter
from pathlib import Path
from typing import List, Optional

from typer import Argument, Exit, Option, Typer

from dcqc import __version__
from dcqc.file import FileType
from dcqc.parsers import CsvParser, JsonParser
from dcqc.reports import JsonReport
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import Target
from dcqc.tests.test_abc import ExternalTestMixin, TestABC
from dcqc.utils import is_url_local

# Make commands optional to allow for `dcqc --version`
app = Typer(invoke_without_command=True)


# Common arguments
# Distinguishing between path and path/url arguments until I/O is consistent
input_path_arg = Argument(..., help="Input file")
input_path_list_arg = Argument(..., help="List of input files")
output_arg = Argument(..., help="Path or (remote) URL for output file")
output_dir_arg = Argument(..., help="Directory path or (remote) URL for output files")
output_path_arg = Argument(..., help="Path for output file")
output_dir_path_arg = Argument(..., help="Directory path for output files")

# Common options
overwrite_opt = Option(False, "--overwrite", "-f", help="Ignore existing files")
required_tests_opt = Option(None, "--required-tests", "-rt", help="Required tests")
skipped_tests_opt = Option(None, "--skipped-tests", "-st", help="Skipped tests")
stage_files_opt = Option(False, "--stage-files", "-sf", help="Stage remote files.")
prt_help = "Update paths to be relative to given directory upon serialization."
paths_relative_to_opt = Option(None, "--paths-relative-to", "-prt", help=prt_help)


@app.callback()
def main(version: bool = False):
    """DCQC Python Package"""
    if version:
        print(f"DCQC Python Package Version: {__version__}")
        raise Exit()


@app.command()
def create_targets(
    input_csv: Path = input_path_arg,
    output_dir: str = output_dir_arg,
    overwrite: bool = overwrite_opt,
    stage_files: bool = stage_files_opt,
):
    """Create target JSON files from a targets CSV file"""
    if is_url_local(output_dir):
        _, _, resource = output_dir.rpartition("://")
        os.makedirs(resource, exist_ok=True)

    parser = CsvParser(input_csv, stage_files)
    targets = parser.create_targets()

    # Naming the targets by index to ensure no clashes
    named_targets = {f"target-{target.id}.json": target for target in targets}

    report = JsonReport()
    report.save_many(named_targets, output_dir, overwrite)


@app.command()
def stage_target(
    input_json: Path = input_path_arg,
    output_json: str = output_arg,
    output_dir: Path = output_dir_path_arg,
    overwrite: bool = overwrite_opt,
    paths_relative_to: Optional[Path] = paths_relative_to_opt,
):
    """Create local file copies from a target JSON file"""
    output_dir.mkdir(parents=True, exist_ok=True)

    target = JsonParser.parse_object(input_json, Target)
    target.stage(output_dir, overwrite)

    report = JsonReport(paths_relative_to)
    report.save(target, output_json, overwrite)


@app.command()
def create_tests(
    input_json: Path = input_path_arg,
    output_dir: Path = output_dir_path_arg,
    required_tests: List[str] = required_tests_opt,
    skipped_tests: List[str] = skipped_tests_opt,
    overwrite: bool = overwrite_opt,
):
    """Create test JSON files from a target JSON file"""
    output_dir.mkdir(parents=True, exist_ok=True)

    target = JsonParser.parse_object(input_json, Target)
    suite = SuiteABC.from_target(target, required_tests, skipped_tests)

    report = JsonReport()
    for test in suite.tests:
        output_path = output_dir / f"{input_json.stem}.{test.type}.json"
        output_url = output_path.as_posix()
        report.save(test, output_url, overwrite)


@app.command()
def create_process(
    input_json: Path = input_path_arg,
    output_json: Path = output_path_arg,
    overwrite: bool = overwrite_opt,
):
    """Create external process JSON file from a test JSON file"""
    output_json.parent.mkdir(parents=True, exist_ok=True)

    test = JsonParser.parse_object(input_json, ExternalTestMixin)
    process = test.generate_process()
    output_url = output_json.as_posix()

    report = JsonReport()
    report.save(process, output_url, overwrite)


@app.command()
def compute_test(
    input_json: Path = input_path_arg,
    output_json: Path = output_path_arg,
    overwrite: bool = overwrite_opt,
):
    """Compute the test status from a test JSON file"""
    output_json.parent.mkdir(parents=True, exist_ok=True)

    test = JsonParser.parse_object(input_json, TestABC)
    test.get_status()
    output_url = output_json.as_posix()

    report = JsonReport()
    report.save(test, output_url, overwrite)


@app.command()
def create_suite(
    output_json: str = output_arg,
    input_jsons: List[Path] = input_path_list_arg,
    required_tests: List[str] = required_tests_opt,
    skipped_tests: List[str] = skipped_tests_opt,
    overwrite: bool = overwrite_opt,
):
    """Create a suite from a set of test JSON files sharing the same target"""
    tests = [JsonParser.parse_object(test_json, TestABC) for test_json in input_jsons]
    suite = SuiteABC.from_tests(tests, required_tests, skipped_tests)
    report = JsonReport()
    report.save(suite, output_json, overwrite)


@app.command()
def combine_suites(
    output_json: str = output_arg,
    input_jsons: List[Path] = input_path_list_arg,
    overwrite: bool = overwrite_opt,
):
    """Combine several suite JSON files into a single JSON report"""
    suites = [JsonParser.parse_object(json_, SuiteABC) for json_ in input_jsons]
    report = JsonReport()
    report.save(suites, output_json, overwrite)


@app.command()
def list_tests():
    """List the tests available for each file type"""
    test_classes_by_file_type = SuiteABC.list_test_classes_by_file_type()

    rows = list()
    for file_type_name, test_classes in test_classes_by_file_type.items():
        file_type = FileType.get_file_type(file_type_name)
        for test_cls in test_classes:
            test_dict = {
                "file_type": file_type_name,
                "edam_iri": file_type.edam_iri,
                "test_name": test_cls.__name__,
                "test_tier": test_cls.tier,
                "test_type": "external" if test_cls.is_external_test else "internal",
            }
            rows.append(test_dict)

    fieldnames = list(rows[0])
    writer = DictWriter(sys.stdout, fieldnames)
    writer.writeheader()
    writer.writerows(rows)
