import json
import sys
from csv import DictWriter
from pathlib import Path
from typing import List

from typer import Argument, Exit, Option, Typer

from dcqc import __version__
from dcqc.file import File, FileType
from dcqc.parsers import CsvParser, JsonParser
from dcqc.reports import JsonReport
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import SingleTarget
from dcqc.tests.base_test import BaseTest, ExternalTestMixin
from dcqc.updaters import CsvUpdater

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
required_tests_opt = Option(None, "--required-tests", "-r", help="Required tests")
skipped_tests_opt = Option(None, "--skipped-tests", "-s", help="Skipped tests")
file_type_opt = Option(..., "--file-type", "-t", help="File type")
metadata_opt = Option("{}", "--metadata", "-m", help="File metadata")


@app.callback()
def main(version: bool = False):
    """DCQC Python Package"""
    if version:
        print(f"DCQC Python Package Version: {__version__}")
        raise Exit()


@app.command()
def create_targets(
    input_csv: Path = input_path_arg,
    output_dir: Path = output_dir_path_arg,
    overwrite: bool = overwrite_opt,
):
    """Create target JSON files from a targets CSV file"""
    output_dir.mkdir(parents=True, exist_ok=True)

    parser = CsvParser(input_csv)
    targets = parser.create_targets()

    # Naming the targets by index to ensure no clashes
    named_targets = {f"target-{target.id}.json": target for target in targets}

    report = JsonReport()
    report.save_many(named_targets, output_dir.as_posix(), overwrite)


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

    # Interpret empty lists from CLI as None (to auto-generate values)
    required_tests_maybe = required_tests if required_tests else None
    skipped_tests_maybe = skipped_tests if skipped_tests else None

    target = JsonParser.parse_object(input_json, SingleTarget)
    suite = SuiteABC.from_target(target, required_tests_maybe, skipped_tests_maybe)

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

    test = JsonParser.parse_object(input_json, BaseTest)
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
    # Interpret empty lists from CLI as None (to auto-generate values)
    required_tests_maybe = required_tests if required_tests else None
    skipped_tests_maybe = skipped_tests if skipped_tests else None

    tests = [JsonParser.parse_object(test_json, BaseTest) for test_json in input_jsons]
    suite = SuiteABC.from_tests(tests, required_tests_maybe, skipped_tests_maybe)
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


@app.command()
def qc_file(
    input_file: Path = input_path_arg,
    file_type: str = file_type_opt,
    metadata: str = metadata_opt,
    required_tests: List[str] = required_tests_opt,
    skipped_tests: List[str] = skipped_tests_opt,
):
    """Run QC tests on a single file (external tests are skipped)"""
    # Interpret empty lists from CLI as None (to auto-generate values)
    required_tests_maybe = required_tests if required_tests else None

    # Prepare target
    file_metadata = json.loads(metadata)
    file_metadata["file_type"] = file_type
    file = File(input_file.as_posix(), file_metadata)
    target = SingleTarget(file)

    # Prepare suite (skip all external tests)
    suite = SuiteABC.from_target(target, required_tests_maybe, skipped_tests)
    external_tests = [test.type for test in suite.tests if test.is_external_test]
    skipped_tests += external_tests
    suite = SuiteABC.from_target(target, required_tests_maybe, skipped_tests)

    # Output QC report on stdout
    report = JsonReport()
    suite_json = report.generate(suite)
    json.dump(suite_json, sys.stdout, indent=2)


@app.command()
def update_csv(
    suites_file: Path = input_path_arg,
    input_file: Path = input_path_arg,
    output_file: Path = output_path_arg,
):
    """Update input CSV file with dcqc_status column"""
    suites = JsonParser.parse_objects(suites_file, SuiteABC)
    updater = CsvUpdater(input_file, output_file)
    updater.update(suites)
